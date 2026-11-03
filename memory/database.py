"""
SQLite database engine for SANJI.
Handles connection pooling, table creations, and migrations safely.
"""

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Optional

from utils.logger import logger


class Database:
    """Thread-safe SQLite connection and schema manager."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.init_schema()

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Provides a managed SQLite connection with WAL mode and foreign keys enabled."""
        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        try:
            with self._lock:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA foreign_keys=ON;")
            yield conn
            conn.commit()
        except Exception as err:
            conn.rollback()
            logger.error(f"Database transaction error: {err}")
            raise
        finally:
            conn.close()

    def init_schema(self) -> None:
        """Initializes all necessary database tables for SANJI Phase 1 and future phases."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Conversations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1
                );
            """)

            # 2. Messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('system', 'user', 'assistant', 'tool')),
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    model TEXT,
                    tokens INTEGER DEFAULT 0,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                );
            """)

            # 3. Application Settings & Preferences Key-Value Store
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)

            # 4. Long-term / Semantic Facts (Reserved for future memory enhancement)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    fact TEXT NOT NULL,
                    importance INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL
                );
            """)

            # Indexes for high performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_ts ON messages(timestamp);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conv_updated ON conversations(updated_at);")

            logger.info(f"Database initialized successfully at {self.db_path}")


def utc_now_iso() -> str:
    """Helper to return ISO 8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()
