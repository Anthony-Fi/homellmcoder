from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QTextEdit


class ChatInputBox(QTextEdit):
    """A custom QTextEdit that sends a message on Enter.

    It adds a newline on Ctrl+Enter.
    """

    send_message = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(40)
        self.setMaximumHeight(120)
        self.setPlaceholderText(
            "Ask the AI here. Press Enter to send, Ctrl+Enter for a new line."
        )

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.insertPlainText("\n")
            else:
                self.send_message.emit()
        else:
            super().keyPressEvent(event)
