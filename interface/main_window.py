"""
Main application window for SANJI HUD.
Integrates Sidebar, Chat Feed, Stacked Views, and Assistant Business Logic.
"""

from typing import Optional
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from config import settings
from core.assistant import Assistant
from core.model_manager import ModelStatus
from interface.chat_widget import ChatWidget
from interface.sidebar import SidebarWidget
from interface.styles import COLORS, THEME_STYLESHEET
from utils.logger import logger


class MemoryView(QWidget):
    """View displaying persistent SQLite conversation history, sessions, and memory statistics."""

    def __init__(self, assistant: Assistant, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.assistant = assistant
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("CONVERSATION MEMORY & PERSISTENCE")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['accent_cyan']}; letter-spacing: 1px;")
        layout.addWidget(title)

        self.memory_display = QTextEdit()
        self.memory_display.setReadOnly(True)
        self.memory_display.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_surface']};
                border: 1px solid {COLORS['border_subtle']};
                border-radius: 8px;
                padding: 16px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
                color: {COLORS['text_primary']};
            }}
        """)
        layout.addWidget(self.memory_display, 1)

    def refresh(self) -> None:
        """Reloads conversation sessions and message logs from SQLite database."""
        conversations = self.assistant.memory.list_conversations(limit=20)
        current_conv_id = self.assistant.conversation.active_conversation_id
        messages = self.assistant.get_conversation_history()

        lines = [
            "===========================================================",
            "             SANJI SQLITE PERSISTENCE TELEMETRY            ",
            "===========================================================",
            f"Database File         : {settings.get_resolved_db_path()}",
            f"Active Session ID     : {current_conv_id}",
            f"Active Session Msgs   : {len(messages)} message(s)",
            f"Max Context Sliding   : {settings.max_history_messages} turns",
            "-----------------------------------------------------------",
            "STORED CONVERSATIONS (Recent 20):",
        ]

        if conversations:
            for c in conversations:
                active_mark = " [CURRENT ACTIVE]" if c["id"] == current_conv_id else ""
                lines.append(f"  • [{c['updated_at'][-8:-3]}] {c['title']} (ID: {c['id'][:8]}...){active_mark}")
        else:
            lines.append("  (No stored sessions yet)")

        lines.extend([
            "-----------------------------------------------------------",
            "ACTIVE SESSION MESSAGES SUMMARY:",
        ])

        if messages:
            for m in messages:
                snippet = m["content"].replace("\n", " ")[:65]
                lines.append(f"  [{m['role'].upper()}] {snippet}...")
        else:
            lines.append("  (Session buffer is empty)")

        lines.append("===========================================================")
        self.memory_display.setPlainText("\n".join(lines))


class DiagnosticsView(QWidget):
    """View displaying detailed Ollama health, system parameters, and setup guidance."""

    def __init__(self, assistant: Assistant, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.assistant = assistant
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("SYSTEM DIAGNOSTICS & HARDWARE INTEL")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['accent_cyan']}; letter-spacing: 1px;")
        layout.addWidget(title)

        self.info_box = QTextEdit()
        self.info_box.setReadOnly(True)
        self.info_box.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_surface']};
                border: 1px solid {COLORS['border_subtle']};
                border-radius: 8px;
                padding: 16px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
                color: {COLORS['text_primary']};
            }}
        """)
        layout.addWidget(self.info_box, 1)

    def refresh(self, status: ModelStatus) -> None:
        """Populates diagnostic panel with up-to-date hardware and model telemetry."""
        lines = [
            "===========================================================",
            "              SANJI CORE SYSTEM DIAGNOSTICS                ",
            "===========================================================",
            f"Application Name      : {settings.app_name} v{settings.app_version}",
            f"Environment           : {settings.env.upper()}",
            f"Target Model          : {status.target_model}",
            f"Ollama Endpoint       : {settings.ollama_base_url}",
            f"Service Status        : {'ONLINE' if status.service_available else 'OFFLINE (Not reachable)'}",
            f"Ping Latency          : {f'{status.ping_latency_ms} ms' if status.ping_latency_ms else 'N/A'}",
            f"Target Model Status   : {'FOUND & READY' if status.target_model_installed else 'NOT FOUND'}",
            f"Database Location     : {settings.get_resolved_db_path()}",
            "-----------------------------------------------------------",
            "INSTALLED LOCAL MODELS IN OLLAMA:",
        ]

        if status.installed_models:
            for m in status.installed_models:
                lines.append(f"  • {m}")
        else:
            lines.append("  (None detected)")

        lines.extend([
            "-----------------------------------------------------------",
            "OLLAMA SETUP INSTRUCTIONS:",
            "  1. If Ollama is offline, open Start Menu and launch 'Ollama'.",
            f"  2. To pull the target model, run: ollama run {status.target_model}",
            "  3. Check Windows taskbar notification area for the Ollama icon.",
            "===========================================================",
        ])

        self.info_box.setPlainText("\n".join(lines))


class MainWindow(QMainWindow):
    """Primary HUD container window for SANJI."""

    def __init__(self, assistant: Assistant):
        super().__init__()
        self.assistant = assistant
        self._init_window()
        self._init_ui()
        self._wire_signals()

        # Initial startup routines
        QTimer.singleShot(100, self._startup_routine)

    def _init_window(self) -> None:
        self.setWindowTitle(f"{settings.app_name} — Autonomous AI Desktop Assistant")
        self.resize(1080, 720)
        self.setMinimumSize(850, 580)
        self.setStyleSheet(THEME_STYLESHEET)

    def _init_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Left Navigation Sidebar
        self.sidebar = SidebarWidget(self)
        root_layout.addWidget(self.sidebar)

        # Subtle vertical separator
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(f"background-color: {COLORS['border_subtle']}; max-width: 1px;")
        root_layout.addWidget(sep)

        # 2. Main Right Container
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Top Header Bar
        header_bar = QFrame()
        header_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_surface']};
                border-bottom: 1px solid {COLORS['border_subtle']};
                max-height: 48px;
            }}
        """)
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(20, 10, 20, 10)

        self.session_title_lbl = QLabel("ACTIVE HUD SESSION")
        self.session_title_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.session_title_lbl.setStyleSheet(f"color: {COLORS['accent_cyan']}; letter-spacing: 1px;")
        header_layout.addWidget(self.session_title_lbl)

        header_layout.addStretch()

        self.status_chip = QLabel("INITIALIZING...")
        self.status_chip.setObjectName("statusBadge")
        self.status_chip.setStyleSheet(f"""
            background-color: rgba(0, 240, 255, 0.1);
            color: {COLORS['accent_cyan']};
            border: 1px solid {COLORS['accent_cyan']};
        """)
        header_layout.addWidget(self.status_chip)

        right_layout.addWidget(header_bar)

        # Stacked Views (Chat vs Memory vs Diagnostics)
        self.stack = QStackedWidget()

        # View 0: Chat Interface
        self.chat_view = ChatWidget(self)
        self.stack.addWidget(self.chat_view)

        # View 1: Memory & History
        self.mem_view = MemoryView(self.assistant, self)
        self.stack.addWidget(self.mem_view)

        # View 2: Diagnostics
        self.diag_view = DiagnosticsView(self.assistant, self)
        self.stack.addWidget(self.diag_view)

        right_layout.addWidget(self.stack, 1)
        root_layout.addWidget(right_container, 1)

    def _wire_signals(self) -> None:
        """Connects UI and Assistant events."""
        # Chat user prompt -> Assistant
        self.chat_view.send_requested.connect(self.assistant.send_prompt)

        # Assistant streaming -> Chat UI
        self.assistant.chunk_received.connect(self.chat_view.append_streaming_token)
        self.assistant.response_finished.connect(self.chat_view.finish_streaming_response)
        self.assistant.error_occurred.connect(self.chat_view.display_error)

        # Status updates
        self.assistant.status_changed.connect(self._on_status_changed)
        self.assistant.health_checked.connect(self._on_health_checked)

        # Sidebar navigation
        self.sidebar.new_chat_requested.connect(self._on_new_chat)
        self.sidebar.refresh_health_requested.connect(self._check_health_async)

        self.sidebar.btn_chat.clicked.connect(lambda: self._switch_view(0))
        self.sidebar.btn_memory.clicked.connect(lambda: self._switch_view(1))
        self.sidebar.btn_diagnostics.clicked.connect(lambda: self._switch_view(2))

        # Voice Subsystem Signals (Phase 2)
        self.chat_view.mic_toggle_requested.connect(self.assistant.toggle_listening)
        self.chat_view.mute_toggle_requested.connect(self._on_toggle_mute)
        self.chat_view.stop_speech_requested.connect(self.assistant.stop_speaking)

        self.assistant.listening_state_changed.connect(self.chat_view.set_recording_state)
        self.assistant.volume_level_changed.connect(self.chat_view.update_volume_meter)
        self.assistant.transcription_ready.connect(self.chat_view.insert_transcribed_text)

    def _startup_routine(self) -> None:
        """Loads previous conversation messages and checks Ollama health."""
        # 1. Load history
        history = self.assistant.get_conversation_history()
        for msg in history:
            self.chat_view.add_message(
                role=msg.get("role", "user"),
                content=msg.get("content", ""),
                timestamp=msg.get("timestamp", "")[-8:-3] if msg.get("timestamp") else None
            )

        # If no history, show friendly welcome
        if not history:
            self.chat_view.add_message(
                role="assistant",
                content=(
                    "System initialized. I am SANJI, your autonomous AI desktop assistant.\n\n"
                    "Ready for command input or natural discussion."
                )
            )

        # 2. Check Ollama Health
        self._check_health_async()

        # 3. Initialize voice UI state
        self.chat_view.set_mute_state(self.assistant.is_muted)

    def _check_health_async(self) -> None:
        """Executes health check via timer to avoid startup hitch."""
        self.status_chip.setText("CHECKING HEALTH...")
        status = self.assistant.check_health()

    def _on_health_checked(self, status: ModelStatus) -> None:
        self.sidebar.update_status(status)
        self.diag_view.refresh(status)

        if status.service_available:
            if status.target_model_installed:
                self.status_chip.setText("CORE ONLINE")
                self.status_chip.setStyleSheet(f"""
                    background-color: rgba(0, 255, 170, 0.12);
                    color: {COLORS['status_online']};
                    border: 1px solid {COLORS['status_online']};
                """)
            else:
                self.status_chip.setText("MODEL MISSING")
                self.status_chip.setStyleSheet(f"""
                    background-color: rgba(255, 170, 0, 0.12);
                    color: {COLORS['status_thinking']};
                    border: 1px solid {COLORS['status_thinking']};
                """)
        else:
            self.status_chip.setText("OLLAMA OFFLINE")
            self.status_chip.setStyleSheet(f"""
                background-color: rgba(255, 51, 102, 0.12);
                color: {COLORS['status_offline']};
                border: 1px solid {COLORS['status_offline']};
            """)

    def _on_status_changed(self, msg: str) -> None:
        logger.debug(f"Status update: {msg}")
        self.chat_view.set_voice_status(msg)
        if msg in ("Listening...", "Processing...", "Speaking...", "Thinking..."):
            self.status_chip.setText(msg.upper())
        elif msg == "Ready":
            self.status_chip.setText("CORE ONLINE")

    def _on_toggle_mute(self) -> None:
        muted = self.assistant.toggle_mute()
        self.chat_view.set_mute_state(muted)

    def _on_new_chat(self) -> None:
        self.assistant.start_new_conversation()
        self.chat_view.clear_feed()
        self.chat_view.add_message(
            role="assistant",
            content="New session initialized. How can I assist you?"
        )
        self._switch_view(0)

    def _switch_view(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        self.sidebar.btn_chat.setChecked(index == 0)
        self.sidebar.btn_memory.setChecked(index == 1)
        self.sidebar.btn_diagnostics.setChecked(index == 2)
        if index == 1:
            self.mem_view.refresh()
        elif index == 2:
            self.assistant.check_health()

