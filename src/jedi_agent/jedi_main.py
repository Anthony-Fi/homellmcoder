import sys
import os
import subprocess
import shutil
import difflib

# Add the project root to the sys.path
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
sys.path.insert(0, project_root)

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QFileDialog,
    QMessageBox,
    QListWidget,
    QAbstractItemView,
    QTreeView,
    QTextEdit,
    QDialog
)
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCharFormat, QColor

from src.llm_service.manager import LocalLLMManager
from src.services.file_operation_service import FileOperationService
from src.jedi_agent.jedi_agents import PlannerAgent, ManagerAgent, CoderAgent

class JediWindow(QWidget):
    def __init__(self, llm_manager=None):
        super().__init__()
        self.llm_manager = llm_manager
        self.setWindowTitle("Jedi Automation Agent")
        self.setGeometry(200, 200, 600, 400)
        try:
            self._setup_ui()
        except Exception as e:
            print(f"Error during JediWindow UI setup: {e}")



    def _setup_ui(self):
        try:
            main_layout = QVBoxLayout(self)
        except Exception as e:
            print(f"Error during JediWindow UI setup: {e}")


        # Project Name
        project_name_layout = QHBoxLayout()
        project_name_label = QLabel("Project Name:")
        self.project_name_input = QLineEdit()
        project_name_layout.addWidget(project_name_label)
        project_name_layout.addWidget(self.project_name_input)
        main_layout.addLayout(project_name_layout)

        # Output Directory
        output_dir_layout = QHBoxLayout()
        output_dir_label = QLabel("Output Directory:")
        self.output_dir_input = QLineEdit()
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self._browse_output_directory)
        output_dir_layout.addWidget(output_dir_label)
        output_dir_layout.addWidget(self.output_dir_input)
        output_dir_layout.addWidget(self.browse_button)
        main_layout.addLayout(output_dir_layout)

        # Start Button
        self.start_button = QPushButton("Start Jedi")
        self.start_button.clicked.connect(self._start_jedi_process)
        main_layout.addWidget(self.start_button)

        # LLM Selection
        llm_selection_label = QLabel("Available LLMs:")
        main_layout.addWidget(llm_selection_label)

        self.llm_list_widget = QListWidget()
        if self.llm_manager:
            available_models = self.llm_manager.list_models()
            self.llm_list_widget.addItems(available_models)

        main_layout.addWidget(self.llm_list_widget)

        self.results_list_widget = QListWidget()
        self.results_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        main_layout.addWidget(QLabel("Generated Projects:"))
        main_layout.addWidget(self.results_list_widget)

        self.open_project_button = QPushButton("Open Selected Project in Explorer")
        self.open_project_button.clicked.connect(self._open_selected_project_in_explorer)
        main_layout.addWidget(self.open_project_button)

        self.compare_button = QPushButton("Compare Selected Projects")
        self.compare_button.clicked.connect(self._compare_selected_projects)
        main_layout.addWidget(self.compare_button)

        main_layout.addStretch()

        # File navigation and content display
        file_display_layout = QHBoxLayout()
        self.file_tree_view = QTreeView()
        self.file_model = QFileSystemModel()
        self.file_tree_view.setModel(self.file_model)
        self.file_tree_view.setRootIsDecorated(False)
        self.file_tree_view.setSortingEnabled(True)
        self.file_tree_view.clicked.connect(self._on_file_selected)

        self.file_content_display = QTextEdit()
        self.file_content_display.setReadOnly(True)

        # self.diff_display = QTextEdit() # This was part of a previous attempt to put diff in main window, but now it's in a dialog
        # self.diff_display.setReadOnly(True)

        file_display_layout.addWidget(self.file_tree_view)
        file_display_layout.addWidget(self.file_content_display)
        # file_display_layout.addWidget(self.diff_display)
        main_layout.addLayout(file_display_layout)

    def _on_file_selected(self, index):
        file_path = self.file_model.filePath(index)
        if os.path.isfile(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.file_content_display.setText(content)
            except Exception as e:
                self.file_content_display.setText(f"Error reading file: {e}")
        else:
            self.file_content_display.clear()

    def _compare_selected_projects(self):
        selected_items = self.results_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a generated project to open.")
            return

        selected_path = selected_items[0].text()
        if sys.platform == "win32":
            os.startfile(selected_path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", selected_path])
        else:
            subprocess.Popen(["xdg-open", selected_path])

    def _open_selected_project_in_explorer(self):
        selected_items = self.results_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a generated project to open in explorer.")
            return

        selected_path = selected_items[0].text()
        if sys.platform == "win32":
            os.startfile(selected_path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", selected_path])
        else:
            subprocess.Popen(["xdg-open", selected_path])

    def _on_project_selection_changed(self):
        selected_items = self.results_list_widget.selectedItems()
        if not selected_items:
            self.file_model.setRootPath("")
            self.file_tree_view.setRootIndex(self.file_model.index(""))
            self.file_content_display.clear()
            return

        selected_path = selected_items[0].text()
        self.file_model.setRootPath(selected_path)
        self.file_tree_view.setRootIndex(self.file_model.index(selected_path))
        self.file_content_display.clear()

    def _browse_output_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.output_dir_input.setText(directory)

    def _start_jedi_process(self):
        project_name = self.project_name_input.text()
        output_directory = self.output_dir_input.text()

        if not project_name:
            QMessageBox.warning(self, "Input Error", "Please enter a project name.")
            return
        if not output_directory:
            QMessageBox.warning(self, "Input Error", "Please select an output directory.")
            return

        selected_llms = [item.text() for item in self.llm_list_widget.selectedItems()]
        if not selected_llms:
            QMessageBox.warning(self, "Input Error", "Please select at least one LLM.")
            return

        # Here you would integrate the actual Jedi agent logic
        # For now, just print the inputs and selected LLMs
        QMessageBox.information(self, "Jedi Started", f"Jedi process started for {project_name} with LLMs: {', '.join(selected_llms)}")

        for llm_name in selected_llms:
            print(f"--- Orchestrating agents for LLM: {llm_name} ---")
            sanitized_llm_name = llm_name.replace(':', '-')
            llm_output_path = os.path.join(output_directory, sanitized_llm_name)
            os.makedirs(llm_output_path, exist_ok=True)

            file_operation_service = FileOperationService()

            planner_agent = PlannerAgent(self.llm_manager, llm_name)
            manager_agent = ManagerAgent(self.llm_manager, llm_name)
            coder_agent = CoderAgent(self.llm_manager, llm_name)

            print(f"    Instantiated agents for {llm_name}")

            try:
                # Step 1: Planner Agent generates initial plan
                user_request = "Generate a simple calculator application with basic arithmetic operations (add, subtract, multiply, divide) in Python. The application should have a command-line interface."
                print(f"    Planner Agent: Generating plan for '{user_request}'")
                initial_plan = planner_agent.execute(user_request)
                print(f"    Initial Plan: {initial_plan}")

                # Step 2: Manager Agent refines the plan (for now, just passes it through)
                print(f"    Manager Agent: Refining plan...")
                refined_plan = manager_agent.execute(initial_plan) # In a real scenario, manager might ask clarifying questions
                print(f"    Refined Plan: {refined_plan}")

                # Step 3: Coder Agent generates code based on the refined plan
                print(f"    Coder Agent: Generating code...")
                code_actions = coder_agent.execute(refined_plan) # Coder generates file operations
                print(f"    Generated Code Actions: {code_actions}")

                # Step 4: FileOperationService executes file actions
                print(f"    FileOperationService: Executing file operations...")
                # Ensure project_root is consistently llm_output_path for all agent-generated files
                file_operation_service.execute_actions(actions=code_actions.get('actions', []), project_root=llm_output_path)
                print(f"    File operations executed for {llm_name}")

                self._post_generation_tasks(llm_output_path, llm_name)

            except Exception as e:
                print(f"    Error during orchestration for {llm_name}: {e}")
                QMessageBox.critical(self, "Jedi Error", f"An error occurred during orchestration for {llm_name}: {e}")

            print(f"--- Finished orchestration for LLM: {llm_name} ---")
            self.results_list_widget.addItem(llm_output_path)

    def _post_generation_tasks(self, project_path, llm_name):
        print(f"    Running post-generation tasks for {llm_name} in {project_path}...")

        # Run black formatter
        print("        Running black formatter...")
        try:
            result = subprocess.run([sys.executable, "-m", "black", project_path], check=True, capture_output=True, text=True)
            print("        Black formatting complete.")
            if result.stdout:
                print(f"        Black stdout: {result.stdout}")
            if result.stderr:
                print(f"        Black stderr: {result.stderr}")
        except subprocess.CalledProcessError as e:
            print(f"        Black formatting failed: {e.stderr}")
            QMessageBox.warning(self, "Jedi Warning", f"Black formatting failed for {llm_name}: {e.stderr}")
        except Exception as e:
            print(f"        An unexpected error occurred during black formatting: {e}")
            QMessageBox.warning(self, "Jedi Warning", f"An unexpected error occurred during black formatting for {llm_name}: {e}")

        # Initialize Git repository and commit
        print("        Initializing Git repository and committing files...")
        try:
            # Remove .git if it exists to re-initialize cleanly
            git_path = os.path.join(project_path, ".git")
            if os.path.exists(git_path):
                print(f"        Removing existing .git directory: {git_path}")
                shutil.rmtree(git_path)

            result = subprocess.run(["git", "init"], cwd=project_path, check=True, capture_output=True, text=True)
            print("        Git init complete.")
            if result.stdout:
                print(f"        Git init stdout: {result.stdout}")
            if result.stderr:
                print(f"        Git init stderr: {result.stderr}")

            result = subprocess.run(["git", "add", "."], cwd=project_path, check=True, capture_output=True, text=True)
            print("        Git add complete.")
            if result.stdout:
                print(f"        Git add stdout: {result.stdout}")
            if result.stderr:
                print(f"        Git add stderr: {result.stderr}")

            result = subprocess.run(["git", "commit", "-m", f"Initial commit for {llm_name} generated code"], cwd=project_path, check=True, capture_output=True, text=True)
            print("        Git commit successful.")
            if result.stdout:
                print(f"        Git commit stdout: {result.stdout}")
            if result.stderr:
                print(f"        Git commit stderr: {result.stderr}")

        except subprocess.CalledProcessError as e:
            print(f"        Git operations failed: {e.stderr}")
            QMessageBox.warning(self, "Jedi Warning", f"Git operations failed for {llm_name}: {e.stderr}")
        except Exception as e:
            print(f"        An unexpected error occurred during Git operations: {e}")
            QMessageBox.warning(self, "Jedi Warning", f"An unexpected error occurred during Git operations for {llm_name}: {e}")


class DiffViewerDialog(QDialog):
    def __init__(self, diff_content, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Comparison Results")
        self.setGeometry(200, 200, 800, 600)

        layout = QVBoxLayout(self)

        self.diff_display = QTextEdit()
        self.diff_display.setReadOnly(True)
        layout.addWidget(self.diff_display)

        # Apply basic diff highlighting
        cursor = self.diff_display.textCursor()
        format_add = QTextCharFormat()
        format_add.setForeground(QColor("green"))
        format_remove = QTextCharFormat()
        format_remove.setForeground(QColor("red"))

        for line in diff_content.splitlines():
            if line.startswith('+'):
                cursor.insertText(line + '\n', format_add)
            elif line.startswith('-'):
                cursor.insertText(line + '\n', format_remove)
            else:
                cursor.insertText(line + '\n')

        self.diff_display.setTextCursor(cursor)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    llm_manager = LocalLLMManager()
    window = JediWindow(llm_manager)
    window.show()
    sys.exit(app.exec())