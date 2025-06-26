from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QLabel, QScrollArea, QFrame, QMessageBox
from PyQt6.QtCore import pyqtSignal, QObject, QThread, Qt, QTimer
from PyQt6.QtGui import QColor, QPalette, QKeyEvent, QFont
import re
import os
import json

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
        def stream_callback(response):
            status = response.get("status")
            if status == "chunk":
                self.chunk_received.emit(response.get("content", ""))
            elif status == "done":
                self.finished.emit()
            elif status == "error":
                self.error.emit(response.get("message", "Unknown error"))

        self.llm_manager.chat_stream(self.prompt, stream_callback)

class ChatBubble(QWidget):
    """A chat bubble for displaying a single message."""
    change_requested = pyqtSignal(dict)

    def __init__(self, text, is_user, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 5, 10, 5)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setPlainText(text)
        self.text_edit.setFrameStyle(QFrame.Shape.NoFrame)

        # Styling based on who sent the message
        palette = self.text_edit.palette()
        if is_user:
            self.layout.setAlignment(Qt.AlignmentFlag.AlignRight)
            palette.setColor(QPalette.ColorRole.Base, QColor("#DCF8C6"))
        else:
            self.layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
            palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
        self.text_edit.setPalette(palette)
        self.text_edit.setAutoFillBackground(True)

        self.layout.addWidget(self.text_edit)

        # Add 'Apply Change' button for AI messages
        if not is_user:
            self.apply_button = QPushButton("Apply Change")
            self.apply_button.setFixedWidth(100)
            self.apply_button.setVisible(False) # Hidden by default
            self.layout.addWidget(self.apply_button)

    def append_text(self, text_chunk):
        """Appends a chunk of text to the chat bubble, used for streaming."""
        current_text = self.text_edit.toPlainText()
        self.text_edit.setPlainText(current_text + text_chunk)
        self.set_text(self.text_edit.toPlainText())

    def set_text(self, text):
        """Sets the text of the bubble and checks for file action JSON."""
        self.text_edit.setPlainText(text)

        # Use regex to find a JSON block for file operations
        match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
        if match:
            try:
                action_json_str = match.group(1)
                action_data = json.loads(action_json_str)
                
                # Basic validation of the action format
                if 'type' in action_data and 'file_path' in action_data:
                    self.apply_button.setVisible(True)
                    # Ensure we don't have duplicate connections
                    try:
                        self.apply_button.clicked.disconnect()
                    except TypeError: # Raised if no connections exist
                        pass
                    self.apply_button.clicked.connect(lambda: self.change_requested.emit(action_data))

            except (json.JSONDecodeError, KeyError):
                self.apply_button.setVisible(False)
        else:
            self.apply_button.setVisible(False)

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

class LLMChatWidget(QWidget):
    """A widget for interacting with the loaded LLM."""
    change_requested = pyqtSignal(dict)

    # System prompt to guide the AI to produce structured file modification commands
    SYSTEM_PROMPT = ("""
        You are an expert AI pair programmer. Your primary function is to help the user by directly modifying the filesystem.
        
        **CRITICAL INSTRUCTION:** When the user asks you to create, overwrite, or delete a file, you MUST NOT write Python code to do it. Instead, you MUST respond with a single JSON object inside a 'json' markdown block. This is the only way you can interact with files.
        
        The JSON object MUST have the following structure:
        - "type": A string, MUST be one of "CREATE_FILE", "OVERWRITE_FILE", or "DELETE_FILE".
        - "file_path": A string representing the relative path to the file (e.g., "src/new_feature.py").
        - "content": A string containing the full content for the file. This key is REQUIRED for "CREATE_FILE" and "OVERWRITE_FILE". It MUST be omitted for "DELETE_FILE".

        --- 
        **EXAMPLE 1: User asks 'Create a file named app.py with a print statement.'**

        Your response MUST be:
        ```json
        {
          "type": "CREATE_FILE",
          "file_path": "app.py",
          "content": "print('Hello from app.py!')"
        }
        ```

        --- 
        **EXAMPLE 2: User asks 'Delete the file named old_styles.css.'**

        Your response MUST be:
        ```json
        {
          "type": "DELETE_FILE",
          "file_path": "old_styles.css"
        }
        ```
        --- 

        For any other conversation, code explanation, or questions that do not involve file manipulation, you can respond normally as a helpful AI assistant.
    """)

    def __init__(self, llm_manager=None, parent=None):
        super().__init__(parent)
        self.llm_manager = llm_manager
        self.ai_bubble = None
        self.current_ai_response = ""
        self._init_ui()

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

        layout.addWidget(self.conversation_view)
        layout.addWidget(self.input_box)

    def send_message(self):
        """Sends the user's message to the LLM."""
        prompt = self.input_box.toPlainText().strip()
        if not prompt:
            return

        if not self.llm_manager:
            self.conversation_view_layout.addWidget(ChatBubble("<i style='color:red;'>Error: No model is loaded. Please select and load a model first.</i>", True))
            return

        self.conversation_view_layout.addWidget(ChatBubble(f"<b style='color:#00008B;'>You:</b> {prompt}", True))
        self.input_box.clear()
        self.input_box.setEnabled(False)
        self.ai_bubble = ChatBubble("", False, self)
        self.ai_bubble.change_requested.connect(self.change_requested)
        self.conversation_view_layout.addWidget(self.ai_bubble)
        self.current_ai_response = "<b style='color:#006400;'>Assistant:</b> "

        # Run chat in a separate thread to keep UI responsive
        self.thread = QThread()
        self.worker = ChatWorker(self.llm_manager, LLMChatWidget.SYSTEM_PROMPT + "\n" + prompt)
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
        """Re-enables input and cleans up the thread when chat is done."""
        self.input_box.setEnabled(True)
        self.input_box.setFocus()
        self.thread.quit()

    def on_chat_error(self, error_message):
        """Displays an error and re-enables the input box."""
        self.conversation_view_layout.addWidget(ChatBubble(f"<i style='color:red;'>Error: {error_message}</i>", False))
        self.on_chat_finished() # Re-enable input and clean up
