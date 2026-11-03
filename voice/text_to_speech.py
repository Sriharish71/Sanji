"""
Text-to-Speech (TTS) Engine for SANJI using Piper TTS.
Provides natural, offline neural speech synthesis running purely on CPU
with non-blocking playback and stop/mute controls.
"""

import re
import threading
from pathlib import Path
from typing import Optional
import numpy as np
from PySide6.QtCore import QObject, QThread, Signal

from utils.logger import logger
from voice.audio_manager import AudioManager


def clean_text_for_speech(text: str) -> str:
    """
    Cleans markdown formatting, links, and code blocks
    so the assistant sounds natural and avoids pronouncing punctuation.
    """
    # Remove code blocks ```...```
    cleaned = re.sub(r"```[\s\S]*?```", " Code snippet omitted. ", text)
    # Remove inline code `...`
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    # Remove markdown links [text](url) -> text
    cleaned = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", cleaned)
    # Remove bold/italic asterisks and underscores
    cleaned = re.sub(r"[\*_]{1,3}([^\*_]+)[\*_]{1,3}", r"\1", cleaned)
    # Remove header markers #
    cleaned = re.sub(r"^#{1,6}\s*", "", cleaned, flags=re.MULTILINE)
    # Remove bullet markers
    cleaned = re.sub(r"^\s*[\-\*\•]\s*", "", cleaned, flags=re.MULTILINE)
    # Remove emoji and strange control characters
    cleaned = re.sub(r"[^\x00-\x7F]+", " ", cleaned)
    # Normalize whitespaces
    cleaned = " ".join(cleaned.split())
    return cleaned.strip()


class TTSWorker(QThread):
    """Asynchronous worker for synthesizing and playing audio chunks."""

    speech_started = Signal()
    speech_finished = Signal()
    error_occurred = Signal(str)

    def __init__(self, tts_engine: "TextToSpeech", text: str):
        super().__init__()
        self.tts = tts_engine
        self.raw_text = text
        self._is_cancelled = False

    def cancel(self) -> None:
        self._is_cancelled = True

    def run(self) -> None:
        try:
            cleaned = clean_text_for_speech(self.raw_text)
            if not cleaned:
                self.speech_finished.emit()
                return

            self.speech_started.emit()

            # Synthesize with Piper
            audio_data, sample_rate = self.tts.synthesize_sync(cleaned)

            if self._is_cancelled or audio_data is None:
                self.speech_finished.emit()
                return

            # Play synthesized audio through AudioManager
            self.tts.audio_manager.play_audio(audio_data, sample_rate=sample_rate)

            # Wait while audio is playing, polling cancel flag
            import sounddevice as sd
            while sd.get_stream() and sd.get_stream().active:
                if self._is_cancelled or self.tts.is_muted:
                    self.tts.audio_manager.stop_playback()
                    break
                self.msleep(100)

            self.speech_finished.emit()

        except Exception as e:
            logger.exception("TTS Worker failure")
            self.error_occurred.emit(f"Speech synthesis error: {e}")
            self.speech_finished.emit()


class TextToSpeech(QObject):
    """High-level Piper TTS coordinator with playback queue and mute control."""

    speech_started = Signal()
    speech_finished = Signal()
    speaking_state_changed = Signal(bool)  # True = speaking, False = silent
    error_occurred = Signal(str)

    def __init__(
        self,
        audio_manager: AudioManager,
        model_path: Optional[str] = None,
    ):
        super().__init__()
        self.audio_manager = audio_manager
        self.model_path = model_path or "voice/models/piper/en_US-lessac-medium.onnx"
        self._voice = None
        self._current_worker: Optional[TTSWorker] = None
        self._is_speaking = False
        self._is_muted = False
        self._lock = threading.Lock()

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    @property
    def is_muted(self) -> bool:
        return self._is_muted

    def set_muted(self, muted: bool) -> None:
        """Sets mute state. If muted while speaking, interrupts speech immediately."""
        self._is_muted = muted
        if muted:
            self.stop()

    def toggle_muted(self) -> bool:
        """Toggles mute state and returns new state."""
        self.set_muted(not self._is_muted)
        return self._is_muted

    def _ensure_voice_loaded(self) -> None:
        """Loads Piper ONNX voice model if not already loaded."""
        if self._voice is not None:
            return

        with self._lock:
            if self._voice is not None:
                return

            import piper
            resolved_path = Path(self.model_path)
            if not resolved_path.is_absolute():
                resolved_path = Path(__file__).resolve().parent.parent / resolved_path

            if not resolved_path.exists():
                logger.info(f"Downloading Piper voice model to {resolved_path}...")
                resolved_path.parent.mkdir(parents=True, exist_ok=True)
                import urllib.request
                model_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
                config_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"
                config_path = resolved_path.with_suffix(".onnx.json")
                if not config_path.exists():
                    urllib.request.urlretrieve(config_url, config_path)
                urllib.request.urlretrieve(model_url, resolved_path)
                logger.info("Piper voice model downloaded successfully.")

            logger.info(f"Loading Piper voice from {resolved_path}...")
            self._voice = piper.PiperVoice.load(str(resolved_path), use_cuda=False)
            logger.info("Piper voice initialized successfully.")

    def synthesize_sync(self, text: str) -> tuple[Optional[np.ndarray], int]:
        """Synthesizes text into contiguous float32 audio array and sample rate."""
        self._ensure_voice_loaded()
        chunks = list(self._voice.synthesize(text))
        if not chunks:
            return None, 22050

        # Concatenate audio chunks
        audio_arrays = [c.audio_float_array for c in chunks if c.audio_float_array is not None]
        if not audio_arrays:
            return None, 22050

        combined = np.concatenate(audio_arrays, axis=0)
        sample_rate = chunks[0].sample_rate
        return combined, sample_rate

    def speak_async(self, text: str) -> None:
        """Synthesizes and plays text asynchronously without blocking the UI."""
        if self._is_muted:
            logger.debug("TTS is muted; skipping speech.")
            return

        # Stop any currently playing audio
        self.stop()

        self._current_worker = TTSWorker(self, text)
        self._current_worker.speech_started.connect(self._on_worker_started)
        self._current_worker.speech_finished.connect(self._on_worker_finished)
        self._current_worker.error_occurred.connect(self.error_occurred)
        self._current_worker.start()

    def stop(self) -> None:
        """Immediately cancels ongoing speech and stops audio playback."""
        if self._current_worker and self._current_worker.isRunning():
            self._current_worker.cancel()
            self._current_worker.wait(300)
            self._current_worker = None

        self.audio_manager.stop_playback()

        if self._is_speaking:
            self._is_speaking = False
            self.speaking_state_changed.emit(False)
            self.speech_finished.emit()

    def _on_worker_started(self) -> None:
        self._is_speaking = True
        self.speaking_state_changed.emit(True)
        self.speech_started.emit()

    def _on_worker_finished(self) -> None:
        self._is_speaking = False
        self.speaking_state_changed.emit(False)
        self.speech_finished.emit()
        self._current_worker = None
