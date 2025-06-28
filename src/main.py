#!/usr/bin/env python3
"""
HomeLLMCoder - Main entry point for the application.
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from src.error_logger import setup_logging
from src.ui.main_window import MainWindow

# Add the project root to the Python path BEFORE other project imports
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Setup logging at the very beginning
setup_logging()


# NOTE: This is a workaround for a bug in PyQt6 < 6.4.1.
# If the app is packaged with PyInstaller, this prevents a crash on exit.
# See: https://github.com/pyinstaller/pyinstaller/issues/7754
if sys.platform == "win32" and "PyInstaller" in sys.executable:
    # This is a conditional import to avoid issues on non-windows systems
    # or when not running from a PyInstaller bundle.
    try:
        import PySide6.QtCore

        PySide6.QtCore.QCoreApplication.setAttribute(
            PySide6.QtCore.Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True
        )
    except ImportError:
        # PySide6 might not be installed, which is fine if not packaged.
        pass


def main():
    """Main function to run the application."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
