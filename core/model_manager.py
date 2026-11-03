"""
Model Manager for SANJI.
Handles Ollama service connectivity checks, model inventory verification,
and diagnostic status reporting.
"""

import time
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel
import requests

from config import settings
from utils.logger import logger


class ModelStatus(BaseModel):
    """Detailed health and model availability snapshot."""
    service_available: bool = False
    status_message: str = "Checking status..."
    installed_models: List[str] = []
    target_model_installed: bool = False
    ping_latency_ms: Optional[float] = None
    target_model: str = settings.ollama_model


class ModelManager:
    """Monitors and manages connection to local Ollama runtime and models."""

    def __init__(self, base_url: Optional[str] = None, target_model: Optional[str] = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.target_model = target_model or settings.ollama_model

    def check_health(self) -> ModelStatus:
        """
        Pings Ollama service and queries installed models.
        Returns a ModelStatus model with current state diagnostics.
        """
        start = time.perf_counter()
        tags_url = f"{self.base_url}/api/tags"

        try:
            response = requests.get(tags_url, timeout=3.0)
            latency = round((time.perf_counter() - start) * 1000, 1)

            if response.status_code == 200:
                data = response.json()
                raw_models = data.get("models", [])
                # Extract model names and clean tags
                installed_names = [m.get("name", "") for m in raw_models]

                # Check if target model (e.g. 'qwen2.5:3b') or base match exists
                target_base = self.target_model.split(":")[0]
                target_installed = any(
                    self.target_model == name or name.startswith(f"{target_base}:")
                    for name in installed_names
                )

                if target_installed:
                    msg = f"Online • Model {self.target_model} ready"
                elif installed_names:
                    msg = f"Online • Model {self.target_model} not found ({len(installed_names)} other model(s) available)"
                else:
                    msg = "Online • No models found. Run: ollama run qwen2.5:3b"

                return ModelStatus(
                    service_available=True,
                    status_message=msg,
                    installed_models=installed_names,
                    target_model_installed=target_installed,
                    ping_latency_ms=latency,
                    target_model=self.target_model
                )
            else:
                return ModelStatus(
                    service_available=False,
                    status_message=f"Ollama returned HTTP {response.status_code}",
                    installed_models=[],
                    target_model_installed=False,
                    ping_latency_ms=latency,
                    target_model=self.target_model
                )

        except requests.exceptions.ConnectionError:
            return ModelStatus(
                service_available=False,
                status_message="Ollama service is not running (Offline)",
                installed_models=[],
                target_model_installed=False,
                ping_latency_ms=None,
                target_model=self.target_model
            )
        except requests.exceptions.Timeout:
            return ModelStatus(
                service_available=False,
                status_message="Connection to Ollama timed out (>3s)",
                installed_models=[],
                target_model_installed=False,
                ping_latency_ms=None,
                target_model=self.target_model
            )
        except Exception as ex:
            logger.error(f"Error checking Ollama status: {ex}")
            return ModelStatus(
                service_available=False,
                status_message=f"Error: {str(ex)[:40]}",
                installed_models=[],
                target_model_installed=False,
                ping_latency_ms=None,
                target_model=self.target_model
            )

    def get_setup_instructions(self) -> str:
        """Returns friendly markdown instructions for starting or installing Ollama."""
        return (
            "### Ollama Setup Guide\n\n"
            "1. **Download & Install Ollama**:\n"
            "   Visit [https://ollama.com/download](https://ollama.com/download) and install the Windows client.\n\n"
            "2. **Download Model (Qwen 2.5 3B)**:\n"
            "   Open PowerShell or Terminal and run:\n"
            f"   ```bash\n   ollama run {self.target_model}\n   ```\n\n"
            "3. **Verify Service**:\n"
            "   Ensure the Ollama icon is running in your Windows taskbar system tray."
        )

