import os
from PyQt6.QtWidgets import QTabWidget, QTextEdit, QVBoxLayout, QWidget, QMenu, QMessageBox
from PyQt6.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor
from PyQt6.QtCore import QRegularExpression, pyqtSignal

class PythonHighlighter(QSyntaxHighlighter):
    """A simple syntax highlighter for Python code."""
    def __init__(self, parent):
        super().__init__(parent)
        self.highlighting_rules = []

        # Keywords (blue, bold)
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#0000ff"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = [
            "and", "as", "assert", "break", "class", "continue", "def",
            "del", "elif", "else", "except", "False", "finally", "for",
            "from", "global", "if", "import", "in", "is", "lambda",
            "None", "nonlocal", "not", "or", "pass", "raise", "return",
            "True", "try", "while", "with", "yield"
        ]
        for word in keywords:
            pattern = QRegularExpression(f"\\b{word}\\b")
            self.highlighting_rules.append((pattern, keyword_format))

        # Strings (red)
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#a31515"))
        self.highlighting_rules.append((QRegularExpression('\".*?\"'), string_format))
        self.highlighting_rules.append((QRegularExpression("\'.*?\'"), string_format))

        # Comments (green)
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#008000"))
        self.highlighting_rules.append((QRegularExpression("#[^\n]*"), comment_format))

        # Numbers (dark cyan)
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#098658"))
        self.highlighting_rules.append((QRegularExpression("\\b[0-9]+\\b"), number_format))

    def highlightBlock(self, text):
        """Applies highlighting rules to a block of text."""
        for pattern, format in self.highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)

class CodeEditor(QTextEdit):
    """A basic code editor widget that uses the PythonHighlighter."""
    code_executed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        font = QFont("Consolas", 11)
        self.setFont(font)
        self.highlighter = PythonHighlighter(self.document())

    def contextMenuEvent(self, event):
        """Creates a context menu for the editor."""
        menu = QMenu(self)
        execute_action = menu.addAction("Execute Selection")
        execute_action.setEnabled(self.textCursor().hasSelection())
        action = menu.exec(event.globalPos())

        if action == execute_action:
            selected_text = self.textCursor().selectedText()
            self.code_executed.emit(selected_text)

class TabbedCodeEditor(QWidget):
    """A widget that contains multiple CodeEditor widgets in a tabbed view."""
    code_to_execute = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.layout().addWidget(self.tab_widget)

    def open_file(self, file_path):
        """Opens a file in a new tab or focuses the existing tab."""
        for i in range(self.tab_widget.count()):
            if self.tab_widget.widget(i).property("file_path") == file_path:
                self.tab_widget.setCurrentIndex(i)
                return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error opening file {file_path}: {e}")
            return

        editor = CodeEditor()
        editor.setPlainText(content)
        editor.setProperty("file_path", file_path)
        editor.code_executed.connect(self.code_to_execute.emit)

        index = self.tab_widget.addTab(editor, os.path.basename(file_path))
        self.tab_widget.setTabToolTip(index, file_path)
        self.tab_widget.setCurrentIndex(index)

    def check_and_reload_file(self, file_path):
        """Checks if a file is open in a tab and prompts the user to reload it if it has been modified externally."""
        abs_path = os.path.abspath(file_path)
        for i in range(self.tab_widget.count()):
            editor = self.tab_widget.widget(i)
            tab_path = editor.property("file_path")
            if tab_path and os.path.abspath(tab_path) == abs_path:
                reply = QMessageBox.question(self, "File Changed", 
                                             f"The file '{os.path.basename(file_path)}' has been modified externally.\n\nDo you want to reload it?",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                             QMessageBox.StandardButton.Yes)
                if reply == QMessageBox.StandardButton.Yes:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        editor.setPlainText(content)
                        self.tab_widget.setTabText(i, os.path.basename(file_path)) # Reset tab text in case of rename
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"Could not reload file: {e}")
                break

    def close_tab(self, index):
        """Closes the tab at the given index."""
        widget = self.tab_widget.widget(index)
        if widget:
            widget.deleteLater()
        self.tab_widget.removeTab(index)
