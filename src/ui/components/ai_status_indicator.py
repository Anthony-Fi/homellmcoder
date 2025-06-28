from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QPainter, QColor, QBrush


class AIStatusIndicator(QWidget):
    """A widget that displays a colored circle to indicate AI status."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_busy = False
        self.setFixedSize(16, 16)

    def set_busy(self, busy):
        """Sets the busy status and triggers a repaint."""
        if self._is_busy != busy:
            self._is_busy = busy
            self.update()

    def paintEvent(self, event):
        """Paints the circle with the appropriate color."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = QColor("green") if self._is_busy else QColor("red")
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)

        rect = self.rect()
        painter.drawEllipse(rect)

    def sizeHint(self):
        return QSize(16, 16)
