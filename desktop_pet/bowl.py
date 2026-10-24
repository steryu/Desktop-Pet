"""Food bowl: a small always-on-top window standing on the ground.
Click it to fill it; the pet walks over and eats when it's hungry."""
import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget

BOWL_W, BOWL_H = 56, 30

RIM = QColor("#3f7fbf")
SIDE = QColor("#2f6aa6")
KIBBLE = (QColor("#a0612b"), QColor("#7d4a1f"), QColor("#c07a3a"))


class BowlWindow(QWidget):
    def __init__(self, data, area, on_filled):
        super().__init__()
        self.area = area                  # callable returning the usable screen rect
        self.on_filled = on_filled
        self.full = bool(data.get("full", False))

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(BOWL_W, BOWL_H)
        self.setToolTip("Click to fill")

        # fixed kibble layout so it doesn't jitter on repaint
        rnd = random.Random(7)
        self._kibble = [(rnd.uniform(12, 44), rnd.uniform(4, 11), rnd.choice(KIBBLE))
                        for _ in range(16)]
        self.place(data.get("x"))

    def place(self, x=None):
        a = self.area()
        if x is None:
            x = a.x() + a.width() * 0.15
        x = min(max(float(x), a.x()), a.x() + a.width() - BOWL_W)
        self.move(int(x), a.y() + a.height() - BOWL_H)

    def center_x(self):
        return self.x() + BOWL_W / 2

    def fill(self):
        if not self.full:
            self.full = True
            self.update()
            self.on_filled()

    def empty(self):
        self.full = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.fill()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)

        if self.full:
            for x, y, c in self._kibble:
                p.setBrush(c)
                p.drawEllipse(QPointF(x, y + 2), 4, 3)

        body = QPainterPath()
        body.moveTo(2, 12)
        body.lineTo(54, 12)
        body.lineTo(46, 29)
        body.lineTo(10, 29)
        body.closeSubpath()
        p.setBrush(SIDE)
        p.drawPath(body)
        p.setBrush(RIM)
        p.drawRoundedRect(QRectF(0, 10, 56, 6), 3, 3)
        p.end()

    def to_dict(self):
        return {"x": self.x(), "full": self.full}
