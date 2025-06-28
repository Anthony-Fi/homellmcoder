import logging
from PyQt6.QtCore import QObject, pyqtSignal


class ChatWorker(QObject):
    """A worker that runs the chat stream in a separate thread."""

    response_updated = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, llm_manager, conversation_history: list):
        super().__init__()
        self.llm_manager = llm_manager
        self.conversation_history = conversation_history

    def run(self):
        """Executes the chat stream and emits signals with the results."""
        try:
            logging.info(
                (
                    "ChatWorker: Starting chat stream with %s history items.",
                    len(self.conversation_history),
                )
            )
            stream = self.llm_manager.get_response(self.conversation_history)
            for chunk in stream:
                content = chunk.get("message", {}).get("content", "")
                if content:
                    self.response_updated.emit(content)
        except Exception as e:
            logging.error(f"Error in ChatWorker: {e}", exc_info=True)
            self.error_occurred.emit(f"An error occurred in the AI worker thread: {e}")
        finally:
            self.finished.emit()
