from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtWidgets import QLineEdit, QHBoxLayout, QWidget, QMessageBox, QFileDialog
import os
import sys
from PyQt6.QtWidgets import QApplication
from src.llm_service.agents import AGENTS
from src.services.file_operation_service import FileOperationService, CommandOutputEmitter

class JediWindow(QDialog):
    def __init__(self, llm_manager, parent=None):
        super().__init__(parent)
        self.llm_manager = llm_manager
        self.setWindowTitle("Jedi Automation Agent")
        self.setGeometry(200, 200, 800, 600)

        self.command_output_emitter = CommandOutputEmitter()
        self.file_operation_service = FileOperationService(self.command_output_emitter)

        self.layout = QVBoxLayout(self)

        self.label = QLabel("Welcome to the Jedi Automation Agent!")
        self.layout.addWidget(self.label)

        # Project Name Input
        project_name_layout = QHBoxLayout()
        project_name_label = QLabel("Project Name:")
        self.project_name_input = QLineEdit()
        self.project_name_input.setPlaceholderText("e.g., MyAwesomeProject")
        project_name_layout.addWidget(project_name_label)
        project_name_layout.addWidget(self.project_name_input)
        self.layout.addLayout(project_name_layout)

        # Output Directory Display (read-only for now, selection handled by MainWindow)
        output_dir_layout = QHBoxLayout()
        output_dir_label = QLabel("Output Directory:")
        self.output_dir_display = QLineEdit()
        self.output_dir_display.setReadOnly(True)
        self.output_dir_display.setText("") # Set initial text
        output_dir_layout.addWidget(output_dir_label)
        output_dir_layout.addWidget(self.output_dir_display)

        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._select_output_directory)
        output_dir_layout.addWidget(self.browse_button)

        self.layout.addLayout(output_dir_layout)

        self.start_button = QPushButton("Start Generation")
        self.start_button.clicked.connect(self._start_generation)
        self.layout.addWidget(self.start_button)

        # Project Idea Input
        project_idea_label = QLabel("Project Idea:")
        self.project_idea_input = QTextEdit()
        self.project_idea_input.setPlaceholderText("Describe your project idea here (e.g., 'Create a simple calculator application in Python with command-line interface').")
        self.project_idea_input.setFixedHeight(80) # Give it some height
        self.layout.addWidget(project_idea_label)
        self.layout.addWidget(self.project_idea_input)


    def _select_output_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory", self.output_dir_display.text())
        if directory:
            self.output_dir_display.setText(directory)


    def _start_generation(self):
        project_name = self.project_name_input.text()
        output_base_dir = self.output_dir_display.text()

        if not project_name:
            QMessageBox.warning(self, "Input Error", "Please enter a Project Name.")
            return

        if not output_base_dir:
            QMessageBox.warning(self, "Input Error", "Please select an Output Directory.")
            return

        project_idea = self.project_idea_input.toPlainText()
        if not project_idea:
            QMessageBox.warning(self, "Input Error", "Please enter a Project Idea.")
            return

        # Get available LLM names from the llm_manager
        llm_names = self.llm_manager.list_models()
        if not llm_names:
            QMessageBox.warning(self, "LLM Error", "No LLMs found. Please ensure Ollama is running and models are available.")
            return

        for llm_name in llm_names:
            QMessageBox.information(self, "Starting Generation", f"Starting generation for LLM: {llm_name}")

            # Sanitize llm_name for folder creation (replace invalid characters like ':')
            sanitized_llm_name = llm_name.replace(':', '-')

            # Construct subfolder name and ensure uniqueness with versioning
            version = 1
            while True:
                subfolder_name = f"{project_name}_{sanitized_llm_name}_v{version}"
                full_path = os.path.join(output_base_dir, subfolder_name)
                if not os.path.exists(full_path):
                    break
                version += 1

            print(f"Attempting to create folder: {full_path}") # Debug print

            try:
                os.makedirs(full_path, exist_ok=True)
                QMessageBox.information(self, "Folder Created", f"Created folder: {full_path}")

                # Orchestrate agents for this LLM
                self._orchestrate_agents(project_idea, llm_name, output_base_dir)

            except OSError as e:
                QMessageBox.critical(self, "Error", f"Failed to create folder {full_path}: {e}")


    def _orchestrate_agents(self, project_idea: str, llm_name: str, base_output_dir: str):
        """Orchestrates the Planner, Manager, and Coder agents for a given LLM."""
        QMessageBox.information(self, "Agent Orchestration", f"Orchestrating agents for {llm_name} in {base_output_dir}")

        # Set the current working directory for file operations
        sanitized_llm_name = llm_name.replace(':', '-')
        llm_output_path = os.path.join(base_output_dir, sanitized_llm_name)
        os.makedirs(llm_output_path, exist_ok=True)

        try:
            # --- Step 1: Manager Agent ---
            manager_system_prompt = AGENTS["manager"]["system_prompt"]
            manager_user_message = f"High-level goal: {project_idea}"

            conversation_history = [
                {"role": "system", "content": manager_system_prompt},
                {"role": "user", "content": manager_user_message},
            ]

            if not self.llm_manager:
                QMessageBox.critical(self, "LLM Manager Error", "LLM Manager is not initialized.")
                return

            # Check if the LLM manager's client is ready (e.g., connected to Ollama)
            # This might vary depending on the internal implementation of LocalLLMManager
            # For now, we'll assume a 'client' attribute and check its existence.
            # You might need to adjust this check based on LocalLLMManager's actual API.
            if not self.llm_manager:
                QMessageBox.critical(self, "LLM Manager Error", "LLM Manager is not initialized.")
                return

            # Ensure the specific LLM model is loaded before proceeding
            if not self.llm_manager.load_model(llm_name):
                QMessageBox.critical(self, "LLM Load Error", f"Failed to load LLM: {llm_name}. Skipping this LLM.")
                return # Exit this orchestration for the current LLM

            manager_response_content = ""
            for chunk in self.llm_manager.stream_chat(conversation_history):
                if "message" in chunk and "content" in chunk["message"]:
                    manager_response_content += chunk["message"]["content"]

            # Extract JSON from the LLM's response
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', manager_response_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                try:
                    import json
                    manager_actions = json.loads(json_str.strip())
                    if "actions" in manager_actions:
                        for action in manager_actions["actions"]:
                            if action["action"] == "create_file" and action["path"] == "project_plan.md":
                                # The project_root for this file operation is the current LLM's output directory
                                current_llm_output_dir = os.path.join(base_output_dir, sanitized_llm_name)
                                
                                # Ensure the directory exists before creating the file
                                os.makedirs(current_llm_output_dir, exist_ok=True)

                                # Execute the create_file action using file_operation_service.execute_actions
                                # The 'path' in the action dictionary should be relative to the project_root
                                file_action = {
                                    "action": "create_file",
                                    "path": action["path"], # This is 'project_plan.md'
                                    "content": action["content"]
                                }
                                self.file_operation_service.execute_actions(current_llm_output_dir, [file_action])
                                QMessageBox.information(self, "Manager Success", f"Manager created project_plan.md in {sanitized_llm_name}'s folder")
                                # Store the path to the project_plan.md for the Coder agent
                                project_plan_path = os.path.join(current_llm_output_dir, "project_plan.md")
                                break
                            else:
                                QMessageBox.warning(self, "Manager Warning", f"Unexpected Manager action: {action}")
                    else:
                        QMessageBox.warning(self, "Manager Warning", "Manager response missing 'actions' key.")

                except json.JSONDecodeError:
                    QMessageBox.critical(self, "Manager Error", f"Manager response was not valid JSON: {json_str}")
                except Exception as e:
                    QMessageBox.critical(self, "Manager Error", f"Error processing Manager response: {e}")
            else:
                QMessageBox.critical(self, "Manager Error", "Manager response did not contain a valid JSON block.")

            # --- Step 2: Planner Agent (Optional Refinement) ---
            # For now, we'll assume the Manager's project_plan.md is sufficient.
            # If a separate Planner refinement step is needed, it would go here.
            QMessageBox.information(self, "Agent Orchestration", "Skipping Planner Agent refinement step.")

            # --- Step 3: Coder Agent ---
            QMessageBox.information(self, "Agent Orchestration", "Starting Coder Agent step.")

            # Read the project_plan.md content
            if not os.path.exists(project_plan_path):
                QMessageBox.critical(self, "Coder Error", f"project_plan.md not found at {project_plan_path}. Cannot proceed with Coder agent.")
                return

            with open(project_plan_path, "r", encoding="utf-8") as f:
                project_plan_content = f.read()

            coder_system_prompt = AGENTS["coder"]["system_prompt"]
            coder_user_message = f"Project plan: {project_plan_content}\n\nHigh-level goal: {project_idea}"

            coder_conversation_history = [
                {"role": "system", "content": coder_system_prompt},
                {"role": "user", "content": coder_user_message},
            ]

            coder_response_content = ""
            for chunk in self.llm_manager.stream_chat(coder_conversation_history):
                if "message" in chunk and "content" in chunk["message"]:
                    coder_response_content += chunk["message"]["content"]
            
            # Extract JSON from the Coder's response
            coder_json_match = re.search(r'```json\s*(.*?)\s*```', coder_response_content, re.DOTALL)
            if coder_json_match:
                coder_json_str = coder_json_match.group(1)
                try:
                    coder_actions = json.loads(coder_json_str.strip())
                    if "actions" in coder_actions:
                        # Execute Coder's actions
                        self.file_operation_service.execute_actions(current_llm_output_dir, coder_actions["actions"])
                        QMessageBox.information(self, "Coder Success", f"Coder agent executed actions for {sanitized_llm_name}.")
                    else:
                        QMessageBox.warning(self, "Coder Warning", "Coder response missing 'actions' key.")
                except json.JSONDecodeError:
                    QMessageBox.critical(self, "Coder Error", f"Coder response was not valid JSON: {coder_json_str}")

        except Exception as e:
            QMessageBox.critical(self, "Jedi Orchestration Error", f"An error occurred during agent orchestration: {e}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = JediWindow(None) # Pass None as llm_manager for now
    window.show()
    sys.exit(app.exec())