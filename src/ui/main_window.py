import sys
import shutil
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QTextEdit, QSplitter, QTreeView, QLabel, QStatusBar,
    QComboBox, QPushButton, QProgressBar, QTabWidget, QMenu, QInputDialog, QMessageBox
)
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtCore import Qt, QDir, QModelIndex
import os
import tempfile

from llm_service.manager import LocalLLMManager
from llm_service.rag import RAGSystem
from .code_editor import TabbedCodeEditor
from .chat_widget import LLMChatWidget
from .terminal_widget import TerminalWidget

class MainWindow(QMainWindow):
    """Main application window with a three-panel layout."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("HomeLLMCoder - Offline AI Desktop App")
        self.setGeometry(100, 100, 1200, 800)

        # Initialize backend managers first, as UI components depend on them
        self.llm_manager = LocalLLMManager()
        self.rag_system = RAGSystem()

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

        self.tree = QTreeView()
        self.tree.setModel(model)
        self.tree.setRootIndex(model.index(QDir.currentPath()))
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

    def _show_file_navigator_context_menu(self, position):
        """Creates and shows the context menu for the file navigator."""
        menu = QMenu()
        index = self.tree.indexAt(position)
        path = self.tree.model().filePath(index) if index.isValid() else QDir.currentPath()

        # Actions
        new_file_action = menu.addAction("New File...")
        new_folder_action = menu.addAction("New Folder...")
        menu.addSeparator()
        rename_action = menu.addAction("Rename...")
        delete_action = menu.addAction("Delete")

        # Disable actions that don't apply
        if not index.isValid():
            rename_action.setEnabled(False)
            delete_action.setEnabled(False)

        action = menu.exec(self.tree.viewport().mapToGlobal(position))

        # Handle selected action
        if action == new_file_action:
            self._create_new_file(path)
        elif action == new_folder_action:
            self._create_new_folder(path)
        elif action == rename_action:
            self._rename_item(path)
        elif action == delete_action:
            self._delete_item(path)

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
                    self.status_bar.showMessage(f"File '{file_name}' created.", 4000)
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
                    self.status_bar.showMessage(f"Folder '{folder_name}' created.", 4000)
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
                self.status_bar.showMessage(f"Renamed to '{new_name}'.", 4000)
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
                self.status_bar.showMessage(f"Deleted '{item_name}'.", 4000)
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
            self.status_bar.showMessage("No file selected.", 4000)
            return

        # Get the file path from the model
        file_path = self.tree.model().filePath(indexes[0])

        if os.path.isdir(file_path):
            self.status_bar.showMessage("Cannot index a directory.", 4000)
            return

        self.status_bar.showMessage(f"Indexing {os.path.basename(file_path)}...", 2000)
        success = self.rag_system.index(file_path)

        if success:
            self.status_bar.showMessage(f"Successfully indexed {os.path.basename(file_path)}.", 5000)
        else:
            self.status_bar.showMessage(f"Failed to index {os.path.basename(file_path)}.", 5000)

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
        """Handles a file modification action requested by the AI."""
        action_type = action.get("type")
        file_path = action.get("file_path")
        content = action.get("content", "")

        if not action_type or not file_path:
            QMessageBox.warning(self, "Invalid Action", "AI proposed an invalid file action.")
            return

        # Ensure the file path is relative to the project root
        # and prevent directory traversal attacks.
        project_root = os.path.abspath(QDir.currentPath())
        full_path = os.path.abspath(os.path.join(project_root, file_path))
        if not full_path.startswith(project_root):
            QMessageBox.critical(self, "Security Error", "Attempted file access outside the project directory.")
            return

        # Create directories if they don't exist for file creation
        if action_type in ["CREATE_FILE", "OVERWRITE_FILE"]:
            try:
                dir_name = os.path.dirname(full_path)
                if not os.path.exists(dir_name):
                    os.makedirs(dir_name)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create directory: {e}")
                return

        # Ask for user confirmation
        confirm_text = f"The AI wants to perform the following action:\n\n"
        confirm_text += f"Type: {action_type}\n"
        confirm_text += f"File: {file_path}\n\n"
        confirm_text += "Do you want to proceed?"

        reply = QMessageBox.question(self, f"Confirm AI Action: {action_type}", confirm_text, 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.No:
            self.status_bar.showMessage("AI action cancelled by user.", 4000)
            return

        # Execute the action
        try:
            if action_type == "CREATE_FILE" or action_type == "OVERWRITE_FILE":
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.status_bar.showMessage(f"Successfully wrote to {file_path}", 5000)
                # If the editor is open, prompt to reload
                self.code_editor.check_and_reload_file(full_path)

            elif action_type == "DELETE_FILE":
                if os.path.exists(full_path):
                    os.remove(full_path)
                    self.status_bar.showMessage(f"Successfully deleted {file_path}", 5000)
                else:
                    self.status_bar.showMessage(f"File not found for deletion: {file_path}", 4000)
            
            # Refresh the file navigator to show the change
            self.tree.model().setRootPath(QDir.currentPath()) # This forces a refresh

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to perform AI action: {e}")

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
