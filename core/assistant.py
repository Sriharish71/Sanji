"""
Assistant Coordinator for SANJI.
Orchestrates AI Engine, Conversation State, Model Health, and Memory Persistence.
Acts as the central controller between UI and backend subsystems.
"""

from typing import Any, Dict, List, Optional
from PySide6.QtCore import QObject, Signal

from config import settings
from core.ai_engine import AIEngine
from core.conversation_manager import ConversationManager
from core.model_manager import ModelManager, ModelStatus
from memory.database import Database
from memory.memory_manager import MemoryManager
from utils.logger import logger


class Assistant(QObject):
    """Primary business logic controller for SANJI."""

    # UI Notifications
    chunk_received = Signal(str)
    response_finished = Signal(str)
    error_occurred = Signal(str)
    status_changed = Signal(str)
    health_checked = Signal(object)  # ModelStatus object

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

        logger.info("SANJI Assistant coordinator initialized successfully.")

    def _wire_engine_signals(self) -> None:
        """Connects engine worker signals to assistant coordinator signals."""
        self.ai_engine.chunk_received.connect(self.chunk_received)
        self.ai_engine.status_changed.connect(self.status_changed)
        self.ai_engine.response_finished.connect(self._handle_response_finished)
        self.ai_engine.error_occurred.connect(self._handle_error_occurred)

    def send_prompt(self, user_text: str) -> None:
        """
        Processes a user message: records to memory, prepares context,
        and launches async streaming generation.
        """
        trimmed = user_text.strip()
        if not trimmed:
            return

        # 1. Persist user message to memory
        self.conversation.add_user_message(trimmed)

        # 2. Prepare context payload
        payload = self.conversation.build_llm_payload()

        # 3. Launch generation
        self.status_changed.emit("SANJI is generating response...")
        self.ai_engine.generate(payload)

    def _handle_response_finished(self, full_response: str) -> None:
        """Saves generated answer into database upon completion."""
        # Persist assistant response
        self.conversation.add_assistant_message(
            content=full_response,
            model=self.ai_engine.model
        )
        self.status_changed.emit("Ready")
        self.response_finished.emit(full_response)

    def _handle_error_occurred(self, error_message: str) -> None:
        """Handles engine errors gracefully."""
        self.status_changed.emit("Error")
        self.error_occurred.emit(error_message)

    def check_health(self) -> ModelStatus:
        """Queries Ollama status and emits health update."""
        status = self.model_manager.check_health()
        self.health_checked.emit(status)
        return status

    def start_new_conversation(self, title: str = "New Chat") -> str:
        """Clears active screen context and initiates a new session."""
        conv_id = self.conversation.start_new_conversation(title=title)
        self.status_changed.emit("New session initialized")
        return conv_id

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Returns messages for active conversation."""
        return self.conversation.get_display_messages()

