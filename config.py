"""
Configuration management for SANJI using Pydantic.
Loads settings from environment variables and .env file with safe defaults.
"""

from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

# Try to load .env if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import os


class Settings(BaseModel):
    """Central configuration for the SANJI Assistant application."""

    # Application Metadata
    app_name: str = Field(default="SANJI", description="Application display name")
    app_version: str = Field(default="1.0.0", description="Application version")
    env: str = Field(default="development", description="Environment: development, production")

    # Local AI (Ollama)
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Local Ollama HTTP service endpoint"
    )
    ollama_model: str = Field(
        default="qwen2.5:3b",
        description="Target LLM model tag in Ollama"
    )
    ollama_timeout_seconds: float = Field(
        default=90.0,
        description="Timeout for inference requests in seconds"
    )

    # Persona & Intelligence
    system_prompt: str = Field(
        default=(
            "You are SANJI, a personalized, intelligent, and highly capable AI desktop assistant for Windows 11. "
            "You are friendly, sharp, and confident. By default, give concise, direct, and thoughtful answers. "
            "Expand into depth only when requested or when complex clarity is required. "
            "Address yourself as SANJI."
        ),
        description="Initial system prompt defining SANJI's core persona"
    )

    # Memory & Database
    database_path: str = Field(
        default="memory/sanji.db",
        description="Relative or absolute path to persistent SQLite database"
    )
    max_history_messages: int = Field(
        default=20,
        description="Number of recent messages to inject for conversational context"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)")
    log_file: str = Field(default="sanji.log", description="Log file output path")

    @classmethod
    def load(cls) -> "Settings":
        """Instantiate Settings from OS environment variables with fallback defaults."""
        return cls(
            app_name=os.getenv("APP_NAME", "SANJI"),
            app_version=os.getenv("APP_VERSION", "1.0.0"),
            env=os.getenv("SANJI_ENV", "development"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
            ollama_timeout_seconds=float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "90.0")),
            system_prompt=os.getenv(
                "SYSTEM_PROMPT",
                (
                    "You are SANJI, a personalized, intelligent, and highly capable AI desktop assistant for Windows 11. "
                    "You are friendly, sharp, and confident. By default, give concise, direct, and thoughtful answers. "
                    "Expand into depth only when requested or when complex clarity is required. "
                    "Address yourself as SANJI."
                )
            ),
            database_path=os.getenv("DATABASE_PATH", "memory/sanji.db"),
            max_history_messages=int(os.getenv("MAX_HISTORY_MESSAGES", "20")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE", "sanji.log"),
        )

    def get_resolved_db_path(self, base_dir: Optional[Path] = None) -> Path:
        """Resolve database path relative to the project root directory."""
        db_p = Path(self.database_path)
        if db_p.is_absolute():
            return db_p
        root = base_dir or Path(__file__).resolve().parent
        resolved = root / db_p
        resolved.parent.mkdir(parents=True, exist_ok=True)
        return resolved


# Global singleton instance
settings = Settings.load()

