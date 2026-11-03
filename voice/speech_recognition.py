"""
Speech-to-Text (STT) Engine for SANJI using Faster-Whisper.
Provides non-blocking, CPU-optimized transcription of microphone audio
without consuming GPU VRAM needed for local LLM inference.
"""

from typing import Optional
import numpy as np
from PySide6.QtCore import QObject, QThread, Signal

from config import settings
from utils.logger import logger


class STTWorker(QThread):
    """Background worker thread for executing speech transcription without blocking UI."""

    transcription_finished = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, recognizer: "SpeechRecognizer", audio_data: np.ndarray):
        super().__init__()
        self.recognizer = recognizer
        self.audio_data = audio_data

    def run(self) -> None:
        try:
            text = self.recognizer.transcribe_sync(self.audio_data)
            self.transcription_finished.emit(text)
        except Exception as e:
            logger.exception("STT Worker transcription failure")
            self.error_occurred.emit(f"Speech recognition error: {str(e)}")


class SpeechRecognizer(QObject):
    """High-level Faster-Whisper interface and worker coordinator."""

    transcription_started = Signal()
    transcription_finished = Signal(str)
    error_occurred = Signal(str)
    model_loaded = Signal()

    def __init__(
        self,
        model_size: str = "tiny.en",
        device: str = "cpu",
        compute_type: str = "int8",
    ):
        super().__init__()
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None
        self._is_loading = False
        self._current_worker: Optional[STTWorker] = None

    def _ensure_model_loaded(self) -> None:
        """Lazy loader for Faster-Whisper model."""
        if self._model is not None:
            return

        try:
            from faster_whisper import WhisperModel

            logger.info(
                f"Loading Faster-Whisper [{self.model_size}] on {self.device} ({self.compute_type})..."
            )
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=4,
            )
            logger.info(f"Faster-Whisper model [{self.model_size}] initialized successfully.")
            self.model_loaded.emit()

        except Exception as e:
            err = f"Failed to load Faster-Whisper model: {e}"
            logger.error(err)
            raise RuntimeError(err)

    def transcribe_sync(self, audio_data: np.ndarray) -> str:
        """
        Synchronously transcribes 16kHz float32 audio array.
        Intended to be called from a background thread (e.g., STTWorker).
        """
        if audio_data is None or len(audio_data) == 0:
            return ""

        self._ensure_model_loaded()

        # Run transcription with beam_size=1 and vad_filter=True for speed
        segments, info = self._model.transcribe(
            audio_data,
            beam_size=1,
            language="en",
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )

        # Collect segment texts
        text_parts = [segment.text.strip() for segment in segments]
        transcription = " ".join(text_parts).strip()
        logger.info(f"Faster-Whisper recognized text: '{transcription}'")
        return transcription

    def transcribe_async(self, audio_data: np.ndarray) -> None:
        """Launches an asynchronous transcription task in background QThread."""
        if audio_data is None or len(audio_data) == 0:
            self.transcription_finished.emit("")
            return

        self.transcription_started.emit()

        # Clean up any lingering worker
        if self._current_worker and self._current_worker.isRunning():
            self._current_worker.wait(500)

        self._current_worker = STTWorker(self, audio_data)
        self._current_worker.transcription_finished.connect(self._on_worker_finished)
        self._current_worker.error_occurred.connect(self._on_worker_error)
        self._current_worker.start()

    def _on_worker_finished(self, text: str) -> None:
        self.transcription_finished.emit(text)
        self._current_worker = None

    def _on_worker_error(self, err: str) -> None:
        self.error_occurred.emit(err)
        self._current_worker = None
