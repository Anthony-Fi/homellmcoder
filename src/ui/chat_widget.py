from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QLabel, QScrollArea, QFrame, QMessageBox
from PyQt6.QtCore import pyqtSignal, QObject, QThread, Qt, QTimer, QSize
from PyQt6.QtGui import QColor, QPalette, QKeyEvent, QFont, QPainter, QBrush
import re
import os
import json
import logging
import traceback

class ChatWorker(QObject):
    """A worker that runs the chat stream in a separate thread."""
    chunk_received = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, llm_manager, prompt):
        super().__init__()
        self.llm_manager = llm_manager
        self.prompt = prompt

    def run(self):
        """Executes the chat stream and emits signals with the results."""
        try:
            # get_response is a generator, so we iterate over it
            for chunk in self.llm_manager.get_response(self.prompt):
                self.chunk_received.emit(chunk)
            self.finished.emit()
        except Exception as e:
            # Log the full error for debugging
            logging.error(f"Error in ChatWorker: {e}\n{traceback.format_exc()}")
            self.error.emit(str(e))

class ChatBubble(QWidget):
    """A chat bubble for displaying a single message."""
    change_requested = pyqtSignal(dict)

    def __init__(self, text, is_user, parent=None):
        super().__init__(parent)
        self.is_user = is_user

        # --- Layout and Core Widget --- #
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 5, 10, 5)
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFrameStyle(QFrame.Shape.NoFrame)
        self.text_edit.setStyleSheet("background:transparent; border: none;")
        self.layout.addWidget(self.text_edit)

        # --- Styling and Button Logic --- #
        if self.is_user:
            # User messages are simple: apply style and set text.
            self.setStyleSheet("background-color: #DCF8C6; border-radius: 10px;")
        else:
            # AI messages get the 'Apply Change' button.
            self.setStyleSheet("background-color: #FFFFFF; border-radius: 10px;")
            self.apply_button = QPushButton("Apply Change")
            self.apply_button.setFixedWidth(100)
            self.apply_button.setVisible(False) # Hidden until a JSON block is detected
            self.layout.addWidget(self.apply_button)

        self.set_text(text)

    def set_text(self, text):
        """Sets the text of the chat bubble and updates button visibility for AI messages."""
        self.text_edit.setMarkdown(text)

        # The 'Apply Change' button logic only runs for AI messages.
        if not self.is_user:
            self.update_apply_button_visibility(text)

    def append_text(self, text_chunk):
        """Appends a chunk of text to the chat bubble, used for streaming AI responses."""
        current_text = self.text_edit.toPlainText() + text_chunk
        self.set_text(current_text)

    def update_apply_button_visibility(self, text):
        """Shows or hides the 'Apply Change' button based on the presence of valid JSON."""
        # This method should only be called for AI bubbles, so self.apply_button exists.
        json_block_found = '```json' in text
        
        if json_block_found:
            try:
                json_str = text.split('```json')[1].split('```')[0]
                data = json.loads(json_str)

                # Check if the JSON structure is a valid, actionable request
                if 'actions' in data and isinstance(data['actions'], list):
                    self.apply_button.setVisible(True)
                    # Re-connect signal to ensure it has the latest data
                    try:
                        self.apply_button.clicked.disconnect()
                    except TypeError:
                        pass # No connection existed
                    self.apply_button.clicked.connect(lambda: self.change_requested.emit(data))
                    return # Exit after successful setup

            except (json.JSONDecodeError, IndexError):
                # Malformed JSON or text structure, hide the button.
                pass

        # Default to hidden if no valid JSON is found.
        self.apply_button.setVisible(False)

    def get_data(self):
        """Returns the bubble's data for serialization."""
        return {"is_user": self.is_user, "text": self.text_edit.toPlainText()}

class ChatInputBox(QTextEdit):
    """A custom QTextEdit that sends a message on Enter and adds a newline on Ctrl+Enter."""
    send_message = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(40) # Set a larger minimum height
        self.setMaximumHeight(120) # And a maximum height to control resizing
        self.setPlaceholderText("Ask the AI here. Press Enter to send, Ctrl+Enter for a new line.")

    def keyPressEvent(self, event: QKeyEvent):
        # Send message on Enter, but allow newlines with Ctrl+Enter
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                # Ctrl+Enter -> Insert newline
                self.insertPlainText('\n')
            else:
                # Enter -> Send message
                self.send_message.emit()
        else:
            super().keyPressEvent(event) # Default behavior for all other keys

class AIStatusIndicator(QWidget):
    """A widget that displays a colored circle to indicate AI status."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_busy = False
        self.setFixedSize(16, 16) # Small, fixed size circle

    def set_busy(self, busy):
        """Sets the busy status and triggers a repaint."""
        if self._is_busy != busy:
            self._is_busy = busy
            self.update() # Schedule a repaint

    def paintEvent(self, event):
        """Paints the circle with the appropriate color."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        color = QColor("green") if self._is_busy else QColor("red")
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Draw a circle in the center of the widget
        rect = self.rect()
        painter.drawEllipse(rect)

    def sizeHint(self):
        return QSize(16, 16)

class LLMChatWidget(QWidget):
    """A widget for interacting with the loaded LLM."""
    change_requested = pyqtSignal(dict)

    # System prompt to guide the AI to produce structured file modification commands
    SYSTEM_PROMPT = ("""You are a file-operation AI. You ONLY respond with JSON.

**CRITICAL RULE: For a new project, your FIRST and ONLY response MUST be JSON to create `plan.md`.**

Example `plan.md` creation:
```json
{
  "actions": [
    {
      "action": "create_file",
      "path": "plan.md",
      "content": "# Project Plan\\n\\n- [ ] Step 1: Set up an industry-standard project structure (e.g., src, tests, docs).\\n- [ ] Step 2: Implement core feature A.\\n- [ ] Step 3: Write tests for core feature A."
    }
  ]
}
```

**ALL RESPONSES MUST BE JSON WRAPPED IN ```json ... ```**

If you need to talk, another AI will handle it. Your only job is to generate file operations as JSON.

**VALID ACTIONS:** `create_file`, `edit_file`, `delete_file`, `create_directory`.
""")

    def __init__(self, llm_manager=None, parent=None):
        super().__init__(parent)
        self.llm_manager = llm_manager
        self.ai_bubble = None
        self.current_ai_response = ""
        self.status_indicator = AIStatusIndicator()
        self.history_path = self._get_history_path()
        self.plan_exists = False
        self._init_ui()
        self.load_history()

    def set_llm_manager(self, llm_manager):
        self.llm_manager = llm_manager

    def _init_ui(self):
        """Initializes the UI components of the widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        self.conversation_view = QScrollArea()
        self.conversation_view.setWidgetResizable(True)
        self.conversation_view_widget = QWidget()
        self.conversation_view.setWidget(self.conversation_view_widget)
        self.conversation_view_layout = QVBoxLayout(self.conversation_view_widget)
        self.conversation_view_layout.setContentsMargins(10, 10, 10, 10)

        self.input_box = ChatInputBox() # Use the new custom widget
        self.input_box.send_message.connect(self.send_message)
        self.input_box.setFont(QFont("Segoe UI", 10))

        # Create a layout for the input area
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.status_indicator)
        input_layout.addWidget(self.input_box, 1) # Give the input box stretch factor

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_button)

        layout.addWidget(self.conversation_view)
        layout.addLayout(input_layout)

    def on_plan_created(self):
        """Slot to be called when plan.md is successfully created."""
        self.plan_exists = True
        logging.info("plan.md has been created. Switching to plan execution mode.")

    def send_message(self):
        """Sends the user's message to the LLM."""
        prompt = self.input_box.toPlainText().strip()
        if not prompt:
            return

        if not self.llm_manager:
            self.conversation_view_layout.addWidget(ChatBubble("<i style='color:red;'>Error: No model is loaded. Please select and load a model first.</i>", True))
            return

        self.add_message_to_view(prompt, is_user=True)
        self.input_box.clear()
        self.input_box.setEnabled(False)
        self.status_indicator.set_busy(True) # Set status to busy
        self.ai_bubble = self.add_message_to_view("", is_user=False)
        self.ai_bubble.change_requested.connect(self.change_requested)
        self.current_ai_response = ""

        prompt_to_send = prompt
        if not self.plan_exists:
            prompt_to_send = f"CRITICAL: Your first and only task is to create a detailed `plan.md` file for the following user request. Do not generate any other code. USER REQUEST: '{prompt}'"
            logging.info("Plan does not exist. Intercepting prompt to force plan creation.")

        # Run chat in a separate thread to keep UI responsive
        self.thread = QThread()
        self.worker = ChatWorker(self.llm_manager, LLMChatWidget.SYSTEM_PROMPT + "\n" + prompt_to_send)
        self.worker.moveToThread(self.thread)

        self.worker.chunk_received.connect(self.append_chunk)
        self.worker.finished.connect(self.on_chat_finished)
        self.worker.error.connect(self.on_chat_error)

        self.thread.started.connect(self.worker.run)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def append_chunk(self, chunk):
        """Appends a chunk of text from the AI to the conversation view."""
        self.current_ai_response += chunk
        self.ai_bubble.set_text(self.current_ai_response)
        self.conversation_view.verticalScrollBar().setValue(self.conversation_view.verticalScrollBar().maximum())

    def on_chat_finished(self):
        """Cleans up after the chat stream is finished."""
        self.input_box.setEnabled(True)
        self.input_box.setFocus()
        self.status_indicator.set_busy(False) # Set status to idle
        self.thread.quit()
        self.worker.deleteLater()
        self.thread.deleteLater()
        self.save_history() # Save history after each successful interaction

        # After the full response is received, parse for file operations.
        # First, try to find a markdown-wrapped JSON block.
        json_str = None
        json_match = re.search(r"```json\n(.*?)\n```", self.current_ai_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Fallback: try to find raw JSON if no markdown block is found.
            start_index = self.current_ai_response.find('{')
            end_index = self.current_ai_response.rfind('}')
            if start_index != -1 and end_index != -1 and start_index < end_index:
                json_str = self.current_ai_response[start_index:end_index+1]
                logging.warning("Found raw JSON without markdown wrapper. The AI may not be following instructions perfectly.")

        if json_str:
            try:
                data = json.loads(json_str)
                actions = data.get("actions", [])
                if actions:
                    self.change_requested.emit({"actions": actions})
            except json.JSONDecodeError as e:
                logging.error(f"Failed to decode JSON from AI response: {e}")
                logging.error(f"Invalid JSON content: {json_str}")

    def on_chat_error(self, error_message):
        """Handles errors from the chat worker."""
        self.conversation_view_layout.addWidget(ChatBubble(f"<i style='color:red;'>Error: {error_message}</i>", False))
        self.on_chat_finished() # Re-enable input and clean up
        self.save_history() # Also save on error to not lose context

    def add_message_to_view(self, text, is_user):
        """Adds a new chat bubble to the conversation view."""
        bubble = ChatBubble(text, is_user, self)
        bubble.change_requested.connect(self.change_requested.emit)
        self.conversation_view_layout.addWidget(bubble)
        QTimer.singleShot(10, self._scroll_to_bottom) # Scroll after the UI updates
        return bubble

    def load_history(self):
        """Loads chat history from a file."""
        if not os.path.exists(self.history_path):
            return
        try:
            with open(self.history_path, 'r', encoding='utf-8') as f:
                history = json.load(f)
            for message in history:
                self.add_message_to_view(message['text'], message['is_user'])
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Failed to load chat history: {e}")

    def save_history(self):
        """Saves the current chat history to a file."""
        history = []
        for i in range(self.conversation_view_layout.count()):
            widget = self.conversation_view_layout.itemAt(i).widget()
            if isinstance(widget, ChatBubble):
                history.append(widget.get_data())

        try:
            os.makedirs(os.path.dirname(self.history_path), exist_ok=True)
            with open(self.history_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2)
        except IOError as e:
            logging.error(f"Failed to save chat history: {e}")

    def clear_history(self):
        """Clears the chat history and removes all bubbles from the UI."""
        self.conversation_view_widget = QWidget()
        self.conversation_view_layout = QVBoxLayout(self.conversation_view_widget)
        self.conversation_view_layout.addStretch()
        self.conversation_view.setWidget(self.conversation_view_widget)
        self.plan_exists = False
        logging.info("Chat history cleared and workflow state reset to AWAITING_PLAN.")

    def _get_history_path(self):
        """Returns the path to the chat history file."""
        config_dir = os.path.join(os.path.expanduser("~"), ".homellmcoder")
        return os.path.join(config_dir, "chat_history.json")

    def _scroll_to_bottom(self):
        """Scrolls the conversation view to the bottom."""
        scroll_bar = self.conversation_view.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())
