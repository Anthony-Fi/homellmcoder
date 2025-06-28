import logging
import sys
from PyQt6.QtWidgets import (
    QMainWindow,
    QVBoxLayout,
    QSplitter,
    QMessageBox,
    QFileDialog,
    QTabWidget,
    QApplication,
    QDialog,
    QListWidget,
    QDialogButtonBox,
    QLabel,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

# Corrected absolute imports
from src.ui.file_navigator import FileNavigator
from src.ui.code_editor import TabbedCodeEditor
from src.ui.terminal_widget import TerminalWidget
from src.ui.chat_widget import LLMChatWidget
from src.llm_service.manager import LocalLLMManager
from src.services.project_service import ProjectService
from src.services.history_service import HistoryService
from src.services.file_operation_service import FileOperationService


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()

        # Initialize services
        self.project_service = ProjectService()
        self.history_service = HistoryService()
        self.file_operation_service = FileOperationService()
        self.llm_manager = LocalLLMManager()

        self.setWindowTitle("HomeLLMCoder")
        self.setGeometry(100, 100, 1200, 800)

        # Setup UI
        self._create_central_widget()
        self._create_menus()
        self._create_status_bar()
        self._connect_signals()

    def _create_central_widget(self):
        """Creates and configures the main central widget with all UI components."""
        # Main vertical splitter for the top content and the bottom terminal
        main_vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        self.setCentralWidget(main_vertical_splitter)

        # Top horizontal splitter for file navigator, code editor, and chat
        top_horizontal_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_vertical_splitter.addWidget(top_horizontal_splitter)

        # Populate the top horizontal splitter
        self.file_navigator = FileNavigator(self)
        top_horizontal_splitter.addWidget(self.file_navigator)

        self.code_editor = TabbedCodeEditor(self)
        top_horizontal_splitter.addWidget(self.code_editor)

        self.chat_widget = LLMChatWidget(
            self.llm_manager, self.history_service, self.file_operation_service, self
        )
        top_horizontal_splitter.addWidget(self.chat_widget)

        # Bottom part: Terminal
        self.terminal_widget = TerminalWidget(self)
        main_vertical_splitter.addWidget(self.terminal_widget)

        # Set initial sizes for the splitters
        top_horizontal_splitter.setSizes([250, 650, 300])
        main_vertical_splitter.setSizes([600, 200])

    def _create_menus(self):
        """Creates the main menu bar."""
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("&File")
        open_folder_action = QAction("&Open Project Folder...", self)
        open_folder_action.triggered.connect(self.open_project_folder)
        file_menu.addAction(open_folder_action)
        file_menu.addSeparator()
        exit_action = QAction("&Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # LLM Select Menu
        llm_menu = menu_bar.addMenu("&LLM Select")
        select_model_action = QAction("Select LLM Model...", self)
        select_model_action.triggered.connect(self.select_llm_model)
        llm_menu.addAction(select_model_action)

    def _create_status_bar(self):
        """Creates and configures the status bar."""
        status_bar = self.statusBar()
        self.status_bar_message = QLabel("No project selected.")
        status_bar.addPermanentWidget(self.status_bar_message)

    def _connect_signals(self):
        """Connect all signals to their slots in one place."""
        self.file_navigator.file_selected.connect(self.code_editor.open_file)
        self.file_navigator.project_root_changed.connect(self.on_project_root_changed)
        # The chat_widget's internal _handle_ai_file_change now manages this.
        # No direct connection needed here if the widget handles its own button clicks.

    def on_project_root_changed(self, new_root):
        """Handles the project root change across the application."""
        self.file_navigator.set_root_path(new_root)
        self.project_service.set_project_root(new_root)
        self.chat_widget.set_project_root(new_root)
        self.terminal_widget.set_project_root(new_root)
        self.status_bar_message.setText(f"Project: {new_root}")
        logging.info(f"MainWindow: Project root changed to {new_root}")

    def open_project_folder(self):
        """Opens a dialog to select a project folder."""
        directory = QFileDialog.getExistingDirectory(self, "Select Project Folder")
        if directory:
            self.on_project_root_changed(directory)

    def select_llm_model(self):
        """Opens a dialog to select and load an LLM model."""
        available_models = self.llm_manager.list_models()
        if not available_models:
            QMessageBox.warning(
                self,
                "No Models Found",
                (
                    "Could not find any Ollama models. Please make sure Ollama is "
                    "running and models are installed."
                ),
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Select LLM Model")
        layout = QVBoxLayout(dialog)

        list_widget = QListWidget()
        list_widget.addItems(available_models)
        if self.llm_manager.loaded_model in available_models:
            try:
                list_widget.setCurrentRow(
                    available_models.index(self.llm_manager.loaded_model)
                )
            except ValueError:
                pass  # loaded model not in list
        layout.addWidget(list_widget)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec():
            selected_item = list_widget.currentItem()
            if selected_item:
                model_name = selected_item.text()
                self.status_bar_message.setText(f"Loading model: {model_name}...")
                QApplication.processEvents()
                if self.llm_manager.load_model(model_name):
                    self.status_bar_message.setText(f"Model loaded: {model_name}")
                else:
                    self.status_bar_message.setText("Failed to load model.")
                    QMessageBox.critical(
                        self, "Error", f"Failed to load model: {model_name}"
                    )

    def closeEvent(self, event):
        """Handles window close events."""
        # The chat widget now handles saving its own history.
        super().closeEvent(event)


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())
