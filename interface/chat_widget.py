"""
Chat widget for SANJI HUD.
Renders conversational message bubbles, streaming text generation,
AI thinking animations, and message input.
"""

from datetime import datetime
from typing import Optional
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QKeyEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from interface.styles import COLORS


class ChatInputField(QTextEdit):
    """Custom QTextEdit that triggers send on Return/Enter (Shift+Enter for newline)."""
    return_pressed = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("chatInput")
        self.setPlaceholderText("Ask SANJI anything... (Enter to send, Shift+Enter for newline)")
        self.setFixedHeight(75)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() & Qt.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.return_pressed.emit()
        else:
            super().keyPressEvent(event)


class MessageBubble(QFrame):
    """Visual bubble for user or assistant messages."""

    def __init__(self, role: str, content: str, timestamp: Optional[str] = None):
        super().__init__()
        self.role = role
        self.timestamp = timestamp or datetime.now().strftime("%H:%M")
        self._init_ui(content)

    def _init_ui(self, content: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        # Header with Role and Timestamp
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        sender_label = QLabel("SANJI" if self.role == "assistant" else "YOU")
        sender_label.setFont(QFont("Segoe UI", 9, QFont.Bold))

        time_label = QLabel(self.timestamp)
        time_label.setFont(QFont("Segoe UI", 8))
        time_label.setStyleSheet(f"color: {COLORS['text_muted']};")

        if self.role == "assistant":
            sender_label.setStyleSheet(f"color: {COLORS['accent_cyan']}; letter-spacing: 1px;")
            header_layout.addWidget(sender_label)
            header_layout.addSpacing(8)
            header_layout.addWidget(time_label)
            header_layout.addStretch()

            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['bg_bubble_sanji']};
                    border: 1px solid {COLORS['border_subtle']};
                    border-left: 3px solid {COLORS['accent_cyan']};
                    border-radius: 8px;
                }}
            """)
        else:
            sender_label.setStyleSheet(f"color: {COLORS['accent_blue']}; letter-spacing: 1px;")
            header_layout.addStretch()
            header_layout.addWidget(time_label)
            header_layout.addSpacing(8)
            header_layout.addWidget(sender_label)

            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['bg_bubble_user']};
                    border: 1px solid {COLORS['border_subtle']};
                    border-right: 3px solid {COLORS['accent_blue']};
                    border-radius: 8px;
                }}
            """)

        layout.addLayout(header_layout)

        # Body Text
        self.body_label = QLabel(content)
        self.body_label.setWordWrap(True)
        self.body_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.body_label.setFont(QFont("Segoe UI", 10))
        self.body_label.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent; border: none;")

        layout.addWidget(self.body_label)

    def set_content(self, text: str) -> None:
        """Dynamically updates content during streaming."""
        self.body_label.setText(text)


class ThinkingIndicator(QFrame):
    """Futuristic animated pulse indicator showing AI generation activity."""

    def __init__(self):
        super().__init__()
        self.dot_count = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate_dots)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)

        self.label = QLabel("SANJI IS PROCESSING")
        self.label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.label.setStyleSheet(f"color: {COLORS['status_thinking']}; letter-spacing: 1.5px;")

        layout.addWidget(self.label)
        layout.addStretch()

        self.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(255, 170, 0, 0.08);
                border: 1px dashed {COLORS['status_thinking']};
                border-radius: 6px;
            }}
        """)
        self.hide()

    def start(self, message: str = "SANJI IS THINKING") -> None:
        self.dot_count = 0
        self.base_message = message
        self.label.setText(message)
        self.show()
        self.timer.start(350)

    def stop(self) -> None:
        self.timer.stop()
        self.hide()

    def _animate_dots(self) -> None:
        self.dot_count = (self.dot_count + 1) % 4
        dots = "." * self.dot_count
        self.label.setText(f"{self.base_message}{dots}")


class ChatWidget(QWidget):
    """Complete Chat Feed, Message Stream, and Input Controller."""

    send_requested = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_streaming_bubble: Optional[MessageBubble] = None
        self._streaming_buffer = ""
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. Message Scroll Feed Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.feed_container = QWidget()
        self.feed_layout = QVBoxLayout(self.feed_container)
        self.feed_layout.setContentsMargins(0, 0, 0, 0)
        self.feed_layout.setSpacing(14)
        self.feed_layout.addStretch()  # Pushes messages downward

        self.scroll_area.setWidget(self.feed_container)
        main_layout.addWidget(self.scroll_area, 1)

        # 2. Thinking Indicator
        self.thinking_indicator = ThinkingIndicator()
        main_layout.addWidget(self.thinking_indicator)

        # 3. Input Controls Bar
        input_container = QWidget()
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(10)

        self.input_field = ChatInputField()
        self.input_field.return_pressed.connect(self._on_send_clicked)

        self.send_button = QPushButton("SEND")
        self.send_button.setObjectName("sendButton")
        self.send_button.setCursor(Qt.PointingHandCursor)
        self.send_button.clicked.connect(self._on_send_clicked)

        input_layout.addWidget(self.input_field, 1)
        input_layout.addWidget(self.send_button)

        main_layout.addWidget(input_container)

    def _on_send_clicked(self) -> None:
        text = self.input_field.toPlainText().strip()
        if not text:
            return

        self.input_field.clear()
        self.add_message("user", text)
        self.thinking_indicator.start("SANJI IS PROCESSING")
        self.send_button.setEnabled(False)
        self.send_requested.emit(text)

    def add_message(self, role: str, content: str, timestamp: Optional[str] = None) -> None:
        """Appends a new static message bubble to the chat feed."""
        bubble = MessageBubble(role=role, content=content, timestamp=timestamp)

        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)

        if role == "user":
            row_layout.addStretch(1)
            row_layout.addWidget(bubble, 4)
        else:
            row_layout.addWidget(bubble, 4)
            row_layout.addStretch(1)

        # Insert before the stretch at the bottom
        count = self.feed_layout.count()
        self.feed_layout.insertLayout(count - 1, row_layout)
        self.scroll_to_bottom()

    def start_streaming_response(self) -> None:
        """Prepares a new assistant bubble to receive incoming streaming tokens."""
        self.thinking_indicator.stop()
        self._streaming_buffer = ""

        self._current_streaming_bubble = MessageBubble(
            role="assistant",
            content="..."
        )

        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(self._current_streaming_bubble, 4)
        row_layout.addStretch(1)

        count = self.feed_layout.count()
        self.feed_layout.insertLayout(count - 1, row_layout)
        self.scroll_to_bottom()

    def append_streaming_token(self, chunk: str) -> None:
        """Appends streaming text chunk to active bubble."""
        if self._current_streaming_bubble is None:
            self.start_streaming_response()

        self._streaming_buffer += chunk
        self._current_streaming_bubble.set_content(self._streaming_buffer)
        self.scroll_to_bottom()

    def finish_streaming_response(self, full_text: str) -> None:
        """Completes active streaming response and re-enables input."""
        if self._current_streaming_bubble:
            self._current_streaming_bubble.set_content(full_text)
            self._current_streaming_bubble = None

        self._streaming_buffer = ""
        self.thinking_indicator.stop()
        self.send_button.setEnabled(True)
        self.input_field.setFocus()
        self.scroll_to_bottom()

    def display_error(self, error_message: str) -> None:
        """Displays error alert in chat and re-enables UI."""
        self.thinking_indicator.stop()
        self.add_message("assistant", f"⚠️ System Alert:\n{error_message}")
        self._current_streaming_bubble = None
        self._streaming_buffer = ""
        self.send_button.setEnabled(True)
        self.scroll_to_bottom()

    def clear_feed(self) -> None:
        """Clears all message widgets from feed."""
        while self.feed_layout.count() > 1:
            item = self.feed_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # Recursively delete layouts
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

    def scroll_to_bottom(self) -> None:
        """Ensures the newest messages are automatically scrolled into view."""
        QTimer.singleShot(20, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))
