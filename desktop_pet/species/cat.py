import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainterPath, QPen, QPolygonF

from .base import Species

BODY = QColor("#e8964a")
DARK = QColor("#b86a28")
BELLY = QColor("#f6d9b0")
NOSE = QColor("#d9567a")
MOUTH = QColor("#7a2e3b")
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


def eye_shift(look):
    """Pupil offset for a look direction (dx, dy) in -1..1, facing right."""
    if not look:
        return 0, 0
    return look[0] * 2.5, look[1] * 2.0


def closed_eyes(p, centres):
    """Happy closed eyes: little upward arcs."""
    p.setPen(QPen(BLACK, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.setBrush(Qt.BrushStyle.NoBrush)
    for cx, cy in centres:
        p.drawArc(QRectF(cx - 4, cy - 3, 8, 7), 20 * 16, 140 * 16)


def line(p, x1, y1, x2, y2, color, width):
    path = QPainterPath()
    path.moveTo(x1, y1)
    path.lineTo(x2, y2)
    stroke(p, path, color, width)


class Cat(Species):
    name = "cat"
    idle_anims = {                           # idle animation -> how long it lasts (s)
        "sit": (5, 12),
        "groom": (3, 6),
        "stretch": (2, 3),
        "yawn": (1.6, 2.2),
        "look": (2.5, 4),
    }
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
        if pose in ("sit", "groom"):
            return 71, 24
        if pose == "stretch":
            return 83, 56
        return 78, 36

    # where hats and collars go, per pose: (x, y, tilt)
    HATS = {"sit": (71, 3, 0), "groom": (73, 9, 8), "stretch": (84, 40, 8),
            "eat": (82, 34, 12), "held": (79, 6, 0), "fall": (79, 6, 0), "sleep": (70, 44, -8)}
    NECKS = {"sit": (69, 42, 80), "groom": (68, 47, 60), "stretch": (70, 62, 30),
             "eat": (66, 49, 20), "held": (65, 39, 25), "fall": (65, 39, 25), "sleep": None}

    def hat_anchor(self, pose):
        return self.HATS.get(pose, (79, 16, 0))

    def neck_anchor(self, pose):
        return self.NECKS.get(pose, (65, 47, 20))

    # ------------------------------------------------------------------
    def paint(self, p, pose, facing, t, frame, look=None):
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
        elif pose == "sit":
            self._sit(p, t, look)
        elif pose == "groom":
            self._groom(p, t)
        elif pose == "stretch":
            self._stretch(p, t)
        elif pose == "yawn":
            self._stand(p, t, frame, moving=False, yawn=max(0.0, math.sin(t * 0.12)))
        else:
            if pose == "look" and look is None:  # gazing around on its own
                look = (math.sin(t * 0.07), -0.3)
            self._stand(p, t, frame, moving=(pose == "walk"), look=look)
        p.restore()

        if pose == "sleep":                  # text must not be mirrored
            self._zzz(p, t, facing)

    # ------------------------------------------------------------------
    def _stand(self, p, t, frame, moving, look=None, yawn=0.0):
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

        # eyes + nose (+ mouth when yawning)
        if yawn > 0.15:
            closed_eyes(p, ((77, 36 + bob), (91, 36 + bob)))
            fill(p, MOUTH)
            oval(p, 88, 46 + bob, 98, 47 + bob + 10 * yawn)
        else:
            ex, ey = eye_shift(look)
            fill(p, BLACK)
            oval(p, 74 + ex, 32 + bob + ey, 80 + ex, 40 + bob + ey)
            oval(p, 88 + ex, 32 + bob + ey, 94 + ex, 40 + bob + ey)
        fill(p, NOSE)
        poly(p, [(92, 44 + bob), (98, 44 + bob), (95, 48 + bob)])

    # ------------------------------------------------------------------
    def _sit_body(self, p, t):
        """Shared by sit and groom: haunches down, tail curled round the front."""
        flick = math.sin(t * 0.08) * 3
        tail = QPainterPath()
        tail.moveTo(40, 74)
        tail.cubicTo(18, 82, 6, 72, 10 + flick, 58)
        stroke(p, tail, DARK, 7)

        fill(p, BODY)
        oval(p, 28, 52, 62, 78)              # back thigh
        oval(p, 36, 28, 76, 78)              # upright body
        fill(p, BELLY)
        oval(p, 50, 42, 72, 78)

    def _sit(self, p, t, look):
        self._sit_body(p, t)
        fill(p, DARK)
        oval(p, 58, 52, 66, 78)
        oval(p, 66, 52, 74, 78)

        fill(p, BODY)
        oval(p, 52, 6, 90, 42)
        poly(p, [(56, 14), (58, -4), (70, 8)])
        poly(p, [(72, 8), (84, -4), (88, 16)])
        ex, ey = eye_shift(look)
        fill(p, BLACK)
        oval(p, 66 + ex, 18 + ey, 72 + ex, 26 + ey)
        oval(p, 80 + ex, 18 + ey, 86 + ex, 26 + ey)
        fill(p, NOSE)
        poly(p, [(84, 30), (90, 30), (87, 34)])

    def _groom(self, p, t):
        """Sitting, licking a raised front paw."""
        lick = math.sin(t * 0.35) * 2
        self._sit_body(p, t)
        fill(p, DARK)
        oval(p, 58, 52, 66, 78)              # the paw still on the ground

        fill(p, BODY)
        oval(p, 54, 12, 92, 48)              # head tipped down to the paw
        poly(p, [(57, 20), (57, 2), (70, 14)])
        poly(p, [(73, 13), (85, 1), (90, 21)])
        closed_eyes(p, ((70, 26), (83, 26)))
        fill(p, NOSE)
        poly(p, [(86, 35), (92, 35), (89, 39)])

        line(p, 68, 60, 86 + lick, 44 + lick, DARK, 9)   # raised paw
        fill(p, MOUTH)
        oval(p, 86, 40 + lick, 92, 45 + lick)            # tongue

    def _stretch(self, p, t):
        """Front down, back end up, front legs reaching forward."""
        wag = math.sin(t * 0.1) * 4
        tail = QPainterPath()
        tail.moveTo(22, 38)
        tail.quadTo(8, 14 + wag, 20, 0 + wag)
        stroke(p, tail, DARK, 7)

        fill(p, DARK)
        oval(p, 22, 44, 32, 78)              # back legs straight
        oval(p, 32, 44, 42, 78)
        oval(p, 58, 68, 98, 77)              # front legs out along the floor
        oval(p, 54, 70, 92, 78)

        p.save()
        p.translate(50, 52)
        p.rotate(22)                         # body sloping down to the front
        fill(p, BODY)
        oval(p, -32, -15, 30, 15)
        fill(p, BELLY)
        oval(p, -22, 0, 22, 15)
        p.restore()

        fill(p, BODY)
        oval(p, 66, 42, 100, 72)
        poly(p, [(70, 48), (70, 32), (82, 44)])
        poly(p, [(86, 44), (98, 32), (100, 52)])
        closed_eyes(p, ((80, 55), (92, 55)))
        fill(p, NOSE)
        poly(p, [(96, 63), (102, 63), (99, 67)])

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
