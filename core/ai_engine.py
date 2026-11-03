"""
AI Engine for SANJI.
Handles asynchronous, non-blocking LLM inference via Ollama streaming API.
Runs in a separate QThread to ensure the PySide6 UI remains buttery-smooth.
"""

import json
from typing import Any, Dict, List, Optional
import requests
from PySide6.QtCore import QObject, QThread, Signal

from config import settings
from utils.logger import logger


class StreamWorker(QObject):
    """
    Worker executing in a dedicated QThread.
    Streams incremental response tokens from Ollama to avoid freezing the UI.
    """

    # Signals for communication with UI thread
    chunk_received = Signal(str)         # Emits each text chunk as it arrives
    stream_finished = Signal(str)        # Emits full accumulated response
    error_occurred = Signal(str)         # Emits friendly error message
    status_changed = Signal(str)         # Status updates (e.g. "Thinking...", "Streaming...")

    def __init__(
        self,
        base_url: str,
        model: str,
        messages: List[Dict[str, str]],
        timeout: float = 90.0,
        options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__()
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.messages = messages
        self.timeout = timeout
        self.options = options or {"temperature": 0.7}
        self._is_cancelled = False

    def cancel(self) -> None:
        """Flags the worker to stop processing and close connection."""
        self._is_cancelled = True

    def run(self) -> None:
        """Executes the streaming HTTP request against Ollama."""
        endpoint = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": self.messages,
            "stream": True,
            "options": self.options,
        }

        accumulated_text: List[str] = []

        try:
            self.status_changed.emit("Connecting to neural engine...")
            logger.debug(f"Sending prompt to {endpoint} with model {self.model}")

            response = requests.post(
                endpoint,
                json=payload,
                stream=True,
                timeout=(5.0, self.timeout),
            )

            if response.status_code == 404:
                error_msg = (
                    f"Model '{self.model}' not found in Ollama.\n"
                    f"Please run: ollama run {self.model}"
                )
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                return

            if response.status_code != 200:
                error_msg = f"Ollama error (HTTP {response.status_code}): {response.text}"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                return

            self.status_changed.emit("SANJI is thinking...")

            for line in response.iter_lines(decode_unicode=True):
                if self._is_cancelled:
                    logger.info("Stream cancelled by user.")
                    break

                if not line:
                    continue

                try:
                    data = json.loads(line)
                    chunk = data.get("message", {}).get("content", "")
                    if chunk:
                        accumulated_text.append(chunk)
                        self.chunk_received.emit(chunk)

                    if data.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue

            full_reply = "".join(accumulated_text)
            self.stream_finished.emit(full_reply)

        except requests.exceptions.ConnectionError:
            error_msg = (
                "Cannot connect to Ollama. Is the service running?\n"
                "Tip: Start Ollama from your Start menu or run 'ollama serve' in PowerShell."
            )
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)

        except requests.exceptions.Timeout:
            error_msg = "Inference timed out. The local model took too long to respond."
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)

        except Exception as e:
            error_msg = f"Unexpected engine error: {str(e)}"
            logger.exception("AI Engine failure")
            self.error_occurred.emit(error_msg)


class AIEngine(QObject):
    """
    High-level facade for launching and managing asynchronous inference threads.
    """

    chunk_received = Signal(str)
    response_finished = Signal(str)
    error_occurred = Signal(str)
    status_changed = Signal(str)

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        super().__init__()
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model
        self.timeout = settings.ollama_timeout_seconds

        self._current_thread: Optional[QThread] = None
        self._current_worker: Optional[StreamWorker] = None

    def is_generating(self) -> bool:
        """Returns True if a generation stream is currently active."""
        return self._current_thread is not None and self._current_thread.isRunning()

    def generate(self, messages: List[Dict[str, str]]) -> None:
        """
        Launches an asynchronous inference task in a background QThread.
        Safe to call from the Qt Main UI thread.
        """
        # Cancel any previous task if still running
        self.cancel_generation()

        # Initialize thread and worker
        self._current_thread = QThread()
        self._current_worker = StreamWorker(
            base_url=self.base_url,
            model=self.model,
            messages=messages,
            timeout=self.timeout
        )
        self._current_worker.moveToThread(self._current_thread)

        # Wire worker signals
        self._current_worker.chunk_received.connect(self.chunk_received)
        self._current_worker.status_changed.connect(self.status_changed)

        self._current_worker.stream_finished.connect(self._on_worker_finished)
        self._current_worker.error_occurred.connect(self._on_worker_error)

        # Wire thread execution
        self._current_thread.started.connect(self._current_worker.run)

        # Start thread
        self._current_thread.start()

    def cancel_generation(self) -> None:
        """Gracefully halts ongoing generation if active."""
        if self._current_worker:
            self._current_worker.cancel()
        if self._current_thread and self._current_thread.isRunning():
            self._current_thread.quit()
            self._current_thread.wait(1000)
        self._current_thread = None
        self._current_worker = None

    def _on_worker_finished(self, full_text: str) -> None:
        self.response_finished.emit(full_text)
        self._cleanup()

    def _on_worker_error(self, error_msg: str) -> None:
        self.error_occurred.emit(error_msg)
        self._cleanup()

    def _cleanup(self) -> None:
        if self._current_thread:
            self._current_thread.quit()
            self._current_thread.wait(500)
            self._current_thread = None
            self._current_worker = None

