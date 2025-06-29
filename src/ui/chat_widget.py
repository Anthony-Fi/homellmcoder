import logging
from PyQt6.QtCore import QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QHBoxLayout,
    QScrollArea,
    QMessageBox,
    QComboBox,
    QLabel,
)
from PyQt6.QtGui import QFont
import json
import os
import re

from .components.chat_bubble import ChatBubble
from .components.chat_worker import ChatWorker
from .components.chat_input_box import ChatInputBox
from .components.ai_status_indicator import AIStatusIndicator
from ..services.history_service import HistoryService
from ..services.file_operation_service import FileOperationService
from src.llm_service.agents import AGENTS


class LLMChatWidget(QWidget):
    """A widget for interacting with the loaded LLM."""

    change_requested = pyqtSignal(dict)
    plan_updated = pyqtSignal(str)

    def __init__(
        self,
        llm_manager,
        history_service: HistoryService = None,
        file_operation_service: FileOperationService = None,
        terminal_widget=None,
        plan_widget=None,
        parent=None,
    ):
        super().__init__(parent)
        self.llm_manager = llm_manager
        self.project_root = None
        self.ai_bubble = None
        self.current_ai_response = ""
        self.status_indicator = AIStatusIndicator()
        self.conversation_history = []
        self.agents = AGENTS
        self.current_agent_key = "manager"  # Default to the manager
        self.pending_actions = None
        self.file_op_service = file_operation_service or FileOperationService()
        self.terminal_widget = terminal_widget
        self.plan_widget = plan_widget
        logging.info(f"LLMChatWidget: self.plan_widget set to {self.plan_widget}")

        # Service Dependencies
        self.history_service = history_service or HistoryService()

        self.thread = None
        self.worker = None

        self._init_ui()

        # Connect signals if plan_widget is provided
        if self.plan_widget:
            logging.info("LLMChatWidget: Connecting plan_widget.run_planner_requested to _on_run_planner_button_clicked.")
            self.plan_widget.run_planner_requested.connect(self._on_run_planner_button_clicked)


    def set_project_root(self, project_root):
        self.project_root = project_root
        self.load_history(project_root)

    def send_message(self):
        """Sends the user's message to the LLM and prepares for a streaming response."""
        prompt = self.input_box.toPlainText().strip()
        if not prompt:
            return

        if not self.llm_manager or not self.llm_manager.loaded_model:
            QMessageBox.warning(
                self,
                "Model Not Loaded",
                "Please load an LLM from the Tools menu before starting a chat.",
            )
            return

        self.set_status_indicator(True)  # Thinking
        self.input_box.clear()
        self.current_ai_response = ""

        self.add_message_to_view(prompt, is_user=True)
        self.conversation_history.append({"role": "user", "content": prompt})
        self.ai_bubble = self.add_message_to_view(
            "", is_user=False
        )  # Create empty bubble for AI

        # Prepare messages for the worker, including the agent's system prompt
        system_prompt = self.agents[self.current_agent_key]["system_prompt"]
        messages_for_worker = [{"role": "system", "content": system_prompt}] + self.conversation_history

        # --- New: Inject file content for Refactor agent if applicable ---
        if self.current_agent_key == "refactor" and "refactor" in prompt.lower() and ".py" in prompt.lower():
            # Attempt to extract file path from prompt (more robust heuristic)
            # Looks for words ending in .py, potentially with path components
            match = re.search(r'\b([\w/\\.-]+\.py)\b', prompt)
            if match:
                file_path_relative = match.group(1)
                full_file_path = os.path.join(self.project_root, file_path_relative)
                if os.path.exists(full_file_path):
                    try:
                        with open(full_file_path, 'r', encoding='utf-8') as f:
                            file_content = f.read()
                        # Inject file content into the conversation history for the LLM
                        messages_for_worker.append({"role": "user", "content": f"Here is the content of {file_path_relative} to refactor:\n```python\n{file_content}\n```"})
                        logging.info(f"Injected content of {file_path_relative} for refactoring.")
                    except Exception as e:
                        logging.error(f"Could not read file {full_file_path}: {e}")
                else:
                    logging.warning(f"File not found for refactoring: {full_file_path}")
                    self.display_agent_message(f"Refactor Agent: Could not find the specified file: {file_path_relative}. Please ensure the file path is correct and exists within your project root.", is_user=False, agent_name="Refactor")
            else:
                logging.warning("Could not extract file path from refactor prompt.")
                self.display_agent_message("Refactor Agent: Please specify the Python file you want to refactor (e.g., 'refactor my_module.py').", is_user=False, agent_name="Refactor")
        # --- End New Section ---

        # --- New: Inject project_plan.md content for Coder agent ---
        if self.current_agent_key == "coder":
            project_plan_path = os.path.join(self.project_root, "project_plan.md")
            if os.path.exists(project_plan_path):
                try:
                    with open(project_plan_path, 'r', encoding='utf-8') as f:
                        project_plan_content = f.read()
                    messages_for_worker.append({"role": "user", "content": f"Here is the project plan you need to follow:\n```markdown\n{project_plan_content}\n```"})
                    logging.info("Injected project_plan.md content for Coder agent.")
                except Exception as e:
                    logging.error(f"Could not read project_plan.md: {e}")
            else:
                logging.warning("project_plan.md not found for Coder agent.")
        # --- End New Section ---

        logging.debug(f"Messages sent to LLM: {messages_for_worker}")

        # Setup and start the worker thread
        self.thread = QThread()
        self.worker = ChatWorker(self.llm_manager, messages_for_worker)
        self.worker.moveToThread(self.thread)

        self.worker.response_updated.connect(self._handle_response_chunk)
        self.worker.error_occurred.connect(self.on_worker_error)
        self.worker.finished.connect(self._on_worker_finished)

        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def _handle_response_chunk(self, chunk):
        """Appends a chunk of the AI's response to the chat view."""
        self.current_ai_response += chunk
        if self.ai_bubble:
            self.ai_bubble.set_text(self.current_ai_response + " █")

        # Log the raw LLM response for debugging purposes


    def _on_worker_finished(self):
        """Handles cleanup and delegation after the worker thread is done."""
        response_text = self.current_ai_response

        # Check for tool use
        tool_request = self._parse_tool_request(response_text)
        if tool_request:
            # If the current agent is the manager, and it's trying to use a tool,
            # log a warning and do NOT execute the tool. This enforces the manager's role.
            if self.current_agent_key == "manager":
                logging.warning(
                    "Manager agent attempted to use a tool. This is not allowed. "
                    "Manager should only create plan.md."
                )
                # Fall through to action parsing, which will filter out non-plan.md actions
            else:
                self._execute_tool(tool_request)
                return  # The tool execution will trigger the next step

        logging.debug(f"Current agent key in _on_worker_finished: {self.current_agent_key}")
        # Check for any agent response containing file actions
        actions_data = None
        if self.current_agent_key == "planner":
            # Inlined _extract_planner_actions_strictly logic
            match = re.search(r"```json\s*({.*})\s*```", response_text, re.DOTALL)
            if match:
                json_str = match.group(1)
            else:
                json_str = response_text.strip()
                start_idx = json_str.find('{')
                end_idx = json_str.rfind('}')
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    json_str = json_str[start_idx : end_idx + 1]
                else:
                    logging.warning("Could not find a valid JSON object in the response for Planner agent.")
                    actions_data = None

            if json_str:
                try:
                    data = json.loads(json_str)
                    if isinstance(data, dict) and "actions" in data:
                        planner_approved_actions = []
                        for action in data.get("actions", []):
                            if action.get("action") in ["create_file", "edit_file"] and action.get("path") == "project_plan.md":
                                planner_approved_actions.append(action)
                            else:
                                logging.warning(f"Planner agent attempted to generate disallowed action: {action}")
                        data["actions"] = planner_approved_actions
                        if not planner_approved_actions:
                            self.display_agent_message("The Planner agent's output was rejected. It must ONLY generate actions for 'project_plan.md'. Please try again or refine the goal.", is_user=False, agent_name="Planner")
                        actions_data = data
                except json.JSONDecodeError:
                    logging.info("Initial JSON parse failed for Planner agent, attempting robust action extraction.")
                    action_pattern = re.compile(r'{\s*"action"\s*:\s*"(?P<action>[^"]*)",\s*"path"\s*:\s*"(?P<path>[^"]*)"(?:,\s*"content"\s*:\s*(?P<content_val>.*?))?}', re.DOTALL)

                    extracted_actions = []
                    for m in action_pattern.finditer(json_str):
                        action_dict = {
                            "action": m.group("action"),
                            "path": m.group("path")
                        }
                        content_val = m.group("content_val")
                        if content_val:
                            content_val = content_val.strip()
                            if content_val.startswith('"""') and content_val.endswith('"""'):
                                content_val = content_val.strip('"""')
                            elif content_val.startswith('"') and content_val.endswith('"'):
                                content_val = content_val.strip('"')

                            content_val = content_val.replace('\\n', '\n').replace('\\"', '"')
                            action_dict["content"] = content_val

                        extracted_actions.append(action_dict)

                    if extracted_actions:
                        logging.info(f"Successfully extracted actions for Planner agent using robust parsing: {extracted_actions}")
                        planner_approved_actions = []
                        for action in extracted_actions:
                            if action.get("action") in ["create_file", "edit_file"] and action.get("path") == "project_plan.md":
                                planner_approved_actions.append(action)
                            else:
                                logging.warning(f"Planner agent attempted to generate disallowed action (robust extract): {action}")
                        if not planner_approved_actions:
                            self.display_agent_message("The Planner agent's output was rejected (robust extract). It must ONLY generate actions for 'project_plan.md'. Please try again or refine the goal.", is_user=False, agent_name="Planner")
                        actions_data = {"actions": planner_approved_actions}
                    else:
                        logging.warning("Robust action extraction failed to find any actions for Planner agent.")
                        actions_data = None
            else:
                actions_data = None
        elif self.current_agent_key == "manager":
            actions_data = self._extract_manager_actions_strictly(response_text)
        else:
            actions_data = self._extract_json_actions(response_text)

        if actions_data:
            # Filter actions: For Manager agent, only allow create_file for plan.md
            if self.current_agent_key == "manager":
                filtered_actions = []
                for action in actions_data.get("actions", []):
                    if action.get("action") == "create_file" and action.get("path") == "plan.md":
                        filtered_actions.append(action)
                actions_data["actions"] = filtered_actions
            # Dedicated parsing and strict filtering for Planner agent
            elif self.current_agent_key == "planner":
                filtered_actions = []
                for action in actions_data.get("actions", []):
                    action_type = action.get("action")
                    action_path = action.get("path")

                    if action_path == "project_plan.md":
                        # Allow 'create_file' if project_plan.md does not exist, otherwise force 'edit_file'
                        if action_type == "create_file" and not os.path.exists(os.path.join(self.project_root, "project_plan.md")):
                            filtered_actions.append(action)
                        elif action_type == "edit_file" and os.path.exists(os.path.join(self.project_root, "project_plan.md")):
                            filtered_actions.append(action)
                        else:
                            logging.warning(f"Planner agent attempted invalid action ({action_type}) or path ({action_path}) for project_plan.md. Action discarded.")
                    else:
                        logging.warning(f"Planner agent attempted to modify forbidden file: {action_path}. Action discarded.")
                actions_data["actions"] = filtered_actions
            # Allow run_command for Coder agent, but strictly forbid plan files
            elif self.current_agent_key == "coder":
                coder_approved_actions = []
                for action in actions_data.get("actions", []):
                    action_type = action.get("action")
                    action_path = action.get("path")

                    # Disallow plan.md and project_plan.md for Coder agent
                    if action_path in ["plan.md", "project_plan.md"]:
                        logging.warning(f"Coder agent attempted to {action_type} {action_path}. This is forbidden and the action will be discarded.")
                        continue # Skip this action

                    if action_type in ["create_file", "edit_file", "run_command", "create_directory"]:
                        coder_approved_actions.append(action)
                    else:
                        logging.warning(f"Coder agent attempted to use unsupported action: {action_type}. This action will be discarded.")

                actions_data["actions"] = coder_approved_actions
                if not coder_approved_actions:
                    self.display_agent_message("Coder Agent: Your request did not result in any valid coding actions (e.g., create_file, edit_file, create_directory, run_command). Please provide a specific coding task based on the project plan.", is_user=False, agent_name="Coder")

            if actions_data.get("actions"): # Only display if there are valid actions after filtering
                # For Manager agent, update the AI bubble with the plan.md content
                if self.current_agent_key == "manager" and actions_data["actions"] and actions_data["actions"][0].get("path") == "plan.md":
                    plan_content = actions_data["actions"][0].get("content", "")
                    self.ai_bubble.set_text(f"Here's the proposed plan.md:\n\n```markdown\n{plan_content}\n```")
                self._display_actions_for_review(actions_data)
                self.thread.quit()
                self.thread.wait() # Wait for the thread to finish
                self.set_status_indicator(False)
                self.save_chat_history()
                self.input_box.setEnabled(True) # Explicitly enable chat input
                return
            else:
                logging.warning("No valid actions to display after filtering. Discarding all actions.")
                self.set_status_indicator(False)
                self.input_box.setEnabled(True)
                self.save_chat_history()
                return

        self.thread.quit()
        self.thread.wait() # Wait for the thread to finish
        self.set_status_indicator(False)
        self.save_chat_history()
        self.input_box.setEnabled(True) # Explicitly enable chat input

    def on_worker_error(self, error_message):
        """Displays an error message from the worker thread."""
        self.set_status_indicator(False)  # Idle
        QMessageBox.critical(self, "AI Error", error_message)
        if self.thread is not None:
            self.thread.quit()
            self.thread.wait()
            self.thread = None
        self.worker = None

    def add_message_to_view(self, text, is_user, is_final=False):
        """Adds a new chat bubble to the conversation view and returns it."""
        bubble = ChatBubble(text, is_user, self)
        bubble.change_requested.connect(self._handle_ai_file_change)
        # If loading a final message from history, we need to re-run set_text
        # to parse for the action button.
        if is_final:
            bubble.set_text(text, is_final=True)

        self.conversation_view_layout.addWidget(bubble)
        QTimer.singleShot(10, self._scroll_to_bottom)
        return bubble

    def _handle_ai_file_change(self, change_data):
        """Callback for when an 'Apply Change' button is clicked."""
        try:
            actions = change_data.get("actions", [])
            if not actions:
                raise ValueError("No actions found in the response.")
            self.file_op_service.execute_actions(self.project_root, actions)
            QMessageBox.information(
                self, "Success", f"{len(actions)} action(s) executed successfully."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to execute action: {e}")
            logging.error(f"Error executing file change: {e}", exc_info=True)

    def clear_chat(self):
        """Clears the chat history and the view."""
        while self.conversation_view_layout.count():
            child = self.conversation_view_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.conversation_history = []
        if self.project_root:
            self.history_service.save_history(
                self.project_root, self.conversation_history
            )
        self.ai_bubble = None
        self.current_ai_response = ""

    def load_history(self, project_root):
        """Loads chat history for a project and populates the view."""
        self.clear_chat()
        self.project_root = project_root
        if not self.project_root:
            return
        self.conversation_history = self.history_service.load_history(project_root)
        for message in self.conversation_history:
            is_user = message["role"] == "user"
            self.add_message_to_view(message["content"], is_user=is_user, is_final=True)

    def set_status_indicator(self, is_busy):
        """Sets the status indicator and enables/disables input elements."""
        if is_busy:
            self.status_indicator.set_busy(True)
            self.send_button.setEnabled(False)
            self.input_box.setEnabled(False)
        else:
            self.status_indicator.set_busy(False)
            self.send_button.setEnabled(True)
            self.input_box.setEnabled(True)
            self.input_box.setFocus()

    def _init_ui(self):
        """Initializes the UI components of the widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        # Agent Selection Dropdown
        agent_selection_layout = QHBoxLayout()
        agent_label = QLabel("Agent:")
        self.agent_combo_box = QComboBox()
        for key, agent_data in self.agents.items():
            self.agent_combo_box.addItem(agent_data["name"], userData=key)
        self.agent_combo_box.setCurrentIndex(list(self.agents.keys()).index(self.current_agent_key))
        self.agent_combo_box.currentIndexChanged.connect(self._on_agent_changed)

        agent_selection_layout.addWidget(agent_label)
        agent_selection_layout.addWidget(self.agent_combo_box)
        layout.addLayout(agent_selection_layout)

        self.conversation_view = QScrollArea()
        self.conversation_view.setWidgetResizable(True)
        self.conversation_view_widget = QWidget()
        self.conversation_view.setWidget(self.conversation_view_widget)
        self.conversation_view_layout = QVBoxLayout(self.conversation_view_widget)
        self.conversation_view_layout.setContentsMargins(10, 10, 10, 10)
        self.conversation_view_layout.addStretch()

        layout.addWidget(self.conversation_view)

        self.input_box = ChatInputBox()
        self.input_box.send_message.connect(self.send_message)
        self.input_box.setFont(QFont("Segoe UI", 10))

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.status_indicator)
        input_layout.addWidget(self.input_box, 1)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_button)

        self.apply_changes_button = QPushButton("Apply Changes")
        self.apply_changes_button.clicked.connect(self._apply_changes)
        self.apply_changes_button.hide() # Initially hidden
        input_layout.addWidget(self.apply_changes_button)

        layout.addLayout(input_layout)

    def shutdown(self):
        """Gracefully shuts down the ChatWorker thread if it's running."""
        if self.thread and self.thread.isRunning():
            logging.info("LLMChatWidget: Shutting down ChatWorker thread...")
            self.worker.stop()
            self.thread.quit()
            self.thread.wait(5000)  # Wait up to 5 seconds for the thread to finish
            if self.thread.isRunning():
                logging.warning("LLMChatWidget: ChatWorker thread did not terminate gracefully. Terminating...")
                self.thread.terminate()
            self.worker.deleteLater()
            self.thread.deleteLater()
            self.thread = None
            self.worker = None

    def _apply_changes(self):
        """Applies the pending actions to the file system."""
        if self.pending_actions:
            logging.debug(f"Applying changes with pending_actions: {self.pending_actions}")
            try:
                # Ensure self.pending_actions is a dictionary with an 'actions' key
                actions_to_execute = []
                if isinstance(self.pending_actions, dict) and "actions" in self.pending_actions:
                    actions_to_execute = self.pending_actions["actions"]
                elif isinstance(self.pending_actions, list):
                    actions_to_execute = self.pending_actions
                else:
                    raise ValueError("pending_actions is not in the expected format (neither a dict with 'actions' key nor a list).")

                self.file_op_service.execute_actions(self.project_root, actions_to_execute)
                QMessageBox.information(self, "Success", f"{len(actions_to_execute)} action(s) executed successfully.")
                self.pending_actions = None # Clear pending actions after applying
                self.apply_changes_button.hide() # Hide button after applying
                self.input_box.setEnabled(True) # Re-enable input box
                self.set_status_indicator(False) # Set status to idle
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to execute actions: {e}")
                logging.error(f"Error applying changes: {e}", exc_info=True)
        else:
            QMessageBox.warning(self, "No Actions", "No pending actions to apply.")

        self.save_chat_history() # Ensure history is saved on shutdown

    def _display_actions_for_review(self, actions_data):
        """Displays the proposed actions to the user and shows the Apply Changes button."""
        self.pending_actions = actions_data
        # Update the AI bubble to show a summary of changes
        summary_text = "I have generated the following proposed changes:\n\n"
        for action in actions_data.get("actions", []):
            action_type = action.get("action", "unknown")
            path = action.get("path", "unknown")
            summary_text += f"- {action_type.replace('_', ' ').title()}: {path}\n"
        summary_text += "\nClick 'Apply Changes' to execute them, or continue the conversation to refine."
        
        if self.ai_bubble:
            self.ai_bubble.set_text(summary_text)
        else:
            self.add_message_to_view(summary_text, is_user=False)

        self.apply_changes_button.show()
        self.input_box.setEnabled(False) # Disable input until action is taken

    def _on_agent_changed(self, index):
        self.current_agent_key = self.agent_combo_box.itemData(index)
        logging.info(f"Switched to {self.agents[self.current_agent_key]['name']}")

    def _scroll_to_bottom(self):
        """Scrolls the conversation view to the bottom."""
        scroll_bar = self.conversation_view.verticalScrollBar()
        QTimer.singleShot(100, lambda: scroll_bar.setValue(scroll_bar.maximum()))

    def save_chat_history(self):
        """Saves the current chat history to a file."""
        if self.project_root:
            self.history_service.save_history(
                self.project_root, self.conversation_history
            )
            history_path = self.history_service.get_history_path(self.project_root)
            logging.info(f"Saved chat history to {history_path}")

    def _add_message(self, role, content):
        self.conversation_history.append({"role": role, "content": content})
        self.add_message_to_view(content, role == "assistant")

    def _is_json_actions(self, text: str) -> bool:
        """Checks if the text is a JSON string with an 'actions' list."""
        try:
            data = json.loads(text)
            return isinstance(data, dict) and "actions" in data
        except json.JSONDecodeError:
            return False

    def _extract_json_actions(self, text: str) -> dict | None:
        """Extracts a JSON object containing file actions from the response."""
        match = re.search(r"```json\s*({.*})\s*```", text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            # Fallback for raw JSON, stripping whitespace and non-printable characters
            json_str = text.strip()
            # Attempt to find the first '{' and last '}' to isolate the JSON object
            start_idx = json_str.find('{')
            end_idx = json_str.rfind('}')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = json_str[start_idx : end_idx + 1]
            else:
                logging.warning("Could not find a valid JSON object in the response.")
                return None

        # If initial parsing fails, try to manually parse action blocks
        try:
            # First, try parsing the cleaned json_str directly
            data = json.loads(json_str)
            if isinstance(data, dict) and "actions" in data:
                return data
        except json.JSONDecodeError:
            logging.info("Initial JSON parse failed, attempting robust action extraction.")
            # Regex to find individual action blocks, assuming they start with { and contain "action" and "path"
            # This is a heuristic and might need refinement based on more LLM outputs
            action_pattern = re.compile(r'\{\s*"action"\s*:\s*"(?P<action>[^"]*)",\s*"path"\s*:\s*"(?P<path>[^"]*)"(?:,\s*"content"\s*:\s*(?P<content_val>.*?))?\}', re.DOTALL)
            
            extracted_actions = []
            for m in action_pattern.finditer(json_str):
                action_dict = {
                    "action": m.group("action"),
                    "path": m.group("path")
                }
                content_val = m.group("content_val")
                if content_val:
                    # Attempt to clean and unescape content if it was part of the match
                    # This might still be problematic if content itself contains complex JSON
                    # For now, assume it's a string that needs to be unquoted and unescaped
                    content_val = content_val.strip()
                    if content_val.startswith('"""') and content_val.endswith('"""'):
                        content_val = content_val.strip('"""')
                    elif content_val.startswith('"') and content_val.endswith('"'):
                        content_val = content_val.strip('"')
                    
                    # Basic unescaping for common JSON escapes
                    content_val = content_val.replace('\\n', '\n').replace('\\"', '"')
                    action_dict["content"] = content_val
                
                extracted_actions.append(action_dict)
            
            if extracted_actions:
                logging.info(f"Successfully extracted actions using robust parsing: {extracted_actions}")
                return {"actions": extracted_actions}
            else:
                logging.warning("Robust action extraction failed to find any actions.")
                return None

        # The previous pre-processing for escaping content is now less necessary if the above robust parsing works
        # but keeping it for now as a fallback or for cases where the LLM does output valid structure with bad content escaping.
        def escape_json_content(match):
            content_value = match.group(1)
            escaped_content = content_value.strip('"').replace('\n', '\\n').replace('"', '\"')
            return f'"{escaped_content}"'

        processed_json_str = re.sub(r'"content"\s*:\s*("""[^"]*"""|"[^"]*")', escape_json_content, json_str, flags=re.DOTALL)

        try:
            data = json.loads(processed_json_str)
            if isinstance(data, dict) and "actions" in data:
                return data
        except json.JSONDecodeError as e:
            logging.error(f"JSON decoding failed: {e}\nAttempted to decode: {processed_json_str}")
            return None

    def _extract_planner_actions_strictly(self, text: str) -> dict | None:
        """Extracts a JSON object containing file actions from the Planner agent's response."""
        # Attempt to find the JSON block, with or without ```json ``` wrapper
        match = re.search(r"```json\s*({.*})\s*```", text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            # Fallback for raw JSON, stripping whitespace and non-printable characters
            json_str = text.strip()
            # Attempt to find the first '{' and last '}' to isolate the JSON object
            start_idx = json_str.find('{')
            end_idx = json_str.rfind('}')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = json_str[start_idx : end_idx + 1]
            else:
                logging.warning("Could not find a valid JSON object in the response for Planner agent.")
                return None

        # If initial parsing fails, try to manually parse action blocks
        try:
            # First, try parsing the cleaned json_str directly
            data = json.loads(json_str)
            if isinstance(data, dict) and "actions" in data:
                # This is the strict filtering for Planner agent, applied after successful JSON parse
                planner_approved_actions = []
                for action in data.get("actions", []):
                    if action.get("action") in ["create_file", "edit_file"] and action.get("path") == "project_plan.md":
                        planner_approved_actions.append(action)
                    else:
                        logging.warning(f"Planner agent attempted to generate disallowed action: {action}")
                data["actions"] = planner_approved_actions
                if not planner_approved_actions:
                    self.display_agent_message("The Planner agent's output was rejected. It must ONLY generate actions for 'project_plan.md'. Please try again or refine the goal.", is_user=False, agent_name="Planner")
                return data
        except json.JSONDecodeError:
            logging.info("Initial JSON parse failed for Planner agent, attempting robust action extraction.")
            # Regex to find individual action blocks, assuming they start with { and contain "action" and "path"
            action_pattern = re.compile(r'{\s*"action"\s*:\s*"(?P<action>[^"]*)",\s*"path"\s*:\s*"(?P<path>[^"]*)"(?:,\s*"content"\s*:\s*(?P<content_val>.*?))?}', re.DOTALL)

            extracted_actions = []
            for m in action_pattern.finditer(json_str):
                action_dict = {
                    "action": m.group("action"),
                    "path": m.group("path")
                }
                content_val = m.group("content_val")
                if content_val:
                    content_val = content_val.strip()
                    if content_val.startswith('"""') and content_val.endswith('"""'):
                        content_val = content_val.strip('"""')
                    elif content_val.startswith('"') and content_val.endswith('"'):
                        content_val = content_val.strip('"')

                    content_val = content_val.replace('\\n', '\n').replace('\\"', '"')
                    action_dict["content"] = content_val

                extracted_actions.append(action_dict)

            if extracted_actions:
                logging.info(f"Successfully extracted actions for Planner agent using robust parsing: {extracted_actions}")
                # Apply strict filtering after robust extraction
                planner_approved_actions = []
                for action in extracted_actions:
                    if action.get("action") in ["create_file", "edit_file"] and action.get("path") == "project_plan.md":
                        planner_approved_actions.append(action)
                    else:
                        logging.warning(f"Planner agent attempted to generate disallowed action (robust extract): {action}")
                if not planner_approved_actions:
                    self.display_agent_message("The Planner agent's output was rejected (robust extract). It must ONLY generate actions for 'project_plan.md'. Please try again or refine the goal.", is_user=False, agent_name="Planner")
                return {"actions": planner_approved_actions}
            else:
                logging.warning("Robust action extraction failed to find any actions for Planner agent.")
                return None

    def _extract_planner_actions_strictly(self, text: str) -> dict | None:
        """Extracts a JSON object containing file actions from the Planner agent's response."""
        # Attempt to find the JSON block, with or without ```json ``` wrapper
        match = re.search(r"```json\s*({.*})\s*```", text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            # Fallback for raw JSON, stripping whitespace and non-printable characters
            json_str = text.strip()
            # Attempt to find the first '{' and last '}' to isolate the JSON object
            start_idx = json_str.find('{')
            end_idx = json_str.rfind('}')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = json_str[start_idx : end_idx + 1]
            else:
                logging.warning("Could not find a valid JSON object in the response for Planner agent.")
                return None

        # If initial parsing fails, try to manually parse action blocks
        try:
            # First, try parsing the cleaned json_str directly
            data = json.loads(json_str)
            if isinstance(data, dict) and "actions" in data:
                # This is the strict filtering for Planner agent, applied after successful JSON parse
                planner_approved_actions = []
                for action in data.get("actions", []):
                    if action.get("action") in ["create_file", "edit_file"] and action.get("path") == "project_plan.md":
                        planner_approved_actions.append(action)
                    else:
                        logging.warning(f"Planner agent attempted to generate disallowed action: {action}")
                data["actions"] = planner_approved_actions
                if not planner_approved_actions:
                    self.display_agent_message("The Planner agent's output was rejected. It must ONLY generate actions for 'project_plan.md'. Please try again or refine the goal.", is_user=False, agent_name="Planner")
                return data
        except json.JSONDecodeError:
            logging.info("Initial JSON parse failed for Planner agent, attempting robust action extraction.")
            # Regex to find individual action blocks, assuming they start with { and contain "action" and "path"
            action_pattern = re.compile(r'{\s*"action"\s*:\s*"(?P<action>[^"]*)",\s*"path"\s*:\s*"(?P<path>[^"]*)"(?:,\s*"content"\s*:\s*(?P<content_val>.*?))?}', re.DOTALL)

            extracted_actions = []
            for m in action_pattern.finditer(json_str):
                action_dict = {
                    "action": m.group("action"),
                    "path": m.group("path")
                }
                content_val = m.group("content_val")
                if content_val:
                    content_val = content_val.strip()
                    if content_val.startswith('"""') and content_val.endswith('"""'):
                        content_val = content_val.strip('"""')
                    elif content_val.startswith('"') and content_val.endswith('"'):
                        content_val = content_val.strip('"')

                    content_val = content_val.replace('\\n', '\n').replace('\\"', '"')
                    action_dict["content"] = content_val

                extracted_actions.append(action_dict)

            if extracted_actions:
                logging.info(f"Successfully extracted actions for Planner agent using robust parsing: {extracted_actions}")
                # Apply strict filtering after robust extraction
                planner_approved_actions = []
                for action in extracted_actions:
                    if action.get("action") in ["create_file", "edit_file"] and action.get("path") == "project_plan.md":
                        planner_approved_actions.append(action)
                    else:
                        logging.warning(f"Planner agent attempted to generate disallowed action (robust extract): {action}")
                if not planner_approved_actions:
                    self.display_agent_message("The Planner agent's output was rejected (robust extract). It must ONLY generate actions for 'project_plan.md'. Please try again or refine the goal.", is_user=False, agent_name="Planner")
                return {"actions": planner_approved_actions}
            else:
                logging.warning("Robust action extraction failed to find any actions for Planner agent.")
                return None

    def _extract_planner_actions_strictly(self, text: str) -> dict | None:
        """Extracts a JSON object containing file actions from the Planner agent's response."""
        # Attempt to find the JSON block, with or without ```json ``` wrapper
        match = re.search(r"```json\s*({.*})\s*```", text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            # Fallback for raw JSON, stripping whitespace and non-printable characters
            json_str = text.strip()
            # Attempt to find the first '{' and last '}' to isolate the JSON object
            start_idx = json_str.find('{')
            end_idx = json_str.rfind('}')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = json_str[start_idx : end_idx + 1]
            else:
                logging.warning("Could not find a valid JSON object in the response for Planner agent.")
                return None

        # If initial parsing fails, try to manually parse action blocks
        try:
            # First, try parsing the cleaned json_str directly
            data = json.loads(json_str)
            if isinstance(data, dict) and "actions" in data:
                # This is the strict filtering for Planner agent, applied after successful JSON parse
                planner_approved_actions = []
                for action in data.get("actions", []):
                    if action.get("action") in ["create_file", "edit_file"] and action.get("path") == "project_plan.md":
                        planner_approved_actions.append(action)
                    else:
                        logging.warning(f"Planner agent attempted to generate disallowed action: {action}")
                data["actions"] = planner_approved_actions
                if not planner_approved_actions:
                    self.display_agent_message("The Planner agent's output was rejected. It must ONLY generate actions for 'project_plan.md'. Please try again or refine the goal.", is_user=False, agent_name="Planner")
                return data
        except json.JSONDecodeError:
            logging.info("Initial JSON parse failed for Planner agent, attempting robust action extraction.")
            # Regex to find individual action blocks, assuming they start with { and contain "action" and "path"
            action_pattern = re.compile(r'{\s*"action"\s*:\s*"(?P<action>[^"]*)",\s*"path"\s*:\s*"(?P<path>[^"]*)"(?:,\s*"content"\s*:\s*(?P<content_val>.*?))?}', re.DOTALL)

            extracted_actions = []
            for m in action_pattern.finditer(json_str):
                action_dict = {
                    "action": m.group("action"),
                    "path": m.group("path")
                }
                content_val = m.group("content_val")
                if content_val:
                    content_val = content_val.strip()
                    if content_val.startswith('"""') and content_val.endswith('"""'):
                        content_val = content_val.strip('"""')
                    elif content_val.startswith('"') and content_val.endswith('"'):
                        content_val = content_val.strip('"')

                    content_val = content_val.replace('\\n', '\n').replace('\\"', '"')
                    action_dict["content"] = content_val

                extracted_actions.append(action_dict)

            if extracted_actions:
                logging.info(f"Successfully extracted actions for Planner agent using robust parsing: {extracted_actions}")
                # Apply strict filtering after robust extraction
                planner_approved_actions = []
                for action in extracted_actions:
                    if action.get("action") in ["create_file", "edit_file"] and action.get("path") == "project_plan.md":
                        planner_approved_actions.append(action)
                    else:
                        logging.warning(f"Planner agent attempted to generate disallowed action (robust extract): {action}")
                if not planner_approved_actions:
                    self.display_agent_message("The Planner agent's output was rejected (robust extract). It must ONLY generate actions for 'project_plan.md'. Please try again or refine the goal.", is_user=False, agent_name="Planner")
                return {"actions": planner_approved_actions}
            else:
                logging.warning("Robust action extraction failed to find any actions for Planner agent.")
                return None

    def _extract_manager_actions_strictly(self, text: str) -> dict | None:
        """Extracts a JSON object containing file actions from the Manager agent's response, strictly enforcing 'create_file' for 'plan.md'."""
        match = re.search(r"```json\s*({.*})\s*```", text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            json_str = text.strip()
            start_idx = json_str.find('{')
            end_idx = json_str.rfind('}')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = json_str[start_idx : end_idx + 1]
            else:
                logging.warning("Could not find a valid JSON object in the response for Manager agent.")
                return None

        try:
            data = json.loads(json_str)
            if isinstance(data, dict) and "actions" in data:
                manager_approved_actions = []
                for action in data.get("actions", []):
                    if action.get("action") == "create_file" and action.get("path") == "plan.md":
                        manager_approved_actions.append(action)
                    else:
                        logging.warning(f"Manager agent attempted to generate disallowed action: {action}")
                data["actions"] = manager_approved_actions
                if not manager_approved_actions:
                    self.display_agent_message("The Manager agent's output was rejected. It must ONLY generate 'create_file' actions for 'plan.md'. Please try again or refine the goal.", is_user=False, agent_name="Manager")
                return data
        except json.JSONDecodeError as e:
            logging.error(f"JSON decoding failed for Manager agent: {e}\nAttempted to decode: {json_str}")
            return None
        return None

    def _display_actions_for_review(self, data: dict):
        self.pending_actions = data.get("actions", [])

        if not self.pending_actions:
            return

        # Format a readable summary of the actions
        summary = "### Proposed File Changes\n\n"
        for action in self.pending_actions:
            op = action.get("action")
            path = action.get("path")
            if op == "create_file":
                summary += f"- **Create File:** `{path}`\n"
            elif op == "delete_file":
                summary += f"- **Delete File:** `{path}`\n"
            elif op == "create_directory":
                summary += f"- **Create Directory:** `{path}`\n"

        summary += "\nPlease review and click \"Apply Changes\" to proceed."
        self._update_ai_bubble_content(summary)
        self.apply_changes_button.show()

    def _apply_pending_changes(self):
        if not self.pending_actions or not self.project_root:
            return

        try:
            self.file_op_service.execute_actions(self.project_root, self.pending_actions)
            if self.project_root:
                plan_path = os.path.join(self.project_root, "plan.md")
                if os.path.exists(plan_path):
                    with open(plan_path, "r", encoding="utf-8") as f:
                        plan_content = f.read()
                    self.plan_updated.emit(plan_content)
                else:
                    self.plan_updated.emit("") # Emit empty string if plan.md doesn't exist
            logging.info("File operations executed successfully.")
        except Exception as e:
            logging.error(f"Error applying changes: {e}")

        self.pending_actions = None
        self.apply_changes_button.hide()
        # Optionally, add a confirmation message to the chat
        self._add_message("assistant", "Changes applied successfully.")
        self._display_conversation()

    def _handle_manager_response(self, response_text):
        # This is now handled by the generic _display_actions_for_review
        self.plan_updated.emit()

    def _update_ai_bubble_content(self, content):
        if self.ai_bubble:
            self.ai_bubble.set_text(content)

    def _execute_tool(self, tool_request: dict):
        """Executes a tool request from an agent."""
        tool_name = tool_request.get("tool")
        path = tool_request.get("path")

        if tool_name == "read_file" and path:
            logging.info(f"Agent requested to read file: {path}")
            try:
                content = self.file_op_service.read_file(self.project_root, path)
                feedback_message = f'I have read the file `{path}`. The content is:\n\n```\n{content}\n```'
                self._add_message("user", feedback_message)  # Feed content back as user message
                self.send_message(self.current_ai_response, is_resend=True) # Resend original context
            except FileNotFoundError:
                error_message = f"Error: The file `{path}` was not found."
                self._add_message("user", error_message)
                self.send_message(self.current_ai_response, is_resend=True)
        elif tool_name == "run_command" and self.terminal_widget:
            logging.info(f"Agent requested to run command: {path}")
            self.terminal_widget.run_command(path)
        else:
            logging.warning(f"Unknown or invalid tool request: {tool_request}")

    def _parse_tool_request(self, text: str) -> dict | None:
        """Checks if the response is a JSON tool request."""
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "tool" in data and "path" in data:
                return data
        except json.JSONDecodeError:
            return None
        return None

    def _display_conversation(self):
        # This method is not implemented in the provided code
        pass

    def display_agent_message(self, message, is_user, agent_name):
        self._add_message("assistant", f"{agent_name}: {message}")

    def _on_run_planner_button_clicked(self):
        logging.info("LLMChatWidget: _on_run_planner_button_clicked method called.")
        self.current_agent_key = "planner"
        logging.info(f"LLMChatWidget: Switched to Planner agent.")

        # Read the content of plan.md to provide context to the Planner agent
        plan_content = ""
        if self.project_root:
            plan_path = os.path.join(self.project_root, "plan.md")
            if os.path.exists(plan_path):
                with open(plan_path, "r", encoding="utf-8") as f:
                    plan_content = f.read()
                self.conversation_history.append({"role": "system", "content": f"The following is the overall plan:\n\n{plan_content}"})
                logging.info(f"LLMChatWidget: Loaded plan content from {plan_path}.")
            else:
                logging.info(f"LLMChatWidget: No plan.md found. Using default prompt.")
        else:
            logging.info(f"LLMChatWidget: No project root set. Using default prompt.")

        # Simulate sending a message to trigger the LLM for the Planner agent
        self.set_status_indicator(True)
        self.current_ai_response = ""
        self.add_message_to_view(f"Triggering Planner with prompt: Based on the overall plan, create a detailed project plan.", is_user=True)
        self.conversation_history.append({"role": "user", "content": "Based on the overall plan, create a detailed project plan."})

        self.ai_bubble = self.add_message_to_view("", is_user=False)

        # Prepare messages for the worker, including the agent's system prompt
        system_prompt = self.agents[self.current_agent_key]["system_prompt"]
        messages_for_worker = [{"role": "system", "content": system_prompt}] + self.conversation_history

        logging.debug(f"Messages sent to LLM: {messages_for_worker}")

        # Setup and start the worker thread
        self.thread = QThread()
        self.worker = ChatWorker(self.llm_manager, messages_for_worker)
        self.worker.moveToThread(self.thread)

        self.worker.response_updated.connect(self._handle_response_chunk)
        self.worker.error_occurred.connect(self.on_worker_error)
        self.worker.finished.connect(self._on_worker_finished)

        self.thread.started.connect(self.worker.run)
        self.thread.start()
        logging.info("LLMChatWidget: Started worker thread for Planner agent.")

    def _on_generate_plan_requested(self, prompt: str):
        logging.info("LLMChatWidget: _on_generate_plan_requested method called.")
        self.current_agent_key = "manager"
        logging.info(f"LLMChatWidget: Switched to Manager agent.")

        self.set_status_indicator(True)
        self.current_ai_response = ""
        self.add_message_to_view(f"Triggering Manager with prompt: {prompt}", is_user=True)
        
        # Temporarily clear conversation history to ensure Manager agent only sees its system prompt and current task
        # This is a diagnostic step to confirm if previous conversation context is influencing the LLM.
        original_conversation_history = self.conversation_history
        self.conversation_history = []

        self.conversation_history.append({"role": "user", "content": prompt})
        self.ai_bubble = self.add_message_to_view("", is_user=False)

        system_prompt = self.agents[self.current_agent_key]["system_prompt"]
        messages_for_worker = [{"role": "system", "content": system_prompt}] + self.conversation_history

        logging.debug(f"Messages sent to LLM: {messages_for_worker}")

        self.thread = QThread()
        self.worker = ChatWorker(self.llm_manager, messages_for_worker)
        self.worker.moveToThread(self.thread)

        self.worker.response_updated.connect(self._handle_response_chunk)
        self.worker.error_occurred.connect(self.on_worker_error)
        self.worker.finished.connect(self._on_worker_finished)

        self.thread.started.connect(self.worker.run)
        self.thread.start()
        logging.info("LLMChatWidget: Started worker thread for Manager agent.")
