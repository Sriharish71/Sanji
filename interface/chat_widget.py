"""
Chat widget for SANJI HUD.
Renders conversational message bubbles, streaming text generation,
voice waveform visualizer, microphone controls, and TTS playback options.
"""

from datetime import datetime
from typing import Optional
import numpy as np
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QFont, QKeyEvent, QPainter, QPen
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


class VoiceWaveVisualizer(QWidget):
    """Futuristic multi-bar audio waveform visualizer for microphone & speaker telemetry."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(24)
        self.setFixedWidth(120)
        self.num_bars = 7
        self.levels = [0.1] * self.num_bars
        self.is_active = False
        self.decay_timer = QTimer(self)
        self.decay_timer.timeout.connect(self._decay)
        self.decay_timer.start(50)

    def set_level(self, normalized_level: float) -> None:
        """Updates bar heights from normalized audio energy (0.0 to 1.0)."""
        self.is_active = normalized_level > 0.05
        # Generate symmetrical frequency-style heights
        mid = self.num_bars // 2
        for i in range(self.num_bars):
            dist = abs(i - mid) / mid
            factor = max(0.2, 1.0 - (dist * 0.5))
            target = max(0.1, min(1.0, normalized_level * factor * np.random.uniform(0.8, 1.2)))
            self.levels[i] = max(self.levels[i] * 0.4 + target * 0.6, 0.1)
        self.update()

    def _decay(self) -> None:
        """Smoothly decays bars when silence occurs."""
        changed = False
        for i in range(self.num_bars):
            if self.levels[i] > 0.12:
                self.levels[i] *= 0.85
                changed = True
            else:
                self.levels[i] = 0.10
        if changed:
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        bar_w = 4
        spacing = 5
        start_x = (w - (self.num_bars * (bar_w + spacing) - spacing)) / 2

        for i, lvl in enumerate(self.levels):
            x = start_x + i * (bar_w + spacing)
            bar_h = max(4.0, lvl * (h - 4))
            y = (h - bar_h) / 2

            if self.is_active:
                color = QColor(COLORS["accent_cyan"])
            else:
                color = QColor(COLORS["text_muted"])

            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(x, y, bar_w, bar_h, 2, 2)


class ChatInputField(QTextEdit):
    """Custom QTextEdit that triggers send on Return/Enter (Shift+Enter for newline)."""
    return_pressed = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("chatInput")
        self.setPlaceholderText("Ask SANJI anything or click 🎙 to speak... (Enter to send)")
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

        self.body_label = QLabel(content)
        self.body_label.setWordWrap(True)
        self.body_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.body_label.setFont(QFont("Segoe UI", 10))
        self.body_label.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent; border: none;")

        layout.addWidget(self.body_label)

    def set_content(self, text: str) -> None:
        """Dynamically updates content during streaming."""
        self.body_label.setText(text)


class StatusIndicatorBar(QFrame):
    """
    Multipurpose state indicator for:
    Ready, Listening, Processing, Thinking, Speaking, Error.
    """

    stop_speech_requested = Signal()

    def __init__(self):
        super().__init__()
        self.dot_count = 0
        self.current_state = "Ready"
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate_dots)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 14, 6)

        self.label = QLabel("READY")
        self.label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.label.setStyleSheet(f"color: {COLORS['status_online']}; letter-spacing: 1px;")
        layout.addWidget(self.label)

        # Audio visualizer in status bar
        self.visualizer = VoiceWaveVisualizer()
        layout.addWidget(self.visualizer)

        layout.addStretch()

        # Stop Speaking button
        self.stop_btn = QPushButton("⏹ STOP SPEECH")
        self.stop_btn.setObjectName("stopSpeechButton")
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.clicked.connect(self.stop_speech_requested)
        self.stop_btn.hide()
        layout.addWidget(self.stop_btn)

        self.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(13, 19, 31, 0.7);
                border: 1px solid {COLORS['border_subtle']};
                border-radius: 6px;
            }}
        """)
        self.hide()

    def set_status(self, state: str, detail: Optional[str] = None) -> None:
        """Switches display status and color scheme."""
        self.current_state = state
        self.timer.stop()
        self.stop_btn.hide()

        if state == "Ready":
            self.hide()
            return

        self.show()

        if state == "Listening...":
            self.label.setText("🎙 LISTENING TO MICROPHONE (Click Mic to Finish)")
            self.label.setStyleSheet(f"color: {COLORS['status_offline']}; font-weight: bold;")
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: rgba(255, 51, 102, 0.12);
                    border: 1px solid {COLORS['status_offline']};
                    border-radius: 6px;
                }}
            """)
        elif state == "Processing...":
            self.label.setText("⌛ TRANSCRIBING SPEECH VIA WHISPER...")
            self.label.setStyleSheet(f"color: {COLORS['status_thinking']}; font-weight: bold;")
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: rgba(255, 170, 0, 0.10);
                    border: 1px solid {COLORS['status_thinking']};
                    border-radius: 6px;
                }}
            """)
        elif state == "Thinking...":
            self.label.setText("⚡ SANJI IS THINKING...")
            self.label.setStyleSheet(f"color: {COLORS['accent_cyan']}; font-weight: bold;")
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: rgba(0, 240, 255, 0.08);
                    border: 1px solid {COLORS['accent_cyan']};
                    border-radius: 6px;
                }}
            """)
            self.timer.start(350)
        elif state == "Speaking...":
            self.label.setText("🔊 SANJI IS SPEAKING...")
            self.label.setStyleSheet(f"color: {COLORS['status_online']}; font-weight: bold;")
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: rgba(0, 255, 170, 0.10);
                    border: 1px solid {COLORS['status_online']};
                    border-radius: 6px;
                }}
            """)
            self.stop_btn.show()
        elif state == "Error":
            self.label.setText(f"⚠️ {detail or 'SYSTEM ALERT'}")
            self.label.setStyleSheet(f"color: {COLORS['status_offline']}; font-weight: bold;")
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: rgba(255, 51, 102, 0.15);
                    border: 1px solid {COLORS['status_offline']};
                    border-radius: 6px;
                }}
            """)

    def _animate_dots(self) -> None:
        self.dot_count = (self.dot_count + 1) % 4
        dots = "." * self.dot_count
        self.label.setText(f"⚡ SANJI IS THINKING{dots}")


class ChatWidget(QWidget):
    """Complete Chat Feed, Message Stream, Microphone, and Audio Controls."""

    send_requested = Signal(str)
    mic_toggle_requested = Signal()
    mute_toggle_requested = Signal()
    stop_speech_requested = Signal()

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
        self.feed_layout.addStretch()

        self.scroll_area.setWidget(self.feed_container)
        main_layout.addWidget(self.scroll_area, 1)

        # 2. Status & Waveform Bar
        self.status_bar = StatusIndicatorBar()
        self.status_bar.stop_speech_requested.connect(self.stop_speech_requested)
        main_layout.addWidget(self.status_bar)

        # 3. Input Controls Bar
        input_container = QWidget()
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(10)

        # Microphone Click-to-Speak Button
        self.mic_btn = QPushButton("🎙")
        self.mic_btn.setObjectName("micButton")
        self.mic_btn.setToolTip("Click to speak with SANJI")
        self.mic_btn.setCursor(Qt.PointingHandCursor)
        self.mic_btn.clicked.connect(self.mic_toggle_requested)

        # Input text area
        self.input_field = ChatInputField()
        self.input_field.return_pressed.connect(self._on_send_clicked)

        # Speaker Mute/Unmute Button
        self.mute_btn = QPushButton("🔊")
        self.mute_btn.setObjectName("muteButton")
        self.mute_btn.setToolTip("Toggle voice speech output")
        self.mute_btn.setCursor(Qt.PointingHandCursor)
        self.mute_btn.clicked.connect(self.mute_toggle_requested)

        # Send Button
        self.send_button = QPushButton("SEND")
        self.send_button.setObjectName("sendButton")
        self.send_button.setCursor(Qt.PointingHandCursor)
        self.send_button.clicked.connect(self._on_send_clicked)

        input_layout.addWidget(self.mic_btn)
        input_layout.addWidget(self.input_field, 1)
        input_layout.addWidget(self.mute_btn)
        input_layout.addWidget(self.send_button)

        main_layout.addWidget(input_container)

    def _on_send_clicked(self) -> None:
        text = self.input_field.toPlainText().strip()
        if not text:
            return

        self.input_field.clear()
        self.add_message("user", text)
        self.status_bar.set_status("Thinking...")
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

        count = self.feed_layout.count()
        self.feed_layout.insertLayout(count - 1, row_layout)
        self.scroll_to_bottom()

    def start_streaming_response(self) -> None:
        """Prepares a new assistant bubble to receive incoming streaming tokens."""
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
        self.send_button.setEnabled(True)
        self.input_field.setFocus()
        self.scroll_to_bottom()

    def display_error(self, error_message: str) -> None:
        """Displays error alert in chat and re-enables UI."""
        self.status_bar.set_status("Error", detail=error_message[:40])
        self.add_message("assistant", f"⚠️ System Alert:\n{error_message}")
        self._current_streaming_bubble = None
        self._streaming_buffer = ""
        self.send_button.setEnabled(True)
        self.scroll_to_bottom()

    def set_recording_state(self, is_recording: bool) -> None:
        """Updates mic button visual state when recording begins or halts."""
        self.mic_btn.setProperty("recording", "true" if is_recording else "false")
        self.mic_btn.style().unpolish(self.mic_btn)
        self.mic_btn.style().polish(self.mic_btn)
        if is_recording:
            self.mic_btn.setText("🔴")
            self.mic_btn.setToolTip("Recording... Click to stop and transcribe")
            self.status_bar.set_status("Listening...")
        else:
            self.mic_btn.setText("🎙")
            self.mic_btn.setToolTip("Click to speak with SANJI")

    def set_mute_state(self, is_muted: bool) -> None:
        """Updates speaker mute button icon and styling."""
        self.mute_btn.setProperty("muted", "true" if is_muted else "false")
        self.mute_btn.style().unpolish(self.mute_btn)
        self.mute_btn.style().polish(self.mute_btn)
        self.mute_btn.setText("🔇" if is_muted else "🔊")
        self.mute_btn.setToolTip("Unmute voice output" if is_muted else "Mute voice output")

    def insert_transcribed_text(self, text: str) -> None:
        """Inserts speech-to-text transcription into input field for editing."""
        if text.strip():
            current = self.input_field.toPlainText().strip()
            if current:
                self.input_field.setPlainText(f"{current} {text.strip()}")
            else:
                self.input_field.setPlainText(text.strip())
            self.input_field.setFocus()

    def update_volume_meter(self, level: float) -> None:
        """Feeds volume level to waveform visualizer."""
        self.status_bar.visualizer.set_level(level)

    def set_voice_status(self, status: str) -> None:
        """Updates status indicator."""
        self.status_bar.set_status(status)

    def clear_feed(self) -> None:
        """Clears all message widgets from feed."""
        while self.feed_layout.count() > 1:
            item = self.feed_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

    def scroll_to_bottom(self) -> None:
        """Ensures the newest messages are automatically scrolled into view."""
        QTimer.singleShot(20, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))
