"""
Sidebar navigation and status monitor widget for SANJI HUD.
Features Arc Reactor inspired identity badge, system telemetry, and navigation controls.
"""

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from core.model_manager import ModelStatus
from interface.styles import COLORS


class ArcReactorBadge(QWidget):
    """Futuristic vector-drawn Arc Reactor / SANJI Core identity emblem."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(60, 60)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        center_x = self.width() / 2
        center_y = self.height() / 2

        # Outer cyber ring
        pen_outer = QPen(QColor(COLORS["accent_blue"]), 1.5, Qt.DashLine)
        painter.setPen(pen_outer)
        painter.drawEllipse(center_x - 26, center_y - 26, 52, 52)

        # Middle cyan glow ring
        pen_mid = QPen(QColor(COLORS["accent_cyan"]), 2.0)
        painter.setPen(pen_mid)
        painter.drawEllipse(center_x - 18, center_y - 18, 36, 36)

        # Core reactor dot
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(COLORS["accent_cyan"]))
        painter.drawEllipse(center_x - 8, center_y - 8, 16, 16)

        # Inner white energy pulse
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(center_x - 4, center_y - 4, 8, 8)


class SidebarWidget(QWidget):
    """Left navigation panel with system telemetry and session controls."""

    new_chat_requested = Signal()
    refresh_health_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedWidth(260)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(18)

        # 1. Identity Header (Arc Reactor + SANJI branding)
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        self.reactor = ArcReactorBadge()
        header_layout.addWidget(self.reactor)

        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 4, 0, 4)
        title_layout.setSpacing(2)

        app_title = QLabel("SANJI")
        app_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        app_title.setStyleSheet(f"color: {COLORS['accent_cyan']}; letter-spacing: 2px;")

        app_sub = QLabel("AI DESKTOP ASSISTANT")
        app_sub.setFont(QFont("Segoe UI", 7, QFont.Bold))
        app_sub.setStyleSheet(f"color: {COLORS['text_muted']}; letter-spacing: 1px;")

        title_layout.addWidget(app_title)
        title_layout.addWidget(app_sub)

        header_layout.addWidget(title_container, 1)
        layout.addWidget(header_container)

        # Separator line
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setStyleSheet(f"background-color: {COLORS['border_subtle']}; max-height: 1px;")
        layout.addWidget(sep1)

        # 2. Action Controls
        self.new_chat_btn = QPushButton("+ NEW SESSION")
        self.new_chat_btn.setObjectName("newChatButton")
        self.new_chat_btn.setCursor(Qt.PointingHandCursor)
        self.new_chat_btn.clicked.connect(self.new_chat_requested)
        layout.addWidget(self.new_chat_btn)

        # 3. Navigation Links
        nav_container = QWidget()
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 8, 0, 8)
        nav_layout.setSpacing(6)

        self.btn_chat = QPushButton("◈  Chat Interface")
        self.btn_chat.setProperty("class", "nav-button")
        self.btn_chat.setCheckable(True)
        self.btn_chat.setChecked(True)

        self.btn_memory = QPushButton("◈  Memory & History")
        self.btn_memory.setProperty("class", "nav-button")
        self.btn_memory.setCheckable(True)

        self.btn_diagnostics = QPushButton("◈  System Diagnostics")
        self.btn_diagnostics.setProperty("class", "nav-button")
        self.btn_diagnostics.setCheckable(True)

        nav_layout.addWidget(self.btn_chat)
        nav_layout.addWidget(self.btn_memory)
        nav_layout.addWidget(self.btn_diagnostics)
        layout.addWidget(nav_container)

        layout.addStretch()

        # 4. Telemetry & Hardware Status Box
        status_box = QFrame()
        status_box.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_surface']};
                border: 1px solid {COLORS['border_subtle']};
                border-radius: 8px;
            }}
        """)
        status_box_layout = QVBoxLayout(status_box)
        status_box_layout.setContentsMargins(12, 12, 12, 12)
        status_box_layout.setSpacing(8)

        status_header = QLabel("SYSTEM TELEMETRY")
        status_header.setFont(QFont("Segoe UI", 8, QFont.Bold))
        status_header.setStyleSheet(f"color: {COLORS['text_muted']}; letter-spacing: 1px;")
        status_box_layout.addWidget(status_header)

        # Ollama Service Row
        service_row = QHBoxLayout()
        service_label = QLabel("Ollama:")
        service_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.service_status = QLabel("Checking...")
        self.service_status.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.service_status.setStyleSheet(f"color: {COLORS['status_thinking']};")
        service_row.addWidget(service_label)
        service_row.addStretch()
        service_row.addWidget(self.service_status)
        status_box_layout.addLayout(service_row)

        # Active Model Row
        model_row = QHBoxLayout()
        model_label = QLabel("Model:")
        model_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.model_status = QLabel("qwen2.5:3b")
        self.model_status.setStyleSheet(f"color: {COLORS['text_primary']}; font-family: Consolas, monospace;")
        model_row.addWidget(model_label)
        model_row.addStretch()
        model_row.addWidget(self.model_status)
        status_box_layout.addLayout(model_row)

        # Latency Row
        latency_row = QHBoxLayout()
        latency_label = QLabel("Ping:")
        latency_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.latency_val = QLabel("-- ms")
        self.latency_val.setStyleSheet(f"color: {COLORS['text_muted']};")
        latency_row.addWidget(latency_label)
        latency_row.addStretch()
        latency_row.addWidget(self.latency_val)
        status_box_layout.addLayout(latency_row)

        # Refresh button
        self.refresh_btn = QPushButton("↺ Check Health")
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['bg_panel']};
                color: {COLORS['accent_cyan']};
                border: 1px solid {COLORS['border_subtle']};
                border-radius: 4px;
                padding: 4px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                border-color: {COLORS['accent_cyan']};
            }}
        """)
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh_health_requested)
        status_box_layout.addWidget(self.refresh_btn)

        layout.addWidget(status_box)

    def update_status(self, status: ModelStatus) -> None:
        """Refreshes telemetry panel based on active ModelStatus."""
        if status.service_available:
            if status.target_model_installed:
                self.service_status.setText("ONLINE")
                self.service_status.setStyleSheet(f"color: {COLORS['status_online']}; font-weight: bold;")
            else:
                self.service_status.setText("NO MODEL")
                self.service_status.setStyleSheet(f"color: {COLORS['status_thinking']}; font-weight: bold;")
        else:
            self.service_status.setText("OFFLINE")
            self.service_status.setStyleSheet(f"color: {COLORS['status_offline']}; font-weight: bold;")

        self.model_status.setText(status.target_model)

        if status.ping_latency_ms is not None:
            self.latency_val.setText(f"{status.ping_latency_ms} ms")
        else:
            self.latency_val.setText("-- ms")

