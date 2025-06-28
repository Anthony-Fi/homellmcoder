from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import pyqtSignal, Qt
import json
import re


class ChatBubble(QWidget):
    """A chat bubble for displaying a single message.

    It has support for action buttons.
    """

    change_requested = pyqtSignal(dict)

    def __init__(self, text, is_user, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self.actions_payload = None

        # --- Layout and Core Widgets --- #
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 5, 10, 5)
        self.layout.setSpacing(5)

        self.text_label = QLabel()
        self.text_label.setWordWrap(True)
        self.text_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.text_label.setOpenExternalLinks(True)

        self.button_container = QWidget()
        self.button_layout = QVBoxLayout(self.button_container)
        self.button_layout.setContentsMargins(0, 5, 0, 0)
        self.button_layout.setSpacing(5)

        self.layout.addWidget(self.text_label)
        self.layout.addWidget(self.button_container)

        # --- Styling --- #
        if self.is_user:
            self.setStyleSheet("background-color: #DCF8C6; border-radius: 10px;")
        else:
            self.setStyleSheet(
                """
                background-color: #F1F0F0;
                border: 1px solid #D1D1D1;
                border-radius: 10px;
            """
            )

        self.set_text(text)

    def set_text(self, text, is_final=False):
        """Sets the display text of the chat bubble.

        If the text is final, it parses for an action block and adds a button.
        """
        display_text = text
        if is_final and not self.is_user:
            # Use regex to find the JSON block, allowing for variations
            match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
            if match:
                json_str = match.group(1)
                try:
                    payload = json.loads(json_str)
                    actions = payload.get("actions")
                    if actions:
                        # Hide the raw JSON from the user's view
                        display_text = text.replace(match.group(0), "").strip()
                        self.add_change_button(
                            "Apply Change",
                            actions
                        )
                except json.JSONDecodeError as e:
                    # If JSON is malformed, just display the raw text for now.
                    print(f"Failed to parse JSON: {e}")  # For debugging
                    pass

        self.text_label.setText(display_text.replace("\n", "<br>"))

    def add_change_button(self, text, actions_payload):
        """Adds a button to the bubble for an AI-suggested action."""
        button = QPushButton(text)
        button.setStyleSheet(
            """
            QPushButton {
                background-color: #007BFF;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """
        )
        button.clicked.connect(
            lambda: self.change_requested.emit({"actions": actions_payload})
        )
        self.button_layout.addWidget(button)

    def get_data(self):
        """Returns the bubble's data for serialization."""
        return {"is_user": self.is_user, "text": self.text_label.text()}
