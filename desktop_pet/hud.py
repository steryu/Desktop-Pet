"""Status panel shown above the pet while the mouse hovers over it."""
import time

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

HUD_W, HUD_H = 168, 112
PAD = 9
ROW = 15

PANEL = QColor(255, 255, 255, 238)
BORDER = QColor(0, 0, 0, 40)
TEXT = QColor("#333333")
MUTED = QColor("#808080")
TRACK = QColor(0, 0, 0, 28)
FOOD = QColor("#e8964a")
ENERGY = QColor("#4a9be8")
LOVE = QColor("#eb4062")
COIN = QColor("#e0b020")


class StatusHud(QWidget):
    def __init__(self, stats):
        super().__init__()
        self.stats = stats
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
        self.setFixedSize(HUD_W, HUD_H)

    def follow(self, center_x, top_y, area):
        """Sit just above top_y, centred on center_x, kept on screen."""
        x = min(max(center_x - HUD_W / 2, area.x()), area.x() + area.width() - HUD_W)
        y = top_y - HUD_H - 4
        if y < area.y():
            y = area.y()
        self.move(int(x), int(y))

    def paintEvent(self, event):
        s = self.stats
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(BORDER, 1))
        p.setBrush(PANEL)
        p.drawRoundedRect(QRectF(0.5, 0.5, HUD_W - 1, HUD_H - 1), 8, 8)

        y = PAD
        p.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        p.setPen(TEXT)
        title = f"{s.mood(time.time()).capitalize()} · {s.level_name()}"
        p.drawText(QRectF(PAD, y, HUD_W - 2 * PAD, ROW), Qt.AlignmentFlag.AlignVCenter, title)
        y += ROW + 3

        for label, value, color in (("Food", s.fullness / 100, FOOD),
                                    ("Energy", s.energy / 100, ENERGY),
                                    ("Love", s.level_progress(), LOVE)):
            self._bar(p, y, label, value, color)
            y += ROW

        p.setFont(QFont("Arial", 10))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(COIN)
        p.drawEllipse(QRectF(PAD, y + 3, 9, 9))
        p.setPen(TEXT)
        p.drawText(QRectF(PAD + 14, y, 60, ROW), Qt.AlignmentFlag.AlignVCenter, str(s.coins))
        y += ROW

        nxt = s.next_unlock()
        p.setFont(QFont("Arial", 9))
        p.setPen(MUTED)
        hint = f"Next: {nxt[1]} at {nxt[0]} ♥" if nxt else "All unlocked ♥"
        p.drawText(QRectF(PAD, y, HUD_W - 2 * PAD, ROW), Qt.AlignmentFlag.AlignVCenter, hint)
        p.end()

    def _bar(self, p, y, label, value, color):
        p.setFont(QFont("Arial", 10))
        p.setPen(TEXT)
        p.drawText(QRectF(PAD, y, 46, ROW), Qt.AlignmentFlag.AlignVCenter, label)
        x0, w = PAD + 48, HUD_W - 2 * PAD - 48
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(TRACK)
        p.drawRoundedRect(QRectF(x0, y + 4, w, 7), 3.5, 3.5)
        p.setBrush(color)
        p.drawRoundedRect(QRectF(x0, y + 4, w * max(0.0, min(1.0, value)), 7), 3.5, 3.5)
