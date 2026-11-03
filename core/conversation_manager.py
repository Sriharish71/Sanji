"""
Conversation Manager for SANJI.
Handles active dialogue state, history truncation/context window maintenance,
and payload preparation for Ollama chat APIs.
"""

from typing import Any, Dict, List, Optional
from config import settings
from memory.memory_manager import MemoryManager
from utils.logger import logger


class ConversationManager:
    """Maintains active conversation sessions and prepares chat payloads."""

    def __init__(self, memory_manager: MemoryManager, system_prompt: Optional[str] = None):
        self.memory = memory_manager
        self.system_prompt = system_prompt or settings.system_prompt
        self.active_conversation_id: str = self.memory.get_or_create_active_conversation()
        self.max_history = settings.max_history_messages

    def set_active_conversation(self, conversation_id: str) -> None:
        """Switches the active conversation session."""
        self.active_conversation_id = conversation_id
        logger.info(f"Switched active conversation to: {conversation_id}")

    def start_new_conversation(self, title: str = "New Session") -> str:
        """Initiates a fresh conversation session."""
        new_id = self.memory.create_conversation(title=title)
        self.active_conversation_id = new_id
        return new_id

    def add_user_message(self, content: str) -> int:
        """Records a user prompt in memory."""
        return self.memory.add_message(
            conversation_id=self.active_conversation_id,
            role="user",
            content=content
        )

    def add_assistant_message(self, content: str, model: Optional[str] = None) -> int:
        """Records a SANJI response in memory."""
        return self.memory.add_message(
            conversation_id=self.active_conversation_id,
            role="assistant",
            content=content,
            model=model
        )

    def build_llm_payload(self) -> List[Dict[str, str]]:
        """
        Constructs the messages array for Ollama `/api/chat`.
        Injects the system prompt followed by the most recent conversation history.
        """
        payload: List[Dict[str, str]] = []

        # 1. System Prompt (SANJI Persona)
        if self.system_prompt:
            payload.append({
                "role": "system",
                "content": self.system_prompt
            })

        # 2. Recent Dialog History
        recent = self.memory.get_recent_messages(
            conversation_id=self.active_conversation_id,
            limit=self.max_history
        )

        for msg in recent:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant"):
                payload.append({
                    "role": role,
                    "content": content
                })

        return payload

    def get_display_messages(self) -> List[Dict[str, Any]]:
        """Returns all messages in the active conversation for the UI chat feed."""
        return self.memory.get_all_messages_for_conversation(self.active_conversation_id)
