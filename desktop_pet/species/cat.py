import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainterPath, QPen, QPolygonF

from .base import Species

BODY = QColor("#e8964a")
DARK = QColor("#b86a28")
BELLY = QColor("#f6d9b0")
NOSE = QColor("#d9567a")
BLACK = QColor("#111111")


def fill(p, color):
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)


def oval(p, x1, y1, x2, y2):
    p.drawEllipse(QRectF(x1, y1, x2 - x1, y2 - y1))


def poly(p, pts):
    p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in pts]))


def stroke(p, path, color, width):
    p.setPen(QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(path)


def line(p, x1, y1, x2, y2, color, width):
    path = QPainterPath()
    path.moveTo(x1, y1)
    path.lineTo(x2, y2)
    stroke(p, path, color, width)


class Cat(Species):
    name = "cat"
    width = 110
    height = 90
    feet_y = 78
    sleep_feet_y = 82
    walk_speed = 2.0
    reach_x = 98

    def head_for(self, pose):
        if pose == "sleep":
            return 70, 50
        if pose == "eat":                    # x is also where the bowl lines up
            return 82, 48
        return 78, 36

    # ------------------------------------------------------------------
    def paint(self, p, pose, facing, t, frame):
        p.save()
        if facing < 0:                       # mirror when facing left
            p.translate(self.width, 0)
            p.scale(-1, 1)

        if pose == "sleep":
            self._sleep(p, t)
        elif pose in ("held", "fall"):
            self._held(p, t)
        elif pose == "eat":
            self._eat(p, t)
        else:
            self._stand(p, t, frame, moving=(pose == "walk"))
        p.restore()

        if pose == "sleep":                  # text must not be mirrored
            self._zzz(p, t, facing)

    # ------------------------------------------------------------------
    def _stand(self, p, t, frame, moving):
        bob = 1 if (moving and frame % 2) else 0
        wag = math.sin(t * (0.25 if moving else 0.1)) * (6 if moving else 4)

        # tail
        tail = QPainterPath()
        tail.moveTo(18, 42 + bob)
        tail.quadTo(2, 32 + wag, 8, 14 + wag)
        stroke(p, tail, DARK, 7)

        # legs
        if moving:
            o1, o2 = (-4, 4) if frame in (0, 1) else (4, -4)
        else:
            o1 = o2 = 0
        fill(p, DARK)
        for lx, o in ((26, o1), (34, o2), (58, o2), (66, o1)):
            oval(p, lx, 60, lx + 10, 76 + o * 0.5)

        # body
        fill(p, BODY)
        oval(p, 16, 32 + bob, 76, 68 + bob)
        fill(p, BELLY)
        oval(p, 26, 48 + bob, 66, 68 + bob)

        # head, ears
        fill(p, BODY)
        oval(p, 60, 20 + bob, 98, 56 + bob)
        poly(p, [(64, 26 + bob), (66, 8 + bob), (78, 22 + bob)])
        poly(p, [(80, 22 + bob), (92, 8 + bob), (96, 28 + bob)])

        # eyes + nose
        fill(p, BLACK)
        oval(p, 74, 32 + bob, 80, 40 + bob)
        oval(p, 88, 32 + bob, 94, 40 + bob)
        fill(p, NOSE)
        poly(p, [(92, 44 + bob), (98, 44 + bob), (95, 48 + bob)])

    # ------------------------------------------------------------------
    def _eat(self, p, t):
        """Head down in the bowl, munching, eyes happily closed."""
        munch = abs(math.sin(t * 0.5)) * 3
        wag = math.sin(t * 0.1) * 4

        tail = QPainterPath()
        tail.moveTo(18, 42)
        tail.quadTo(2, 32 + wag, 8, 14 + wag)
        stroke(p, tail, DARK, 7)

        fill(p, DARK)
        for lx in (26, 34, 58, 66):
            oval(p, lx, 60, lx + 10, 76)

        fill(p, BODY)
        oval(p, 16, 32, 76, 68)
        fill(p, BELLY)
        oval(p, 26, 48, 66, 68)

        hy = 36 + munch                      # head top, bobbing while chewing
        fill(p, BODY)
        oval(p, 64, hy, 100, hy + 32)
        poly(p, [(67, hy + 6), (66, hy - 10), (78, hy + 3)])
        poly(p, [(84, hy + 3), (95, hy - 10), (98, hy + 8)])

        p.setPen(QPen(BLACK, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        for ex in (78, 91):
            p.drawArc(QRectF(ex - 4, hy + 12, 8, 7), 20 * 16, 140 * 16)
        fill(p, NOSE)
        poly(p, [(93, hy + 22), (99, hy + 22), (96, hy + 26)])

    # ------------------------------------------------------------------
    def _held(self, p, t):
        """Picked up / falling: legs dangle and flail, eyes wide, tail puffed."""
        wag = math.sin(t * 0.5) * 5

        tail = QPainterPath()
        tail.moveTo(18, 34)
        tail.quadTo(0, 20 + wag, 10, 4 + wag)
        stroke(p, tail, DARK, 9)

        # dangling legs
        for lx in (26, 36, 58, 68):
            sw = math.sin(t * 0.45 + lx * 0.3) * 6
            line(p, lx + 5, 52, lx + 5 + sw, 80, DARK, 8)

        fill(p, BODY)
        oval(p, 16, 22, 76, 60)
        fill(p, BELLY)
        oval(p, 26, 40, 66, 60)

        fill(p, BODY)
        oval(p, 60, 10, 98, 46)
        poly(p, [(64, 16), (62, -4), (78, 12)])
        poly(p, [(80, 12), (94, -4), (96, 18)])

        # big surprised eyes + open mouth
        fill(p, QColor("white"))
        oval(p, 71, 20, 81, 32)
        oval(p, 86, 20, 96, 32)
        fill(p, BLACK)
        oval(p, 74, 23, 79, 30)
        oval(p, 89, 23, 94, 30)
        fill(p, NOSE)
        poly(p, [(88, 34), (94, 34), (91, 38)])
        fill(p, QColor("#7a2e3b"))
        oval(p, 87, 39, 95, 45)

    # ------------------------------------------------------------------
    def _sleep(self, p, t):
        br = math.sin(t * 0.08) * 2

        fill(p, BODY)
        oval(p, 10, 40 - br, 92, 82)
        fill(p, BELLY)
        oval(p, 24, 58, 80, 82)

        tail = QPainterPath()
        tail.moveTo(14, 74)
        tail.cubicTo(30, 90, 62, 90, 78, 78)
        stroke(p, tail, DARK, 7)

        fill(p, BODY)
        oval(p, 50, 46 - br / 2, 90, 80)
        poly(p, [(54, 54 - br / 2), (56, 38 - br / 2), (68, 50 - br / 2)])
        poly(p, [(72, 50 - br / 2), (84, 38 - br / 2), (88, 56 - br / 2)])

        # closed eyes
        p.setPen(QPen(BLACK, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        for ex in (62, 78):
            p.drawArc(QRectF(ex - 5, 58 - br / 2, 10, 10), 200 * 16, 140 * 16)

    def _zzz(self, p, t, facing):
        for i in range(3):
            phase = ((t * 0.6 + i * 28) % 84) / 84.0
            zx = 86 + phase * 14
            zy = 40 - phase * 36
            if facing < 0:
                zx = self.width - zx
            p.setPen(QColor(85, 85, 85, int(255 * (1 - phase))))
            p.setFont(QFont("Arial", 8 + int(phase * 8), QFont.Weight.Bold))
            p.drawText(QPointF(zx, zy), "z")
