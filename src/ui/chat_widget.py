from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit
from PyQt6.QtCore import pyqtSignal, QObject, QThread, Qt
from PyQt6.QtGui import QFont

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

class LLMChatWidget(QWidget):
    """A widget for interacting with the loaded LLM."""
    def __init__(self, llm_manager, parent=None):
        super().__init__(parent)
        self.llm_manager = llm_manager
        self._init_ui()

    def _init_ui(self):
        """Initializes the UI components of the widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        self.conversation_view = QTextEdit()
        self.conversation_view.setReadOnly(True)
        self.conversation_view.setFont(QFont("Segoe UI", 10))
        self.conversation_view.setStyleSheet("background-color: #f0f0f0;")

        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("Type your message to the AI here and press Enter...")
        self.input_box.returnPressed.connect(self.send_message)
        self.input_box.setFont(QFont("Segoe UI", 10))

        layout.addWidget(self.conversation_view)
        layout.addWidget(self.input_box)

    def send_message(self):
        """Sends the user's message to the LLM."""
        prompt = self.input_box.text().strip()
        if not prompt:
            return

        if not self.llm_manager.get_loaded_model():
            self.conversation_view.append("<i style='color:red;'>Error: No model is loaded. Please select and load a model first.</i>")
            return

        self.conversation_view.append(f"<b style='color:#00008B;'>You:</b> {prompt}")
        self.input_box.clear()
        self.input_box.setEnabled(False)
        self.conversation_view.append(f"<b style='color:#006400;'>Assistant:</b> ")

        # Run chat in a separate thread to keep UI responsive
        self.thread = QThread()
        self.worker = ChatWorker(self.llm_manager, prompt)
        self.worker.moveToThread(self.thread)

        self.worker.chunk_received.connect(self.append_chunk)
        self.worker.finished.connect(self.on_chat_finished)
        self.worker.error.connect(self.on_chat_error)

        self.thread.started.connect(self.worker.run)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def append_chunk(self, chunk):
        """Appends a chunk of text to the conversation view."""
        self.conversation_view.insertPlainText(chunk)
        self.conversation_view.ensureCursorVisible()

    def on_chat_finished(self):
        """Re-enables input and cleans up the thread when chat is done."""
        self.input_box.setEnabled(True)
        self.input_box.setFocus()
        self.thread.quit()

    def on_chat_error(self, error_message):
        """Displays an error and re-enables the input box."""
        self.conversation_view.append(f"<i style='color:red;'>Error: {error_message}</i>")
        self.on_chat_finished() # Re-enable input and clean up
