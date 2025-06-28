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

        # Service Dependencies
        self.history_service = history_service or HistoryService()

        self.thread = None
        self.worker = None

        self._init_ui()

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

    def _on_worker_finished(self):
        """Handles cleanup and delegation after the worker thread is done."""
        response_text = self.current_ai_response

        # Check for tool use
        tool_request = self._parse_tool_request(response_text)
        if tool_request:
            self._execute_tool(tool_request)
            return  # The tool execution will trigger the next step

        # Check for any agent response containing file actions
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
                planner_approved_actions = []
                # Only allow create_file for project_plan.md
                for action in actions_data.get("actions", []):
                    if action.get("action") == "create_file" and action.get("path") == "project_plan.md":
                        planner_approved_actions.append(action)
                actions_data["actions"] = planner_approved_actions
            # Allow run_command for Coder agent
            elif self.current_agent_key == "coder":
                coder_approved_actions = []
                for action in actions_data.get("actions", []):
                    if action.get("action") == "run_command":
                        coder_approved_actions.append(action)
                actions_data["actions"] = coder_approved_actions

            if actions_data.get("actions"): # Only display if there are valid actions after filtering
                self._display_actions_for_review(actions_data)
                self.thread.quit()
                self.worker.deleteLater()
                self.thread.deleteLater()
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
        self.worker.deleteLater()
        self.thread.deleteLater()
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

        layout.addLayout(input_layout)

        self.apply_changes_button = QPushButton("Apply Changes")
        self.apply_changes_button.clicked.connect(self._apply_pending_changes)
        self.apply_changes_button.hide()
        layout.addWidget(self.apply_changes_button)

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
        # Pattern to find ```json ... ```, being more greedy to capture the full JSON block
        match = re.search(r"```json\s*({.*})\s*```", text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            # Fallback for raw JSON, stripping whitespace and non-printable characters
            json_str = text.strip()
            # Remove any trailing non-JSON characters (like '█') and leading/trailing non-JSON text
            json_str = re.sub(r'^[^{]*|[^}]*$', '', json_str) # Remove anything before first { and after last }
            json_str = re.sub(r'[\x00-\x1F\x7F-\x9F\s]*$', '', json_str) # Remove control characters and trailing whitespace
            if not json_str.startswith('{') or not json_str.endswith('}'):
                return None

        try:
            data = json.loads(json_str)
            if isinstance(data, dict) and "actions" in data:
                return data
        except json.JSONDecodeError:
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
