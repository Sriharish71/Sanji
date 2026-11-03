"""
Futuristic JARVIS-inspired UI stylesheet and theme definitions for SANJI.
Palette: Deep Obsidian (#080c14), Electric Cyan (#00f0ff), Neon Blue (#0066ff),
Ice Blue (#90e0ef), Dark Steel (#131c2e), Cyber Amber (#ffaa00), Crimson Alert (#ff3366).
"""

COLORS = {
    "bg_dark": "#070a10",
    "bg_surface": "#0d131f",
    "bg_panel": "#121b2b",
    "bg_bubble_user": "#142542",
    "bg_bubble_sanji": "#0d1a2b",
    "accent_cyan": "#00f0ff",
    "accent_blue": "#0066ff",
    "accent_glow": "rgba(0, 240, 255, 0.25)",
    "text_primary": "#e6f1ff",
    "text_secondary": "#8ba3c7",
    "text_muted": "#4d6280",
    "border_subtle": "#1c2b42",
    "border_active": "#00f0ff",
    "status_online": "#00ffaa",
    "status_offline": "#ff3366",
    "status_thinking": "#ffaa00",
}

THEME_STYLESHEET = f"""
/* ==========================================================================
   SANJI HUD THEME - JARVIS INSPIRED (WINDOWS 11 COMPLIANT)
   ========================================================================== */

QMainWindow {{
    background-color: {COLORS['bg_dark']};
    color: {COLORS['text_primary']};
}}

QWidget {{
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    color: {COLORS['text_primary']};
    font-size: 13px;
}}

/* Scrollbars */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: {COLORS['border_subtle']};
    min-height: 24px;
    border-radius: 3px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLORS['accent_cyan']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* Input Box */
QTextEdit#chatInput {{
    background-color: {COLORS['bg_surface']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_subtle']};
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 14px;
    selection-background-color: {COLORS['accent_blue']};
}}

QTextEdit#chatInput:focus {{
    border: 1px solid {COLORS['accent_cyan']};
    background-color: {COLORS['bg_panel']};
}}

/* Primary Action Buttons */
QPushButton#sendButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLORS['accent_blue']}, stop:1 {COLORS['accent_cyan']});
    color: #ffffff;
    font-weight: bold;
    font-size: 13px;
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    min-height: 38px;
}}

QPushButton#sendButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a75ff, stop:1 #33f3ff);
}}

QPushButton#sendButton:pressed {{
    background-color: {COLORS['accent_blue']};
}}

QPushButton#sendButton:disabled {{
    background: #192333;
    color: #4a5d78;
}}

/* Sidebar Action Buttons */
QPushButton.nav-button {{
    background-color: transparent;
    color: {COLORS['text_secondary']};
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 10px 14px;
    text-align: left;
    font-weight: 500;
    font-size: 13px;
}}

QPushButton.nav-button:hover {{
    background-color: {COLORS['bg_panel']};
    color: {COLORS['accent_cyan']};
    border: 1px solid {COLORS['border_subtle']};
}}

QPushButton.nav-button:checked {{
    background-color: {COLORS['bg_panel']};
    color: {COLORS['accent_cyan']};
    border-left: 3px solid {COLORS['accent_cyan']};
}}

QPushButton#newChatButton {{
    background-color: transparent;
    color: {COLORS['accent_cyan']};
    border: 1px solid {COLORS['accent_cyan']};
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: bold;
}}

QPushButton#newChatButton:hover {{
    background-color: rgba(0, 240, 255, 0.12);
}}

/* Chat Scroll Area */
QScrollArea {{
    background-color: transparent;
    border: none;
}}

QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}

/* Status Badge */
QLabel#statusBadge {{
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 0.5px;
}}
"""
