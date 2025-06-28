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

    def __init__(
        self,
        llm_manager,
        history_service: HistoryService = None,
        file_operation_service: FileOperationService = None,
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

        # Service Dependencies
        self.history_service = history_service or HistoryService()
        self.file_operation_service = file_operation_service or FileOperationService()

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
        self.thread.quit()
        self.worker.deleteLater()
        self.thread.deleteLater()
        self.set_status_indicator(False)
        self.save_chat_history()

        # If the manager was the active agent, create the plan.md file
        if self.current_agent_key == "manager":
            plan_content = self.current_ai_response
            if self.project_root:
                try:
                    actions = [
                        {
                            "action": "create_file",
                            "path": "plan.md",
                            "content": plan_content,
                        }
                    ]
                    self.file_operation_service.execute_actions(self.project_root, actions)
                    plan_path = os.path.join(self.project_root, "plan.md")
                    self._add_message(
                        "system", f"Master plan created at {plan_path}. You can now switch to the Planner agent to detail the steps."
                    )

                except Exception as e:
                    logging.error(f"Error creating plan.md: {e}")
                    self._add_message("system", f"Error creating plan.md: {e}")
            else:
                self._add_message("system", "Error: No project root is set. Cannot create plan.md.")

        self.current_ai_response = ""

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
            self.file_operation_service.execute_actions(self.project_root, actions)
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

        self.input_box = ChatInputBox()
        self.input_box.send_message.connect(self.send_message)
        self.input_box.setFont(QFont("Segoe UI", 10))

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.status_indicator)
        input_layout.addWidget(self.input_box, 1)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_button)

        layout.addWidget(self.conversation_view)
        layout.addLayout(input_layout)

    def _on_agent_changed(self, index):
        self.current_agent_key = self.agent_combo_box.itemData(index)
        logging.info(f"Switched to {self.agents[self.current_agent_key]['name']}")

    def _scroll_to_bottom(self):
        """Scrolls the conversation view to the bottom."""
        scroll_bar = self.conversation_view.verticalScrollBar()
        QTimer.singleShot(100, lambda: scroll_bar.setValue(scroll_bar.maximum()))

    def save_chat_history(self):
        if self.project_root:
            self.history_service.save_history(
                self.project_root, self.conversation_history
            )

    def _add_message(self, role, content):
        self.conversation_history.append({"role": role, "content": content})
        self.add_message_to_view(content, role == "assistant")
