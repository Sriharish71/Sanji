"""
Unit and integration test suite for SANJI Phase 1 core architecture.
Verifies Configuration, Database, Memory, Conversation Manager, and Model Manager.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add project root
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import unittest
from config import Settings
from memory.database import Database
from memory.memory_manager import MemoryManager
from core.conversation_manager import ConversationManager
from core.model_manager import ModelManager


class TestSanjiCore(unittest.TestCase):
    """Test suite for core components."""

    def setUp(self):
        # Create temporary database file for isolated testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_sanji.db"
        self.db = Database(self.db_path)
        self.memory = MemoryManager(self.db)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_database_initialization(self):
        """Verify SQLite database schema and tables."""
        self.assertTrue(self.db_path.exists())
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row["name"] for row in cursor.fetchall()]

        self.assertIn("conversations", tables)
        self.assertIn("messages", tables)
        self.assertIn("settings", tables)
        self.assertIn("memory_facts", tables)

    def test_memory_conversations_and_messages(self):
        """Verify conversation creation, message storage, and chronological retrieval."""
        conv_id = self.memory.create_conversation("Unit Test Session")
        self.assertTrue(bool(conv_id))

        # Add messages
        msg1_id = self.memory.add_message(conv_id, "user", "Hello SANJI!")
        msg2_id = self.memory.add_message(conv_id, "assistant", "Greetings. How can I assist?", model="qwen2.5:3b")

        self.assertGreater(msg1_id, 0)
        self.assertGreater(msg2_id, msg1_id)

        # Retrieve messages
        recent = self.memory.get_recent_messages(conv_id, limit=10)
        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[0]["role"], "user")
        self.assertEqual(recent[0]["content"], "Hello SANJI!")
        self.assertEqual(recent[1]["role"], "assistant")
        self.assertEqual(recent[1]["content"], "Greetings. How can I assist?")

    def test_settings_storage(self):
        """Verify key-value persistence in settings table."""
        self.memory.set_setting("theme", "jarvis_dark")
        val = self.memory.get_setting("theme")
        self.assertEqual(val, "jarvis_dark")

        # Update setting
        self.memory.set_setting("theme", "jarvis_cyan")
        val_updated = self.memory.get_setting("theme")
        self.assertEqual(val_updated, "jarvis_cyan")

        # Non-existent key default
        self.assertEqual(self.memory.get_setting("non_existent", "default_val"), "default_val")

    def test_conversation_manager_payload(self):
        """Verify system prompt and dialog history payload compilation for Ollama."""
        conv_mgr = ConversationManager(
            memory_manager=self.memory,
            system_prompt="You are SANJI."
        )
        conv_mgr.add_user_message("What is your name?")
        conv_mgr.add_assistant_message("I am SANJI.")

        payload = conv_mgr.build_llm_payload()

        self.assertEqual(len(payload), 3)
        self.assertEqual(payload[0]["role"], "system")
        self.assertEqual(payload[0]["content"], "You are SANJI.")
        self.assertEqual(payload[1]["role"], "user")
        self.assertEqual(payload[1]["content"], "What is your name?")
        self.assertEqual(payload[2]["role"], "assistant")
        self.assertEqual(payload[2]["content"], "I am SANJI.")

    def test_model_manager_offline_graceful_handling(self):
        """Verify ModelManager handles offline local service without crashing."""
        # Point to port where Ollama is definitely not listening
        mgr = ModelManager(base_url="http://localhost:59999", target_model="qwen2.5:3b")
        status = mgr.check_health()

        self.assertFalse(status.service_available)
        self.assertFalse(status.target_model_installed)
        self.assertIn("not running", status.status_message.lower())

    def test_config_defaults(self):
        """Verify Pydantic configuration defaults and validation."""
        cfg = Settings.load()
        self.assertEqual(cfg.app_name, "SANJI")
        self.assertEqual(cfg.ollama_model, "qwen2.5:3b")
        self.assertTrue(cfg.ollama_base_url.startswith("http"))


if __name__ == "__main__":
    unittest.main()

