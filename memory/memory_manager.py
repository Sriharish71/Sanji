"""
Memory Manager for SANJI.
Provides high-level APIs for conversations, message history, and settings storage.
"""

import uuid
from typing import Any, Dict, List, Optional
from memory.database import Database, utc_now_iso
from utils.logger import logger


class MemoryManager:
    """Orchestrates persistent storage for dialogues, user preferences, and memory."""

    def __init__(self, db: Database):
        self.db = db

    # ---------------------------------------------------------
    # Conversation Management
    # ---------------------------------------------------------

    def create_conversation(self, title: str = "New Session") -> str:
        """Creates a new conversation session and returns its unique ID."""
        conv_id = str(uuid.uuid4())
        now = utc_now_iso()
        with self.db.get_connection() as conn:
            conn.execute(
                "INSERT INTO conversations (id, title, created_at, updated_at, is_active) VALUES (?, ?, ?, ?, 1)",
                (conv_id, title, now, now)
            )
        logger.info(f"Created conversation '{title}' (ID: {conv_id})")
        return conv_id

    def get_or_create_active_conversation(self) -> str:
        """Retrieves the latest active conversation ID, or generates a new one."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM conversations WHERE is_active = 1 ORDER BY updated_at DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                return row["id"]

        return self.create_conversation(title="Active Session")

    def update_conversation_title(self, conversation_id: str, new_title: str) -> None:
        """Updates the title of an existing conversation."""
        now = utc_now_iso()
        with self.db.get_connection() as conn:
            conn.execute(
                "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
                (new_title, now, conversation_id)
            )

    def list_conversations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Lists recent conversations."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    # ---------------------------------------------------------
    # Message Storage & Context Retrieval
    # ---------------------------------------------------------

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        model: Optional[str] = None,
        tokens: int = 0
    ) -> int:
        """Stores a message and updates the parent conversation's timestamp."""
        now = utc_now_iso()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO messages (conversation_id, role, content, timestamp, model, tokens)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (conversation_id, role, content, now, model, tokens)
            )
            msg_id = cursor.lastrowid
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id)
            )
        return msg_id

    def get_recent_messages(self, conversation_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieves the most recent messages for context generation.
        Returns them in chronological order (oldest to newest).
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, role, content, timestamp, model
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (conversation_id, limit)
            )
            rows = cursor.fetchall()

        # Reverse so chronological order is preserved for LLM context
        return [dict(r) for r in reversed(rows)]

    def get_all_messages_for_conversation(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Retrieves all messages for displaying in the chat interface."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, role, content, timestamp, model
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id ASC
                """,
                (conversation_id,)
            )
            return [dict(r) for r in cursor.fetchall()]

    def clear_conversation_messages(self, conversation_id: str) -> None:
        """Deletes all messages inside a specific conversation."""
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        logger.info(f"Cleared messages for conversation {conversation_id}")

    # ---------------------------------------------------------
    # Key-Value Settings Store
    # ---------------------------------------------------------

    def set_setting(self, key: str, value: str) -> None:
        """Upserts a setting key-value pair."""
        now = utc_now_iso()
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (key, value, now)
            )

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Reads a setting value."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

