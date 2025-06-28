from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont


class PlanWidget(QWidget):
    """A widget to display and interact with the project plan."""

    generate_plan_requested = pyqtSignal(str)
    run_planner_requested = pyqtSignal()
    run_coder_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.plan_view = QTextEdit()
        self.plan_view.setReadOnly(True)
        self.plan_view.setFont(QFont("Consolas", 10))
        layout.addWidget(self.plan_view)

        self.run_planner_button = QPushButton("Run Planner")
        self.run_planner_button.clicked.connect(self.run_planner_requested.emit)
        layout.addWidget(self.run_planner_button)

        self.run_coder_button = QPushButton("Run Coder")
        self.run_coder_button.clicked.connect(self.run_coder_requested.emit)
        layout.addWidget(self.run_coder_button)

        # We can add a button to generate a plan later
        # self.generate_button = QPushButton("Generate Plan from Concept")
        # self.generate_button.clicked.connect(self._on_generate_clicked)
        # layout.addWidget(self.generate_button)

    def set_plan_content(self, markdown_text: str):
        """Sets the plan content from markdown text."""
        self.plan_view.setMarkdown(markdown_text)

    def get_plan_text(self) -> str:
        """Returns the current text from the plan view."""
        return self.plan_view.toPlainText()
