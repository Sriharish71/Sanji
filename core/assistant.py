"""
Assistant Coordinator for SANJI.
Orchestrates AI Engine, Conversation State, Model Health, Memory Persistence,
and Voice Subsystem (Faster-Whisper STT & Piper TTS).
Acts as the central controller between UI and backend subsystems.
"""

from typing import Any, Dict, List, Optional
import numpy as np
from PySide6.QtCore import QObject, Signal

from config import settings
from core.ai_engine import AIEngine
from core.conversation_manager import ConversationManager
from core.model_manager import ModelManager, ModelStatus
from memory.database import Database
from memory.memory_manager import MemoryManager
from utils.logger import logger
from voice.audio_manager import AudioManager
from voice.speech_recognition import SpeechRecognizer
from voice.text_to_speech import TextToSpeech


class Assistant(QObject):
    """Primary business logic controller for SANJI."""

    # UI Notifications
    chunk_received = Signal(str)
    response_finished = Signal(str)
    error_occurred = Signal(str)
    status_changed = Signal(str)
    health_checked = Signal(object)  # ModelStatus object

    # Voice Signals (Phase 2)
    listening_state_changed = Signal(bool)   # True = Recording mic, False = Idle
    speaking_state_changed = Signal(bool)    # True = Speaking via TTS, False = Silent
    volume_level_changed = Signal(float)     # 0.0 to 1.0 for real-time waveform/pulse
    transcription_ready = Signal(str)        # Emitted when speech recognized

    def __init__(self, db: Optional[Database] = None):
        super().__init__()
        # 1. Initialize Memory
        db_path = settings.get_resolved_db_path()
        self.db = db or Database(db_path)
        self.memory = MemoryManager(self.db)

        # 2. Conversation & Model Managers
        self.conversation = ConversationManager(self.memory)
        self.model_manager = ModelManager()

        # 3. Asynchronous AI Engine
        self.ai_engine = AIEngine()
        self._wire_engine_signals()

        # 4. Voice Subsystem (Phase 2)
        self.audio_manager = AudioManager()
        self.speech_recognizer = SpeechRecognizer(
            model_size=settings.stt_model_size,
            device=settings.stt_device,
            compute_type=settings.stt_compute_type,
        )
        self.tts = TextToSpeech(
            audio_manager=self.audio_manager,
            model_path=settings.tts_voice_model,
        )
        self._wire_voice_signals()

        logger.info("SANJI Assistant coordinator & Voice subsystem initialized successfully.")

    def _wire_engine_signals(self) -> None:
        """Connects engine worker signals to assistant coordinator signals."""
        self.ai_engine.chunk_received.connect(self.chunk_received)
        self.ai_engine.status_changed.connect(self.status_changed)
        self.ai_engine.response_finished.connect(self._handle_response_finished)
        self.ai_engine.error_occurred.connect(self._handle_error_occurred)

    def _wire_voice_signals(self) -> None:
        """Connects voice component signals to assistant coordinator signals."""
        self.audio_manager.volume_level_changed.connect(self.volume_level_changed)
        self.audio_manager.error_occurred.connect(self._handle_error_occurred)

        self.speech_recognizer.transcription_finished.connect(self._handle_transcription_finished)
        self.speech_recognizer.error_occurred.connect(self._handle_error_occurred)

        self.tts.speaking_state_changed.connect(self.speaking_state_changed)
        self.tts.error_occurred.connect(self._handle_error_occurred)

    def send_prompt(self, user_text: str) -> None:
        """
        Processes a user message: records to memory, prepares context,
        stops any ongoing TTS speech, and launches async streaming generation.
        """
        trimmed = user_text.strip()
        if not trimmed:
            return

        # Stop any active TTS playback
        self.tts.stop()

        # 1. Persist user message to memory
        self.conversation.add_user_message(trimmed)

        # 2. Prepare context payload
        payload = self.conversation.build_llm_payload()

        # 3. Launch generation
        self.status_changed.emit("Thinking...")
        self.ai_engine.generate(payload)

    def _handle_response_finished(self, full_response: str) -> None:
        """Saves generated answer into database and optionally triggers TTS."""
        # Persist assistant response
        self.conversation.add_assistant_message(
            content=full_response,
            model=self.ai_engine.model
        )
        self.status_changed.emit("Ready")
        self.response_finished.emit(full_response)

        # Vocalize response via Piper TTS if enabled and not muted
        if settings.tts_auto_speak and not self.tts.is_muted and full_response.strip():
            self.status_changed.emit("Speaking...")
            self.tts.speak_async(full_response)

    def _handle_error_occurred(self, error_message: str) -> None:
        """Handles engine or voice errors gracefully."""
        self.status_changed.emit("Error")
        self.error_occurred.emit(error_message)

    # ---------------------------------------------------------
    # Voice Control Actions (Phase 2)
    # ---------------------------------------------------------

    def start_listening(self) -> bool:
        """Starts recording audio from microphone."""
        # Stop any active speaking before listening
        self.tts.stop()
        success = self.audio_manager.start_recording()
        if success:
            self.listening_state_changed.emit(True)
            self.status_changed.emit("Listening...")
        return success

    def stop_listening(self) -> None:
        """Stops recording and launches speech-to-text transcription."""
        if not self.audio_manager.is_recording:
            return

        self.listening_state_changed.emit(False)
        audio_data = self.audio_manager.stop_recording()

        if audio_data is not None and len(audio_data) >= 1600:  # At least 0.1s
            self.status_changed.emit("Processing...")
            self.speech_recognizer.transcribe_async(audio_data)
        else:
            self.status_changed.emit("Ready")

    def toggle_listening(self) -> bool:
        """Toggles microphone recording state."""
        if self.audio_manager.is_recording:
            self.stop_listening()
            return False
        else:
            return self.start_listening()

    def _handle_transcription_finished(self, text: str) -> None:
        """Invoked when Faster-Whisper completes transcription."""
        self.status_changed.emit("Ready")
        self.transcription_ready.emit(text)

    def stop_speaking(self) -> None:
        """Immediately halts any speech synthesis or audio playback."""
        self.tts.stop()
        self.status_changed.emit("Ready")

    def toggle_mute(self) -> bool:
        """Toggles TTS mute state and returns True if muted."""
        muted = self.tts.toggle_muted()
        return muted

    @property
    def is_muted(self) -> bool:
        return self.tts.is_muted

    @property
    def is_listening(self) -> bool:
        return self.audio_manager.is_recording

    @property
    def is_speaking(self) -> bool:
        return self.tts.is_speaking

    # ---------------------------------------------------------
    # System & Memory Helpers
    # ---------------------------------------------------------

    def check_health(self) -> ModelStatus:
        """Queries Ollama status and emits health update."""
        status = self.model_manager.check_health()
        self.health_checked.emit(status)
        return status

    def start_new_conversation(self, title: str = "New Chat") -> str:
        """Clears active screen context and initiates a new session."""
        self.tts.stop()
        conv_id = self.conversation.start_new_conversation(title=title)
        self.status_changed.emit("Ready")
        return conv_id

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Returns messages for active conversation."""
        return self.conversation.get_display_messages()
