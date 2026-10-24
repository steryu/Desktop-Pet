"""A butterfly that flutters across the screen (random event); the pet chases it."""
import math
import random

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

COLORS = (QColor("#f2a541"), QColor("#7fb3e8"), QColor("#e37bc0"), QColor("#f5e15b"))


class Butterfly(QWidget):
    W, H = 30, 26

    def __init__(self, area):
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
        self.setFixedSize(self.W, self.H)

        self.area = area
        a = area()
        self.dir = random.choice((-1, 1))
        self.bx = a.x() - self.W if self.dir > 0 else a.x() + a.width()
        self.base_y = a.y() + a.height() - random.uniform(110, 180)
        self.by = self.base_y
        self.speed = random.uniform(1.8, 2.6)
        self.lift = 0.0                  # extra height after dodging a pounce
        self.color = random.choice(COLORS)
        self.t = random.randint(0, 100)
        self.move(int(self.bx), int(self.by))

    def center(self):
        return self.bx + self.W / 2, self.by + self.H / 2

    def dodge(self):
        self.lift = 70.0
        self.speed *= 1.15

    def gone(self):
        a = self.area()
        return self.bx < a.x() - self.W - 5 or self.bx > a.x() + a.width() + 5

    def tick(self):
        self.t += 1
        self.bx += self.dir * self.speed
        self.lift *= 0.985
        self.by = self.base_y - self.lift + math.sin(self.t * 0.08) * 22
        self.move(int(self.bx), int(self.by))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        flap = 0.25 + 0.75 * abs(math.sin(self.t * 0.45))   # wings open and close
        cx, cy = self.W / 2, self.H / 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.color)
        for side in (-1, 1):
            p.drawEllipse(QPointF(cx + side * 7 * flap, cy - 4), 7 * flap, 7)
            p.drawEllipse(QPointF(cx + side * 5 * flap, cy + 5), 5 * flap, 5)
        p.setPen(QPen(QColor("#3a2a1a"), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(cx, cy - 7), QPointF(cx, cy + 8))
        p.end()
