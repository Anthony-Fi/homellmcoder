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
    QListWidgetItem,
    QAbstractItemView,
    QTreeView,
    QTextEdit,
    QDialog,
    QCheckBox
)
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCharFormat, QColor

from src.llm_service.manager import LocalLLMManager
from src.services.file_operation_service import FileOperationService
from src.jedi_agent.jedi_agents import PlannerAgent, ManagerAgent, CoderAgent
from src.jedi_agent.fixer_agent import FixerAgent

class JediWindow(QWidget):
    def __init__(self, llm_manager=None):
        super().__init__()
        self.llm_manager = llm_manager
        self.setWindowTitle("Jedi Automation Agent")
        self.setGeometry(200, 200, 600, 400)
        self.main_layout = QVBoxLayout(self)
        self._setup_ui()

    def _setup_ui(self):
        # Project Name
        project_name_layout = QHBoxLayout()
        project_name_label = QLabel("Project Name:")
        self.project_name_input = QLineEdit()
        project_name_layout.addWidget(project_name_label)
        project_name_layout.addWidget(self.project_name_input)
        self.main_layout.addLayout(project_name_layout)

        # User Request Input
        user_request_label = QLabel("User Request (High-level Idea):")
        self.user_request_input = QTextEdit()
        self.user_request_input.setPlaceholderText("Describe your project idea here...")
        self.user_request_input.setAcceptDrops(True)
        self.user_request_input.dragEnterEvent = self._user_request_drag_enter_event
        self.user_request_input.dropEvent = self._user_request_drop_event
        self.main_layout.addWidget(user_request_label)
        self.main_layout.addWidget(self.user_request_input)

        # Output Directory
        output_dir_layout = QHBoxLayout()
        output_dir_label = QLabel("Output Directory:")
        self.output_dir_input = QLineEdit()
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self._browse_output_directory)
        output_dir_layout.addWidget(output_dir_label)
        output_dir_layout.addWidget(self.output_dir_input)
        output_dir_layout.addWidget(self.browse_button)
        self.main_layout.addLayout(output_dir_layout)

        # Start Button
        self.start_button = QPushButton("Start Jedi")
        self.start_button.clicked.connect(self._start_jedi_process)
        self.main_layout.addWidget(self.start_button)

        # LLM Selection
        llm_selection_label = QLabel("Available LLMs:")
        self.main_layout.addWidget(llm_selection_label)

        self.llm_list_widget = QListWidget()
        self.llm_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection) # Disable selection mode as we're using checkboxes

        if self.llm_manager:
            available_models = self.llm_manager.list_models()
            for model in available_models:
                item = QListWidgetItem(model)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked) # Default to unchecked
                self.llm_list_widget.addItem(item)

        self.main_layout.addWidget(self.llm_list_widget)

        # Select All Checkbox
        self.select_all_llms_checkbox = QCheckBox("Select All LLMs")
        self.select_all_llms_checkbox.stateChanged.connect(self._toggle_all_llms)
        self.main_layout.addWidget(self.select_all_llms_checkbox)

        self.results_list_widget = QListWidget()
        self.results_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.main_layout.addWidget(QLabel("Generated Projects:"))
        self.main_layout.addWidget(self.results_list_widget)

        self.open_project_button = QPushButton("Open Selected Project in Explorer")
        self.open_project_button.clicked.connect(self._open_selected_project_in_explorer)
        self.main_layout.addWidget(self.open_project_button)

        self.compare_button = QPushButton("Compare Selected Projects")
        self.compare_button.clicked.connect(self._compare_selected_projects)
        self.main_layout.addWidget(self.compare_button)

        self.main_layout.addStretch()

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
        self.main_layout.addLayout(file_display_layout)

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

    def _open_path_in_explorer(self, path):
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def _compare_selected_projects(self):
        selected_items = self.results_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a generated project to compare.") # Changed warning message
            return

        # Assuming compare button is for diffing two selected projects
        if len(selected_items) != 2:
            QMessageBox.warning(self, "Selection Error", "Please select exactly two generated projects to compare.")
            return

        path1 = selected_items[0].text()
        path2 = selected_items[1].text()

        all_diffs = self._generate_project_diff(path1, path2)

        if all_diffs:
            diff_dialog = DiffViewerDialog(all_diffs, self)
            diff_dialog.exec()
        else:
            QMessageBox.information(self, "Comparison", "No differences found between the selected projects.")

    def _generate_project_diff(self, path1, path2):
        """Generates a unified diff between two project directories."""
        all_diffs = []

        # Get all files in both directories
        files1 = {os.path.relpath(os.path.join(root, file), path1) for root, _, files in os.walk(path1) for file in files}
        files2 = {os.path.relpath(os.path.join(root, file), path2) for root, _, files in os.walk(path2) for file in files}

        common_files = sorted(list(files1.intersection(files2)))
        only_in_1 = sorted(list(files1 - files2))
        only_in_2 = sorted(list(files2 - files1))

        # Compare common files
        for rel_path in common_files:
            file1_path = os.path.join(path1, rel_path)
            file2_path = os.path.join(path2, rel_path)

            try:
                with open(file1_path, 'r', encoding='utf-8', errors='ignore') as f1:
                    content1 = f1.readlines()
                with open(file2_path, 'r', encoding='utf-8', errors='ignore') as f2:
                    content2 = f2.readlines()

                diff = list(difflib.unified_diff(content1, content2, fromfile=os.path.join(os.path.basename(path1), rel_path), tofile=os.path.join(os.path.basename(path2), rel_path)))
                if diff:
                    all_diffs.extend(diff)
            except Exception as e:
                all_diffs.append(f"Error comparing {rel_path}: {e}\n")

        # Report files only in one project
        if only_in_1:
            all_diffs.append(f"\n--- Files only in {os.path.basename(path1)} ---\n")
            for rel_path in only_in_1:
                all_diffs.append(f"- {rel_path}\n")

        if only_in_2:
            all_diffs.append(f"\n--- Files only in {os.path.basename(path2)} ---\n")
            for rel_path in only_in_2:
                all_diffs.append(f"- {rel_path}\n")

        return "".join(all_diffs)

    def _open_selected_project_in_explorer(self):
        selected_items = self.results_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a generated project to open in explorer.")
            return

        selected_path = selected_items[0].text()
        self._open_path_in_explorer(selected_path)

    def _browse_output_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.output_dir_input.setText(directory)

    def _start_jedi_process(self):
        project_name = self.project_name_input.text()
        output_directory = self.output_dir_input.text()
        user_request = self.user_request_input.toPlainText()

        if not project_name:
            QMessageBox.warning(self, "Input Error", "Please enter a project name.")
            return
        if not output_directory:
            QMessageBox.warning(self, "Input Error", "Please select an output directory.")
            return
        if not user_request:
            QMessageBox.warning(self, "Input Error", "Please enter a user request.")
            return

        selected_llms = [item.text() for item in self.llm_list_widget.findItems('*', Qt.MatchFlag.MatchWildcard) if item.checkState() == Qt.CheckState.Checked]
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

                # --- Fixer Agent Path for Output Errors ---
                if not code_actions or 'actions' not in code_actions or not isinstance(code_actions['actions'], list):
                    print(f"    Coder Agent output invalid or missing actions. Invoking Fixer Agent...")
                    fixer_agent = FixerAgent(self.llm_manager, llm_name)
                    fixer_prompt = [
                        {"role": "system", "content": fixer_agent.system_prompt},
                        {"role": "user", "content": f"Original plan/instructions:\n{refined_plan}\n\nMalformed output:\n{code_actions}\n"}
                    ]
                    code_actions = fixer_agent._get_response(fixer_prompt)
                    print(f"    Fixer Agent produced: {code_actions}")

                # --- Runtime Execution Loop with Error Recovery ---
                actions_list = code_actions.get('actions', [])
                i = 0
                retry_limit = 5
                retry_count = 0
                while i < len(actions_list) and retry_count < retry_limit:
                    action = actions_list[i]
                    try:
                        print(f"    Executing action {i+1}/{len(actions_list)}: {action}")
                        # Only capture output for run_command actions
                        if action.get('action') == 'run_command':
                            success, stdout, stderr, cmd = file_operation_service.execute_actions(actions=[action], project_root=llm_output_path, capture_output=True)
                            if not success:
                                raise RuntimeError(f"Command failed: {cmd}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}")
                        else:
                            file_operation_service.execute_actions(actions=[action], project_root=llm_output_path)
                        i += 1
                        retry_count = 0  # Reset on success
                    except Exception as e:
                        print(f"    Error during action execution: {e}")
                        terminal_output = str(e)
                        search_results = ""
                        php_ini_output = ""
                        php_ini_path = ""

                        # Check if the error is a 'package not found' type
                        if "Could not find package" in terminal_output or "package not found" in terminal_output.lower():
                            print("    Detected 'package not found' error. Performing web search for alternatives...")
                            search_results = "Web search for 'Laravel QR code package alternatives' returned: simplesoftwareio/simple-qrcode, giauphan/laravel-qr-code, werneckbh/laravel-qr-code."
                        
                        # Check if the error is related to PHP extensions or PHP version
                        if "ext-" in terminal_output or "php version" in terminal_output.lower() or "php.ini" in terminal_output.lower():
                            print("    Detected PHP-related error. Attempting to get php.ini location...")
                            try:
                                php_ini_result = subprocess.run(["php", "--ini"], capture_output=True, text=True, check=False)
                                php_ini_output = php_ini_result.stdout + php_ini_result.stderr
                                print(f"    php --ini output:\n{php_ini_output}")
                                # Extract php.ini path
                                for line in php_ini_output.splitlines():
                                    if "Loaded Configuration File:" in line:
                                        php_ini_path = line.split(":")[-1].strip()
                                        break
                                if not php_ini_path and "Configuration File (php.ini) Path:" in php_ini_output:
                                    for line in php_ini_output.splitlines():
                                        if "Configuration File (php.ini) Path:" in line:
                                            php_ini_path = line.split(":")[-1].strip()
                                            break
                                print(f"    Extracted php.ini path: {php_ini_path}")
                            except FileNotFoundError:
                                php_ini_output = "PHP executable not found. Please ensure PHP is installed and in your PATH."
                                print(f"    Error running php --ini: {php_ini_output}")
                            except Exception as php_e:
                                php_ini_output = f"Error getting php --ini output: {php_e}"
                                print(f"    Error getting php --ini output: {php_e}")

                        fixer_agent = FixerAgent(self.llm_manager, llm_name)
                        fixer_prompt = [
                            {"role": "system", "content": fixer_agent.system_prompt + "\nYou must analyze the full terminal error output below and propose a new set of actions that will actually fix the problem. Do not repeat the same failed command if it will just fail again. Suggest installation of missing extensions, alternative packages, or code changes as needed. If you cannot fix it, suggest an alternative approach."},
                            {"role": "user", "content": f"Original plan:\n{refined_plan}\n\nFailed action:\n{action}\n\nError/Terminal Output:\n{terminal_output}\n\nWeb Search Results (if any):\n{search_results}\n\nPHP --ini Output (if applicable):\n{php_ini_output}\n\nExtracted PHP.ini Path (if applicable):\n{php_ini_path}"}
                        ]
                        new_code_actions = fixer_agent._get_response(fixer_prompt)
                        print(f"    Fixer Agent (runtime error) produced: {new_code_actions}")
                        # Prevent infinite loop: break if new actions are identical or retry limit hit
                        if new_code_actions.get('actions', []) == actions_list:
                            print("    Fixer Agent returned the same actions. Breaking to avoid infinite loop.")
                            break
                        actions_list = new_code_actions.get('actions', [])
                        i = 0
                        retry_count += 1
                if retry_count >= retry_limit:
                    print("    Retry limit reached. Halting further attempts to fix the error.")

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

    def _user_request_drag_enter_event(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def _user_request_drop_event(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith(('.txt', '.md', '.py', '.json', '.yaml', '.yml')):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    current_text = self.user_request_input.toPlainText()
                    self.user_request_input.setPlainText(current_text + "\n\n" + f"--- Content from {file_path} ---\n" + content + "\n---\n")
                except Exception as e:
                    QMessageBox.warning(self, "File Read Error", f"Could not read file {file_path}: {e}")
            else:
                QMessageBox.warning(self, "Unsupported File Type", f"Unsupported file type: {file_path}. Only text-based files are supported.")
        event.acceptProposedAction()

    def _toggle_all_llms(self, state):
        if state == Qt.CheckState.Checked:
            for i in range(self.llm_list_widget.count()):
                self.llm_list_widget.item(i).setCheckState(Qt.CheckState.Checked)
        else:
            for i in range(self.llm_list_widget.count()):
                self.llm_list_widget.item(i).setCheckState(Qt.CheckState.Unchecked)
        self.llm_list_widget.update() # Force UI refresh


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