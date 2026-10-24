"""Speech bubble that floats above the pet's head for a few seconds."""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

PAD_X, PAD_Y, TAIL = 10, 6, 8
TICKS_PER_S = 30

FILL = QColor(255, 255, 255, 245)
BORDER = QColor(0, 0, 0, 60)
TEXT = QColor("#333333")


class SpeechBubble(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.font = QFont("Arial", 11)
        self.text = ""
        self.ticks_left = 0
        self.tail_x = 0

    def say(self, text, seconds=3.5):
        self.text = text
        fm = QFontMetrics(self.font)
        self.setFixedSize(fm.horizontalAdvance(text) + 2 * PAD_X + 2, fm.height() + 2 * PAD_Y + TAIL)
        self.ticks_left = int(seconds * TICKS_PER_S)
        self.update()

    def speaking(self):
        return self.ticks_left > 0

    def tick(self):
        if self.ticks_left > 0:
            self.ticks_left -= 1

    def follow(self, head_x, top_y, area):
        """Tail points at (head_x, top_y); the bubble stays on screen."""
        w, h = self.width(), self.height()
        x = min(max(head_x - w / 2, area.x()), area.x() + area.width() - w)
        y = max(top_y - h, area.y())
        self.tail_x = min(max(head_x - x, 12), w - 12)
        self.move(int(x), int(y))

    def paintEvent(self, event):
        w, h = self.width(), self.height() - TAIL
        path = QPainterPath()
        path.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 9, 9)
        tail = QPainterPath()
        tail.moveTo(self.tail_x - 6, h - 2)
        tail.lineTo(self.tail_x, h + TAIL - 1)
        tail.lineTo(self.tail_x + 6, h - 2)
        tail.closeSubpath()
        path = path.united(tail)

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(BORDER, 1))
        p.setBrush(FILL)
        p.drawPath(path)
        p.setFont(self.font)
        p.setPen(TEXT)
        p.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, self.text)
        p.end()
