"""
Audio Manager for SANJI Voice Subsystem.
Handles low-level microphone audio recording, real-time volume telemetry,
speaker playback, and audio hardware device enumeration using sounddevice.
"""

import queue
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, Signal

from utils.logger import logger


class AudioManager(QObject):
    """Manages audio capture (microphone) and playback (speakers)."""

    # Signals for UI feedback
    volume_level_changed = Signal(float)  # Normalized 0.0 to 1.0 for visualizer
    recording_started = Signal()
    recording_stopped = Signal()
    playback_started = Signal()
    playback_finished = Signal()
    error_occurred = Signal(str)

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        input_device: Optional[int] = None,
        output_device: Optional[int] = None,
    ):
        super().__init__()
        self.sample_rate = sample_rate
        self.channels = channels
        self.input_device = input_device
        self.output_device = output_device

        self._audio_queue: queue.Queue = queue.Queue()
        self._input_stream: Optional[sd.InputStream] = None
        self._is_recording = False
        self._is_muted = False

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    @property
    def is_muted(self) -> bool:
        return self._is_muted

    def set_muted(self, muted: bool) -> None:
        """Sets mute state for audio playback."""
        self._is_muted = muted
        if muted:
            self.stop_playback()

    def get_devices(self) -> Dict[str, List[Dict[str, Any]]]:
        """Queries and returns available input and output audio hardware."""
        inputs = []
        outputs = []
        try:
            devices = sd.query_devices()
            for idx, dev in enumerate(devices):
                info = {
                    "index": idx,
                    "name": dev.get("name", "Unknown"),
                    "hostapi": dev.get("hostapi", 0),
                    "max_inputs": dev.get("max_input_channels", 0),
                    "max_outputs": dev.get("max_output_channels", 0),
                    "default_samplerate": dev.get("default_samplerate", 44100),
                }
                if dev.get("max_input_channels", 0) > 0:
                    inputs.append(info)
                if dev.get("max_output_channels", 0) > 0:
                    outputs.append(info)
        except Exception as e:
            logger.error(f"Error querying audio hardware devices: {e}")

        return {"inputs": inputs, "outputs": outputs}

    def _audio_callback(self, indata, frames, time_info, status):
        """Internal callback invoked for each audio buffer block."""
        if status:
            logger.debug(f"Audio buffer status: {status}")

        if self._is_recording:
            # Copy incoming audio data
            data_copy = indata.copy()
            self._audio_queue.put(data_copy)

            # Calculate Root Mean Square (RMS) volume for live visualizer
            try:
                rms = np.sqrt(np.mean(data_copy ** 2))
                # Normalize and apply non-linear boost for responsive visualizer
                normalized_level = min(1.0, float(rms * 12.0))
                self.volume_level_changed.emit(normalized_level)
            except Exception:
                pass

    def start_recording(self) -> bool:
        """Starts capturing audio stream from default or configured microphone."""
        if self._is_recording:
            return True

        # Clear any stale frames
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

        try:
            self._input_stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                device=self.input_device,
                callback=self._audio_callback,
                blocksize=1024,
            )
            self._input_stream.start()
            self._is_recording = True
            self.recording_started.emit()
            logger.info("Microphone recording started.")
            return True

        except Exception as e:
            error_msg = f"Failed to access microphone: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self._is_recording = False
            return False

    def stop_recording(self) -> Optional[np.ndarray]:
        """
        Stops audio recording and returns all captured audio
        as a contiguous 1D float32 numpy array.
        """
        if not self._is_recording:
            return None

        self._is_recording = False

        if self._input_stream:
            try:
                self._input_stream.stop()
                self._input_stream.close()
            except Exception as e:
                logger.warning(f"Error closing input stream: {e}")
            finally:
                self._input_stream = None

        self.recording_stopped.emit()
        self.volume_level_changed.emit(0.0)

        # Collect all blocks from queue
        audio_blocks = []
        while not self._audio_queue.empty():
            try:
                audio_blocks.append(self._audio_queue.get_nowait())
            except queue.Empty:
                break

        if not audio_blocks:
            logger.warning("No audio blocks captured during recording session.")
            return None

        # Concatenate and flatten to 1D array
        recorded_audio = np.concatenate(audio_blocks, axis=0).flatten()
        duration = len(recorded_audio) / self.sample_rate
        logger.info(f"Captured {duration:.2f}s of microphone audio ({len(recorded_audio)} samples).")
        return recorded_audio

    def play_audio(self, audio_data: np.ndarray, sample_rate: int = 22050) -> None:
        """Plays raw audio array through speakers."""
        if self._is_muted:
            logger.info("Audio playback suppressed (Muted).")
            return

        try:
            self.stop_playback()
            self.playback_started.emit()
            sd.play(audio_data, samplerate=sample_rate, device=self.output_device)
        except Exception as e:
            err = f"Playback error: {e}"
            logger.error(err)
            self.error_occurred.emit(err)

    def stop_playback(self) -> None:
        """Interrupts and stops ongoing speaker audio."""
        try:
            sd.stop()
            self.playback_finished.emit()
        except Exception as e:
            logger.debug(f"Exception stopping audio playback: {e}")

    def is_playing(self) -> bool:
        """Checks if sounddevice output stream is currently playing."""
        try:
            # Query sounddevice active stream status
            stream = sd.get_stream()
            return stream is not None and stream.active
        except Exception:
            return False
