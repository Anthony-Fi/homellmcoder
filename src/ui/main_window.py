import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QTextEdit, QSplitter, QTreeView, QLabel, QStatusBar,
    QComboBox, QPushButton, QProgressBar
)
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtCore import Qt, QDir

from llm_service.manager import LocalLLMManager

class MainWindow(QMainWindow):
    """Main application window with a three-panel layout."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("HomeLLMCoder - Offline AI Desktop App")
        self.setGeometry(100, 100, 1200, 800)

        # Create main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create the main splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter)

        # Left panel: File Navigator
        file_navigator = self._create_file_navigator()
        main_splitter.addWidget(file_navigator)

        # Right panel: Code Editor and Terminal/Chat
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        main_splitter.addWidget(right_splitter)

        # Top-right: Code Editor (placeholder)
        code_editor = QTextEdit()
        code_editor.setPlaceholderText("Code editor goes here...")
        right_splitter.addWidget(code_editor)

        # Bottom-right: Terminal/Chat (placeholder)
        terminal_chat = QTextEdit()
        terminal_chat.setPlaceholderText("Terminal/Chat panel goes here...")
        right_splitter.addWidget(terminal_chat)

        # Set initial sizes for the splitters
        main_splitter.setSizes([250, 950])
        right_splitter.setSizes([600, 200])

        # Initialize LLM Manager
        self.llm_manager = LocalLLMManager()

        # Create status bar
        self._create_status_bar()

        # Populate models
        self._populate_models()

    def _create_file_navigator(self) -> QWidget:
        """Creates the file navigator panel."""
        navigator_container = QWidget()
        layout = QVBoxLayout(navigator_container)
        layout.setContentsMargins(0, 0, 0, 0)

        model = QFileSystemModel()
        model.setRootPath(QDir.currentPath())

        tree = QTreeView()
        tree.setModel(model)
        tree.setRootIndex(model.index(QDir.currentPath()))
        tree.setColumnWidth(0, 200)
        tree.setAlternatingRowColors(True)

        layout.addWidget(tree)
        return navigator_container

    def _create_status_bar(self):
        """Creates and configures the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.model_selector = QComboBox()
        self.model_selector.setToolTip("Select an available LLM")
        self.status_bar.addPermanentWidget(self.model_selector)

        self.load_model_button = QPushButton("Load Model")
        self.load_model_button.setToolTip("Load the selected model")
        self.load_model_button.clicked.connect(self._load_selected_model)
        self.status_bar.addPermanentWidget(self.load_model_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)

    def _populate_models(self):
        """Fetches available models from the LLM manager and populates the dropdown."""
        if self.llm_manager.client:
            models = self.llm_manager.discover_models()
            self.model_selector.addItems(models)
            if not models:
                self.model_selector.addItem("No models found")
                self.model_selector.setEnabled(False)
                self.load_model_button.setEnabled(False)
        else:
            self.model_selector.addItem("Ollama not running")
            self.model_selector.setEnabled(False)
            self.load_model_button.setEnabled(False)

    def _load_selected_model(self):
        """Handles the model loading process."""
        selected_model = self.model_selector.currentText()
        if not selected_model or "No models" in selected_model or "Ollama not" in selected_model:
            self.status_bar.showMessage("No model selected or available to load.", 5000)
            return

        self.progress_bar.setVisible(True)
        self.load_model_button.setEnabled(False)
        self.model_selector.setEnabled(False)
        self.status_bar.showMessage(f"Loading model: {selected_model}...")

        # In a real app, this would be a background thread
        result = self.llm_manager.load_model(selected_model)

        self.progress_bar.setVisible(False)
        self.load_model_button.setEnabled(True)
        self.model_selector.setEnabled(True)

        if result and result.get("status") == "success":
            self.status_bar.showMessage(f"Successfully loaded model: {selected_model}", 5000)
        else:
            error_message = result.get("message", "An unknown error occurred.")
            self.status_bar.showMessage(f"Failed to load model: {error_message}", 5000)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
