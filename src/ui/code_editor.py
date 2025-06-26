import os
from PyQt6.QtWidgets import QTabWidget, QTextEdit, QVBoxLayout, QWidget
from PyQt6.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor
from PyQt6.QtCore import QRegularExpression

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
    def __init__(self, parent=None):
        super().__init__(parent)
        font = QFont("Consolas", 11)
        self.setFont(font)
        self.highlighter = PythonHighlighter(self.document())

class TabbedCodeEditor(QWidget):
    """A widget that contains multiple CodeEditor widgets in a tabbed view."""
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

        index = self.tab_widget.addTab(editor, os.path.basename(file_path))
        self.tab_widget.setTabToolTip(index, file_path)
        self.tab_widget.setCurrentIndex(index)

    def close_tab(self, index):
        """Closes the tab at the given index."""
        widget = self.tab_widget.widget(index)
        if widget:
            widget.deleteLater()
        self.tab_widget.removeTab(index)
