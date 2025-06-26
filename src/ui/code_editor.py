import os
from PyQt6.QtWidgets import QTabWidget, QTextEdit, QVBoxLayout, QWidget, QMenu, QMessageBox, QPlainTextEdit
from PyQt6.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor, QPainter, QMouseEvent
from PyQt6.QtCore import QRegularExpression, pyqtSignal, QRect, QSize, Qt

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

class LineNumberArea(QWidget):
    """A widget that displays line numbers for a QTextEdit."""
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)

    def mousePressEvent(self, event: QMouseEvent):
        self.editor.line_number_area_mouse_press_event(event)


class CodeEditor(QPlainTextEdit):
    """A code editor widget with syntax highlighting and line numbers."""
    code_executed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        font = QFont("Consolas", 11)
        self.setFont(font)

        self.line_number_area = LineNumberArea(self)
        self.highlighter = PythonHighlighter(self.document())

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.textChanged.connect(self.scan_for_folding_regions)

        self.folding_regions = {}
        self.update_line_number_area_width(0)
        self.highlight_current_line()
        self.scan_for_folding_regions()

    def line_number_area_width(self):
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        # Padding: folding marker(M) + 5px + line numbers + 5px
        space = self.fontMetrics().horizontalAdvance('M') + 5 + self.fontMetrics().horizontalAdvance('9') * digits + 5
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#f0f0f0"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                # Draw folding marker
                if block_number in self.folding_regions:
                    painter.setPen(QColor("#606060"))
                    marker_rect = QRect(0, int(top), self.fontMetrics().horizontalAdvance('M'), self.fontMetrics().height())
                    if block.next().isVisible(): # Unfolded
                        painter.drawText(marker_rect, Qt.AlignmentFlag.AlignCenter, "−") # Use minus sign
                    else: # Folded
                        painter.drawText(marker_rect, Qt.AlignmentFlag.AlignCenter, "+")

                # Draw line number
                number = str(block_number + 1)
                painter.setPen(QColor("#a0a0a0"))
                number_x_start = self.fontMetrics().horizontalAdvance('M') + 5
                number_width = self.line_number_area.width() - number_x_start - 5
                number_rect = QRect(number_x_start, int(top), number_width, self.fontMetrics().height())
                painter.drawText(number_rect, Qt.AlignmentFlag.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def line_number_area_mouse_press_event(self, event: QMouseEvent):
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.position().y():
            if top <= event.position().y() <= bottom:
                # Check if the click is on the folding marker area
                marker_width = self.fontMetrics().horizontalAdvance('M')
                if event.position().x() <= marker_width:
                    if block_number in self.folding_regions:
                        self.toggle_fold(block_number)
                break
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def scan_for_folding_regions(self):
        self.folding_regions = {}
        indent_stack = []
        block = self.document().firstBlock()

        while block.isValid():
            text = block.text()
            indent_level = len(text) - len(text.lstrip())

            if indent_level > (indent_stack[-1][1] if indent_stack else -1):
                indent_stack.append((block.blockNumber(), indent_level))

            while indent_stack and indent_level < indent_stack[-1][1]:
                start_block_num, _ = indent_stack.pop()
                end_block = block.previous()
                self.folding_regions[start_block_num] = end_block.blockNumber()

            block = block.next()

        while indent_stack:
            start_block_num, _ = indent_stack.pop()
            end_block = self.document().lastBlock()
            self.folding_regions[start_block_num] = end_block.blockNumber()

    def toggle_fold(self, start_block_num):
        if start_block_num not in self.folding_regions:
            return

        end_block_num = self.folding_regions[start_block_num]
        start_block = self.document().findBlockByNumber(start_block_num)
        should_show = not start_block.next().isVisible()

        block = start_block.next()
        while block.isValid() and block.blockNumber() <= end_block_num:
            block.setVisible(should_show)
            block = block.next()
        self.line_number_area.update()

    def highlight_current_line(self):
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor("#e8e8e8")
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
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
