"""
SANJI — Autonomous AI Desktop Assistant for Windows 11
Main Entrypoint Application.
"""

import sys
from pathlib import Path

# Add project root directory to Python path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from config import settings
from core.assistant import Assistant
from interface.main_window import MainWindow
from utils.logger import logger, setup_logger


def main() -> int:
    """Bootstraps the SANJI application."""
    # 1. Initialize logging
    setup_logger(
        name="SANJI",
        level=settings.log_level,
        log_file=settings.log_file
    )
    logger.info(f"Starting {settings.app_name} v{settings.app_version} [{settings.env}]")

    # 2. Configure High-DPI and Qt Application
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(settings.app_name)
    app.setApplicationVersion(settings.app_version)

    # Global UI Font
    app.setFont(QFont("Segoe UI", 10))

    try:
        # 3. Instantiate Assistant Controller and Main Window
        assistant = Assistant()
        window = MainWindow(assistant=assistant)
        window.show()

        logger.info("Application window displayed. Entering event loop.")
        return app.exec()

    except Exception as e:
        logger.critical(f"Fatal error during application lifecycle: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

