import sys
import shutil
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QTextEdit, QSplitter, QTreeView, QLabel, QStatusBar,
    QComboBox, QPushButton, QProgressBar, QTabWidget, QMenu, QInputDialog, QMessageBox, QFileDialog
)
from PyQt6.QtGui import QFileSystemModel, QAction
from PyQt6.QtCore import Qt, QDir, QModelIndex
import os
import tempfile
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.llm_service.manager import LocalLLMManager
from src.llm_service.rag import RAGSystem
from src.ui.code_editor import TabbedCodeEditor
from src.ui.chat_widget import LLMChatWidget
from src.ui.terminal_widget import TerminalWidget
from src.ui.load_model_thread import LoadModelThread

# Import version using absolute import
try:
    from src.version import __version__
except ImportError:
    # Fallback for when running as a package
    from version import __version__

class MainWindow(QMainWindow):
    """Main application window with a three-panel layout."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"HomeLLMCoder v{__version__}")
        self.setGeometry(100, 100, 1200, 800)

        # Initialize project root
        self.project_root = QDir.currentPath()

        # Initialize backend managers first, as UI components depend on them
        try:
            logging.info("Attempting to create LocalLLMManager instance.")
            self.llm_manager = LocalLLMManager()
            logging.info("LocalLLMManager instance created successfully.")
        except Exception as e:
            logging.critical(f"CRITICAL ERROR during LocalLLMManager instantiation: {e}", exc_info=True)
            self.llm_manager = None
        self.rag_system = RAGSystem()

        # Initialize UI components
        self._create_central_widget()
        self._create_menus()
        self._create_status_bar()

        # Populate models after UI is created
        self._populate_models()

    def _create_central_widget(self):
        """Creates the main layout."""
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

        # Top-right: Code Editor
        self.code_editor = TabbedCodeEditor()
        self.code_editor.code_to_execute.connect(self._execute_code_in_terminal)
        right_splitter.addWidget(self.code_editor)

        # Bottom-right: Tabbed view for Chat and Terminal
        self.bottom_right_tabs = QTabWidget()
        self.chat_widget = LLMChatWidget(self.llm_manager)
        self.chat_widget.change_requested.connect(self._handle_ai_file_change)
        self.terminal_widget = TerminalWidget()
        self.bottom_right_tabs.addTab(self.chat_widget, "LLM Chat")
        self.bottom_right_tabs.addTab(self.terminal_widget, "Terminal")
        right_splitter.addWidget(self.bottom_right_tabs)

        # Set initial sizes for the splitters
        main_splitter.setSizes([250, 950])
        right_splitter.setSizes([600, 200])

    def _create_file_navigator(self) -> QWidget:
        """Creates the file navigator panel."""
        navigator_container = QWidget()
        layout = QVBoxLayout(navigator_container)

        model = QFileSystemModel()
        # Set the root to empty to show all drives
        model.setRootPath("")
        model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot | QDir.Filter.Hidden)

        self.tree = QTreeView()
        self.tree.setModel(model)
        # The view will now start at the drive level

        # --- Configure Tree View Appearance ---
        self.tree.setAnimated(True)
        self.tree.setIndentation(20)

        self.tree.setColumnWidth(0, 200)
        self.tree.setAlternatingRowColors(True)
        self.tree.doubleClicked.connect(self._on_file_navigator_double_clicked)

        # Enable and connect context menu
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_file_navigator_context_menu)

        index_button = QPushButton("Index Selected File")
        index_button.setToolTip("Index the selected file for RAG")
        index_button.clicked.connect(self._index_selected_file)

        layout.addWidget(self.tree)
        layout.addWidget(index_button)
        return navigator_container

    def _create_menus(self):
        """Creates the main menu bar."""
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")

        open_folder_action = QAction("&Open Project Folder...", self)
        open_folder_action.triggered.connect(self._open_project_folder)
        file_menu.addAction(open_folder_action)

        file_menu.addSeparator()

        exit_action = QAction("&Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _open_project_folder(self):
        """Opens a dialog to select a project folder."""
        directory = QFileDialog.getExistingDirectory(self, "Select Project Folder", QDir.currentPath())
        if directory:
            self._set_project_root(directory)

    def _set_project_root(self, path):
        """Sets the root directory for the file navigator and updates the UI."""
        self.project_root = os.path.abspath(path)
        self.tree.model().setRootPath(self.project_root)
        self.tree.setRootIndex(self.tree.model().index(self.project_root))
        self.project_root_label.setText(f"Project: {self.project_root}")
        self.statusBar().showMessage(f"Project root set to {self.project_root}", 5000)

    def _show_file_navigator_context_menu(self, position):
        """Creates and shows the context menu for the file navigator."""
        index = self.tree.indexAt(position)
        if not index.isValid():
            return

        menu = QMenu()
        file_path = self.tree.model().filePath(index)

        # Add 'Set as Project Root' action only for directories
        if os.path.isdir(file_path):
            set_as_root_action = QAction("Set as Project Root", self)
            set_as_root_action.triggered.connect(lambda: self._set_project_root(file_path))
            menu.addAction(set_as_root_action)
            menu.addSeparator()

        new_file_action = QAction("New File...")
        new_file_action.triggered.connect(lambda: self._create_new_file(file_path))
        menu.addAction(new_file_action)
        new_folder_action = menu.addAction("New Folder...")
        new_folder_action.triggered.connect(lambda: self._create_new_folder(file_path))
        menu.addSeparator()
        rename_action = menu.addAction("Rename...")
        rename_action.triggered.connect(lambda: self._rename_item(file_path))
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(lambda: self._delete_item(file_path))

        # Disable actions that don't apply
        if not index.isValid():
            rename_action.setEnabled(False)
            delete_action.setEnabled(False)

        action = menu.exec(self.tree.viewport().mapToGlobal(position))

    def _create_new_file(self, base_path):
        """Handles the 'New File' action."""
        dir_path = base_path if os.path.isdir(base_path) else os.path.dirname(base_path)
        file_name, ok = QInputDialog.getText(self, "New File", "Enter file name:")
        if ok and file_name:
            try:
                new_path = os.path.join(dir_path, file_name)
                if not os.path.exists(new_path):
                    with open(new_path, 'w') as f:
                        pass  # Create an empty file
                    self.statusBar().showMessage(f"File '{file_name}' created.", 4000)
                else:
                    QMessageBox.warning(self, "Error", "File already exists.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create file: {e}")

    def _create_new_folder(self, base_path):
        """Handles the 'New Folder' action."""
        dir_path = base_path if os.path.isdir(base_path) else os.path.dirname(base_path)
        folder_name, ok = QInputDialog.getText(self, "New Folder", "Enter folder name:")
        if ok and folder_name:
            try:
                new_path = os.path.join(dir_path, folder_name)
                if not os.path.exists(new_path):
                    os.makedirs(new_path)
                    self.statusBar().showMessage(f"Folder '{folder_name}' created.", 4000)
                else:
                    QMessageBox.warning(self, "Error", "Folder already exists.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create folder: {e}")

    def _rename_item(self, path):
        """Handles the 'Rename' action."""
        old_name = os.path.basename(path)
        new_name, ok = QInputDialog.getText(self, "Rename", "Enter new name:", text=old_name)
        if ok and new_name and new_name != old_name:
            try:
                new_path = os.path.join(os.path.dirname(path), new_name)
                os.rename(path, new_path)
                self.statusBar().showMessage(f"Renamed to '{new_name}'.", 4000)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not rename item: {e}")

    def _delete_item(self, path):
        """Handles the 'Delete' action with confirmation."""
        item_name = os.path.basename(path)
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to permanently delete '{item_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                self.statusBar().showMessage(f"Deleted '{item_name}'.", 4000)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete item: {e}")

    def _on_file_navigator_double_clicked(self, index: QModelIndex):
        """Handles double-click events in the file navigator to open files."""
        file_path = self.tree.model().filePath(index)
        if not os.path.isdir(file_path):
            self.code_editor.open_file(file_path)

    def _index_selected_file(self):
        """Indexes the currently selected file in the tree view."""
        indexes = self.tree.selectedIndexes()
        if not indexes:
            self.statusBar().showMessage("No file selected.", 4000)
            return

        # Get the file path from the model
        file_path = self.tree.model().filePath(indexes[0])

        if os.path.isdir(file_path):
            self.statusBar().showMessage("Cannot index a directory.", 4000)
            return

        self.statusBar().showMessage(f"Indexing {os.path.basename(file_path)}...", 2000)
        success = self.rag_system.index(file_path)

        if success:
            self.statusBar().showMessage(f"Successfully indexed {os.path.basename(file_path)}.", 5000)
        else:
            self.statusBar().showMessage(f"Failed to index {os.path.basename(file_path)}.", 5000)

    def _execute_code_in_terminal(self, code: str):
        """Receives code, saves it to a temp file, and executes it in the terminal."""
        if not code:
            return

        try:
            # Sanitize the code to handle multiple issues:
            # 1. Replace non-standard line breaks
            sanitized_code = code.replace('\u2029', '\n').strip()

            # 2. Strip markdown code block fences
            if sanitized_code.startswith('```python'):
                sanitized_code = sanitized_code[9:] # len('```python')
            if sanitized_code.startswith('```'):
                sanitized_code = sanitized_code[3:]
            if sanitized_code.endswith('```'):
                sanitized_code = sanitized_code[:-3]

            sanitized_code = sanitized_code.strip()

            # Create a temporary file to hold the code
            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.py', encoding='utf-8') as temp_file:
                temp_file.write(sanitized_code)
                temp_file_path = temp_file.name

            # Get the path to the current python executable (to respect the venv)
            python_executable = sys.executable

            # Construct a robust command for PowerShell:
            # 1. Execute the python script, redirecting stderr to stdout (2>&1)
            # 2. Capture all output into the $output variable
            # 3. Explicitly write the captured output to the pipeline
            # 4. Remove the temporary file, ignoring errors if it's already gone
            command = f"$output = & \"{python_executable}\" \"{temp_file_path}\" 2>&1; Write-Output $output; Remove-Item \"{temp_file_path}\" -ErrorAction SilentlyContinue"

            self.bottom_right_tabs.setCurrentWidget(self.terminal_widget)
            self.terminal_widget.execute_command(command)

        except Exception as e:
            QMessageBox.critical(self, "Execution Error", f"Failed to execute code: {e}")

    def _handle_ai_file_change(self, action: dict):
        """Handles file creation/editing actions requested by the AI."""
        logging.info(f"Attempting to handle AI file change action: {action}")
        try:
            action_type = action.get("type")
            file_path = action.get("file_path")
            content = action.get("content", "")

            if not action_type or not file_path:
                QMessageBox.warning(self, "Invalid Action", "AI proposed an invalid file action.")
                return

            # Ensure the file path is relative to the project root
            # and prevent directory traversal attacks.
            full_path = os.path.abspath(os.path.join(self.project_root, file_path))
            if not full_path.startswith(self.project_root):
                raise Exception("Attempted to access a file outside the project root.")

            logging.info(f"Resolved full path for file operation: {full_path}")

            if action_type == "CREATE_FILE":
                # Ensure parent directory exists
                parent_dir = os.path.dirname(full_path)
                if not os.path.exists(parent_dir):
                    os.makedirs(parent_dir)

                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.statusBar().showMessage(f"File created: {file_path}", 5000)
                logging.info(f"Successfully created file: {full_path}")

            elif action_type == "EDIT_FILE":
                if not os.path.exists(full_path):
                    self.statusBar().showMessage(f"File not found for editing: {file_path}", 4000)
                    return

                with open(full_path, 'r+', encoding='utf-8') as f:
                    lines = f.readlines()
                    # TODO: Implement more robust line-based editing
                    f.seek(0)
                    f.writelines(lines)

                self.statusBar().showMessage(f"File updated: {file_path}", 5000)

        except Exception as e:
            logging.error(f"Failed to perform AI action. Action: {action}, Error: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to perform AI action: {e}")

    def _create_status_bar(self):
        """Creates and configures the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Add a permanent widget to show the project root
        self.project_root_label = QLabel(f"Project: {QDir.currentPath()}")
        self.status_bar.addPermanentWidget(self.project_root_label)

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
        if not self.llm_manager or not self.llm_manager.client:
            self.statusBar().showMessage("Ollama service not available. Please start Ollama and restart.", 5000)
            return

        try:
            models = self.llm_manager.discover_models()
            self.model_selector.addItems(models)
            if not models:
                self.model_selector.addItem("No models found")
                self.model_selector.setEnabled(False)
                self.load_model_button.setEnabled(False)
        except Exception as e:
            self.statusBar().showMessage(f"Failed to populate models: {e}", 5000)

    def _load_selected_model(self):
        """Handles the model loading process."""
        model_name = self.model_selector.currentText()
        if model_name and "No models" not in model_name:
            self.load_model_button.setEnabled(False)
            self.load_model_button.setText("Loading...")
            self.statusBar().showMessage(f"Loading model: {model_name}...")

            # Run model loading in a separate thread to keep UI responsive
            self.load_thread = LoadModelThread(self.llm_manager, model_name)
            self.load_thread.finished.connect(self._on_model_loaded)
            self.load_thread.start()

    def _on_model_loaded(self, result):
        """Callback for when model loading is complete."""
        self.load_model_button.setEnabled(True)
        self.load_model_button.setText("Load Model")
        self.statusBar().showMessage(result["message"], 5000)
        if result["status"] == "success":
            self.chat_widget.set_llm_manager(self.llm_manager)

    def _set_project_root(self, path):
        """Sets the root directory for the file navigator and updates the UI."""
        self.project_root = os.path.abspath(path)
        self.tree.model().setRootPath(self.project_root)
        self.tree.setRootIndex(self.tree.model().index(self.project_root))
        self.project_root_label.setText(f"Project: {self.project_root}")
        self.statusBar().showMessage(f"Project root set to: {self.project_root}")
        logging.info(f"Project root set to: {self.project_root}")

    def _open_project_folder(self):
        """Opens a dialog to select a project folder."""
        directory = QFileDialog.getExistingDirectory(self, "Select Project Folder", QDir.currentPath())
        if directory:
            self._set_project_root(directory)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
