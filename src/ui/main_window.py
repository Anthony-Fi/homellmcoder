import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QTextEdit, QSplitter, QTreeView, QLabel
)
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtCore import Qt, QDir

class MainWindow(QMainWindow):
    """Main application window with a three-panel layout."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("HomeLLMCoder - Offline AI Desktop App")
        self.setGeometry(100, 100, 1200, 800)

        # Create main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create the main splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter)

        # Left panel: File Navigator
        file_navigator = self._create_file_navigator()
        main_splitter.addWidget(file_navigator)

        # Right panel: Code Editor and Terminal/Chat
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        main_splitter.addWidget(right_splitter)

        # Top-right: Code Editor (placeholder)
        code_editor = QTextEdit()
        code_editor.setPlaceholderText("Code editor goes here...")
        right_splitter.addWidget(code_editor)

        # Bottom-right: Terminal/Chat (placeholder)
        terminal_chat = QTextEdit()
        terminal_chat.setPlaceholderText("Terminal/Chat panel goes here...")
        right_splitter.addWidget(terminal_chat)

        # Set initial sizes for the splitters
        main_splitter.setSizes([250, 950])
        right_splitter.setSizes([600, 200])

    def _create_file_navigator(self) -> QWidget:
        """Creates the file navigator panel."""
        navigator_container = QWidget()
        layout = QVBoxLayout(navigator_container)
        layout.setContentsMargins(0, 0, 0, 0)

        model = QFileSystemModel()
        model.setRootPath(QDir.currentPath())

        tree = QTreeView()
        tree.setModel(model)
        tree.setRootIndex(model.index(QDir.currentPath()))
        tree.setColumnWidth(0, 200)
        tree.setAlternatingRowColors(True)

        layout.addWidget(tree)
        return navigator_container

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
