#!/usr/bin/env python3
"""
HomeLLMCoder - Main entry point for the application.
"""
import sys
import os
from pathlib import Path

# Setup logging at the very beginning
from src.error_logger import setup_logging
setup_logging()

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow

def main():
    """Main function to run the application."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
