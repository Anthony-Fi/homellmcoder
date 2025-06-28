import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from PyQt6.QtCore import QProcess, Qt, QDir
from PyQt6.QtGui import QFont, QColor, QTextCursor, QKeyEvent


class TerminalWidget(QWidget):
    """
    A widget that embeds a command-line terminal.
    NOTE: This is a basic implementation. Advanced features like command history
    (up/down arrows) and complex cursor movement are not yet supported.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = None
        self.project_root = None
        self._init_ui()
        self._init_process()
        self.input_start_position = 0

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.terminal = QTextEdit()
        self.terminal.setFont(QFont("Consolas", 10))
        self.terminal.setStyleSheet("background-color: black; color: white;")
        self.terminal.keyPressEvent = (
            self.terminal_key_press_event
        )  # Override key press
        layout.addWidget(self.terminal)

    def set_project_root(self, path):
        """Public method to set the project root directory and restart the process."""
        self.project_root = path
        self._init_process()

    def _init_process(self):
        """Initializes and starts the shell process."""
        if self.process:
            self.process.kill()
            self.process.waitForFinished()

        self.process = QProcess(self)

        # Determine the working directory, fallback to user's home directory
        working_directory = (
            self.project_root
            if self.project_root and os.path.isdir(self.project_root)
            else QDir.homePath()
        )
        self.process.setWorkingDirectory(working_directory)

        shell = "powershell.exe" if os.name == "nt" else "/bin/bash"
        self.process.start(shell)

        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)

    def handle_stdout(self):
        self.terminal.moveCursor(QTextCursor.MoveOperation.End)
        data = (
            self.process.readAllStandardOutput().data().decode("utf-8", errors="ignore")
        )
        self.terminal.insertPlainText(data)
        self.terminal.moveCursor(QTextCursor.MoveOperation.End)
        self.input_start_position = self.terminal.textCursor().position()

    def handle_stderr(self):
        self.terminal.moveCursor(QTextCursor.MoveOperation.End)
        data = (
            self.process.readAllStandardError().data().decode("utf-8", errors="ignore")
        )
        self.terminal.setTextColor(QColor("red"))
        self.terminal.insertPlainText(data)
        self.terminal.setTextColor(QColor("white"))  # Reset color
        self.terminal.moveCursor(QTextCursor.MoveOperation.End)
        self.input_start_position = self.terminal.textCursor().position()

    def terminal_key_press_event(self, event: QKeyEvent):
        cursor = self.terminal.textCursor()

        if cursor.position() < self.input_start_position:
            cursor.setPosition(self.input_start_position)
            self.terminal.setTextCursor(cursor)

        if (
            event.key() == Qt.Key.Key_Backspace
            and cursor.position() == self.input_start_position
        ):
            return  # Don't delete the prompt

        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.terminal.setTextCursor(cursor)

            cursor.setPosition(
                self.input_start_position, QTextCursor.MoveMode.KeepAnchor
            )
            command = cursor.selectedText() + "\n"

            QTextEdit.keyPressEvent(
                self.terminal, event
            )  # Let the editor handle the newline

            self.process.write(command.encode("utf-8"))
            self.input_start_position = self.terminal.textCursor().position()
        else:
            QTextEdit.keyPressEvent(self.terminal, event)

    def execute_command(self, command: str):
        """Writes a command to the terminal process to be executed."""
        if self.process.state() == QProcess.ProcessState.Running:
            # Ensure the command ends with a newline to be executed
            if not command.endswith("\n"):
                command += "\n"
            self.process.write(command.encode("utf-8"))

    def process_finished(self):
        self.terminal.append("\n[Process finished]")

    def closeEvent(self, event):
        if self.process.state() == QProcess.ProcessState.Running:
            self.process.kill()
            self.process.waitForFinished()
        super().closeEvent(event)
