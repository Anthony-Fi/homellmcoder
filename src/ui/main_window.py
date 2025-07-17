import logging
import sys
import os
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
from src.ui.plan_widget import PlanWidget  # Import PlanWidget
from src.llm_service.manager import LocalLLMManager
from src.services.project_service import ProjectService
from src.services.history_service import HistoryService
from src.services.file_operation_service import FileOperationService, CommandOutputEmitter


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()

        # Initialize services
        self.project_service = ProjectService()
        self.history_service = HistoryService()
        self.command_output_emitter = CommandOutputEmitter()
        self.file_operation_service = FileOperationService(self.command_output_emitter)
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
        main_vertical_splitter, top_horizontal_splitter = self._create_splitters()
        self._populate_central_widget(main_vertical_splitter, top_horizontal_splitter)

        # Set initial sizes for the splitters
        top_horizontal_splitter.setSizes([250, 650, 300, 300])  # Adjust size for plan widget
        main_vertical_splitter.setSizes([600, 200])

    def _populate_central_widget(self, main_vertical_splitter, top_horizontal_splitter):
        """Populates the central widget's splitters with UI components."""
        self.file_navigator = FileNavigator(self)
        top_horizontal_splitter.addWidget(self.file_navigator)

        self.code_editor = TabbedCodeEditor(self)
        top_horizontal_splitter.addWidget(self.code_editor)

        self.terminal_widget = TerminalWidget(self)
        main_vertical_splitter.addWidget(self.terminal_widget)

        self.plan_widget = PlanWidget(self)  # Initialize PlanWidget
        top_horizontal_splitter.addWidget(self.plan_widget)

        self.chat_widget = LLMChatWidget(
            self.llm_manager, self.history_service, self.file_operation_service, self.terminal_widget, self.plan_widget
        )
        top_horizontal_splitter.addWidget(self.chat_widget)

    def _create_splitters(self):
        """Creates and returns the main vertical and top horizontal splitters."""
        main_vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        self.setCentralWidget(main_vertical_splitter)

        top_horizontal_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_vertical_splitter.addWidget(top_horizontal_splitter)

        return main_vertical_splitter, top_horizontal_splitter

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

        # Tools Menu
        tools_menu = menu_bar.addMenu("&Tools")
        jedi_agent_action = QAction("Jedi Automation Agent", self)
        jedi_agent_action.triggered.connect(self.launch_jedi_agent)
        tools_menu.addAction(jedi_agent_action)

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
        self.chat_widget.plan_updated.connect(self.plan_widget.set_plan_content)
        self.plan_widget.run_coder_requested.connect(self._on_run_coder_requested)

        # Connect command output signals to terminal widget
        self.command_output_emitter.output_received.connect(self.terminal_widget.append_output)
        self.command_output_emitter.error_received.connect(self.terminal_widget.append_error)
        self.command_output_emitter.command_finished.connect(self.terminal_widget.command_finished)

        # --- Builder/Agent Live Log Integration ---
        try:
            from src.ui.builder_signals import BuilderSignals
            self.builder_signals = BuilderSignals()
            self.builder_signals.log_message.connect(self.append_to_log)
            self.builder_signals.command_output.connect(self.append_to_log)
            self.builder_signals.command_error.connect(self.append_to_log)
            self.builder_signals.command_prompt.connect(self.prompt_user)
        except ImportError:
            self.builder_signals = None  # fallback if not available

    def append_to_log(self, message):
        """Appends a log message to the terminal widget (live agent/command log)."""
        if hasattr(self, 'terminal_widget'):
            self.terminal_widget.append_output(str(message))

    def prompt_user(self, message, callback):
        """Prompt the user for input in response to a command needing input."""
        from PyQt6.QtWidgets import QInputDialog
        user_input, ok = QInputDialog.getText(self, "Command Needs Input", message)
        if ok:
            callback(user_input)

    def _on_run_coder_requested(self):
        """Triggers the Coder agent with the current context."""
        instructions, file_content = self._get_coder_instructions()
        if instructions is None or file_content is None:
            return

        # 3. Run the coder
        self.chat_widget.run_coder_with_context(file_content, instructions)

    def _get_coder_instructions(self):
        """Retrieves the instructions from the plan widget and the content of the active file.
        Ensures only a selected task (not the whole plan) is sent to the Coder agent.
        """
        plan_text = self.plan_widget.plan_view.toPlainText()
        selected_text = self.plan_widget.plan_view.textCursor().selectedText().strip()
        # If nothing is selected or the selection is too large, warn the user
        if not selected_text:
            QMessageBox.warning(self, "No Instructions", "Please select the task instructions from the plan before running the coder.")
            return None, None
        # If the selection is nearly the whole plan, warn the user
        if len(selected_text) > 0.9 * len(plan_text):
            QMessageBox.warning(self, "Too Much Selected", "Please select only the relevant task or step from the plan, not the entire plan.")
            return None, None
        # Optionally, block if the selection mentions plan.md/project_plan.md creation
        if 'plan.md' in selected_text.lower() or 'project_plan.md' in selected_text.lower():
            QMessageBox.warning(self, "Invalid Task", "Do not select instructions related to creating or modifying plan.md/project_plan.md.")
            return None, None
        # You can also add more filters here if needed
        # (file_content can be fetched as before, or left as None if not needed)
        return selected_text, None


    def on_project_root_changed(self, new_root):
        """Handles the project root change across the application."""
        self.file_navigator.set_root_path(new_root)
        self.project_service.set_project_root(new_root)
        self.chat_widget.set_project_root(new_root)
        self.terminal_widget.set_project_root(new_root)
        self.status_bar_message.setText(f"Project: {new_root}")
        self._load_plan_from_file(new_root)

    def _load_plan_from_file(self, project_root):
        """Loads plan.md into the PlanWidget if it exists."""
        if not project_root:
            self.plan_widget.set_plan_content("")
            return

        plan_path = os.path.join(project_root, "plan.md")
        if os.path.exists(plan_path):
            try:
                with open(plan_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.plan_widget.set_plan_content(content)
            except Exception as e:
                logging.error(f"Error loading plan.md: {e}")
                self.plan_widget.set_plan_content(f"# Error loading plan.md\n\n{e}")
        else:
            self.plan_widget.set_plan_content("# No plan.md file found in this project.")

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
                # Actually load the selected model
                success = self.llm_manager.load_model(model_name)
                if success:
                    QMessageBox.information(
                        self,
                        "LLM Model Loaded",
                        f"Successfully loaded model: {model_name}"
                    )
                else:
                    QMessageBox.critical(
                        self,
                        "Load Failed",
                        f"Failed to load model: {model_name}"
                    )

    def launch_jedi_agent(self):
        from src.jedi_agent.jedi_main import JediWindow
        print("Attempting to launch Jedi Agent...")
        # Ensure LLMManager is initialized before passing to JediWindow
        if not hasattr(self, 'llm_manager') or self.llm_manager is None:
            self.llm_manager = LLMManager()
            print("LLMManager initialized for Jedi Agent.")

        print("Before JediWindow instantiation.")
        self.jedi_window = JediWindow(self.llm_manager)
        print("JediWindow instance created.")
        print("Before JediWindow show() call.")
        self.jedi_window.show()
        print("JediWindow show() called.")
        print("Jedi Agent launch sequence completed.")

def closeEvent(self, event):
    """Handles window close events."""
    # Ensure the chat worker thread is gracefully shut down
    if self.chat_widget:
        self.chat_widget.shutdown()
    # The chat widget now handles saving its own history.
    super().closeEvent(event)


app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())
