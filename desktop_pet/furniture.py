"""Furniture: bed, food bowl and toys share one system.

Every item is a small always-on-top window standing on the ground. Drag it
anywhere; let go and it falls back down. A new object is a Furniture subclass
added to KINDS: size, default spot, how it's drawn and what a click does.
"""
import math
import random
import time

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

GRAVITY = 1.0
MAX_FALL_SPEED = 30
DRAG_THRESHOLD = 5
TICK_S = 0.033            # matches the pet's timer; used to turn a throw into a speed


class Furniture(QWidget):
    kind = "base"
    W, H = 40, 40
    DEFAULT_AT = 0.5      # default x, as a fraction of the screen width
    tooltip = ""

    def __init__(self, data, area, notify):
        super().__init__()
        self.area = area                  # callable returning the usable screen rect
        self.notify = notify              # notify(event, item): "picked", "landed", "used"

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(self.W, self.H)
        if self.tooltip:
            self.setToolTip(self.tooltip)

        a = area()
        x = data.get("x")
        if x is None:
            x = a.x() + a.width() * self.DEFAULT_AT - self.W / 2
        self.fx = self.clamp_x(float(x))
        self.fy = float(self.ground())
        self.vx = self.vy = 0.0
        self.dragging = False
        self._press = None
        self._grab = None
        self._trail = []
        self.move(int(self.fx), int(self.fy))

    # ---------- geometry ----------
    def ground(self):
        a = self.area()
        return a.y() + a.height() - self.H

    def clamp_x(self, x):
        a = self.area()
        return min(max(x, a.x()), a.x() + a.width() - self.W)

    def center_x(self):
        return self.fx + self.W / 2

    def on_ground(self):
        return self.fy >= self.ground() - 0.5

    def resting(self):
        """Standing still on the ground: the pet can use it."""
        return not self.dragging and self.on_ground() and abs(self.vx) < 0.5

    # ---------- physics, called from the pet's timer ----------
    def tick(self):
        if self.dragging:
            return
        g = self.ground()
        if self.fy > g and self.vy >= 0:  # dropped below the ground line
            self.fy = g
        if self.fy < g or self.vy < 0:
            self.vy = min(self.vy + GRAVITY, MAX_FALL_SPEED)
            self.fy += self.vy
            if self.fy >= g:
                self.fy = g
                self.land()
        self.roll()
        self.move(int(self.fx), int(self.fy))

    def land(self):
        self.vy = 0
        self.notify("landed", self)

    def roll(self):
        """Sideways movement; only toys roll."""

    # ---------- mouse: drag anywhere, click to use ----------
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._press = e.globalPosition().toPoint()
            self._grab = self._press - self.pos()
            self._trail = []

    def mouseMoveEvent(self, e):
        if self._press is None or not (e.buttons() & Qt.MouseButton.LeftButton):
            return
        cur = e.globalPosition().toPoint()
        if not self.dragging and (cur - self._press).manhattanLength() > DRAG_THRESHOLD:
            self.dragging = True
            self.vx = self.vy = 0.0
            self.notify("picked", self)
        if self.dragging:
            top_left = cur - self._grab
            self.fx, self.fy = self.clamp_x(float(top_left.x())), float(top_left.y())
            self.move(int(self.fx), int(self.fy))
            self._trail = (self._trail + [(time.monotonic(), cur)])[-5:]

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton or self._press is None:
            return
        if self.dragging:
            self.dragging = False
            self.dropped(self._throw_speed())
        else:
            self.clicked()
        self._press = None

    def _throw_speed(self):
        """Mouse speed over the last few moves, in pixels per tick."""
        if len(self._trail) < 2:
            return 0.0, 0.0
        (t0, p0), (t1, p1) = self._trail[0], self._trail[-1]
        dt = max(t1 - t0, 1e-3)
        cap = MAX_FALL_SPEED
        vx = max(-cap, min(cap, (p1.x() - p0.x()) / dt * TICK_S))
        vy = max(-cap, min(cap, (p1.y() - p0.y()) / dt * TICK_S))
        return vx, vy

    def dropped(self, speed):
        """Let go after a drag: just fall straight down."""
        self.vx = self.vy = 0.0
        if self.on_ground():
            self.fy = self.ground()
            self.land()

    def clicked(self):
        pass

    def to_dict(self):
        return {"kind": self.kind, "x": int(self.fx)}


# ----------------------------------------------------------------------
class Bowl(Furniture):
    kind = "bowl"
    W, H = 56, 30
    DEFAULT_AT = 0.15
    tooltip = "Click to fill · drag to move"

    RIM = QColor("#3f7fbf")
    SIDE = QColor("#2f6aa6")
    KIBBLE = (QColor("#a0612b"), QColor("#7d4a1f"), QColor("#c07a3a"))

    def __init__(self, data, area, notify):
        super().__init__(data, area, notify)
        self.full = bool(data.get("full", False))
        rnd = random.Random(7)            # fixed kibble layout, no jitter on repaint
        self._kibble = [(rnd.uniform(12, 44), rnd.uniform(4, 11), rnd.choice(self.KIBBLE))
                        for _ in range(16)]

    def clicked(self):
        self.fill()

    def fill(self):
        if not self.full:
            self.full = True
            self.update()
            self.notify("used", self)

    def empty(self):
        self.full = False
        self.update()

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
        p.setBrush(self.SIDE)
        p.drawPath(body)
        p.setBrush(self.RIM)
        p.drawRoundedRect(QRectF(0, 10, 56, 6), 3, 3)
        p.end()

    def to_dict(self):
        return {**super().to_dict(), "full": self.full}


# ----------------------------------------------------------------------
class Bed(Furniture):
    kind = "bed"
    W, H = 124, 30
    DEFAULT_AT = 0.82
    LIFT = 10             # how far above the ground a pet lies on the cushion
    tooltip = "Pet bed · drag to move"

    BASE = QColor("#7a5ea8")
    RIM = QColor("#9478c4")
    CUSHION = QColor("#e9e1f5")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.BASE)
        p.drawRoundedRect(QRectF(2, 8, self.W - 4, self.H - 8), 12, 12)
        p.setBrush(self.CUSHION)
        p.drawEllipse(QRectF(12, 10, self.W - 24, 14))
        p.setBrush(self.RIM)
        p.drawRoundedRect(QRectF(0, self.H - 12, self.W, 12), 6, 6)
        p.end()


# ----------------------------------------------------------------------
class Ball(Furniture):
    kind = "ball"
    W, H = 24, 24
    DEFAULT_AT = 0.5
    ROLL_FRICTION = 0.97
    WALL_BOUNCE = 0.7
    FLOOR_BOUNCE = 0.45
    tooltip = "Click to kick · throw it!"

    RED = QColor("#e04848")
    STRIPE = QColor("#f5f0e6")

    def __init__(self, data, area, notify):
        super().__init__(data, area, notify)
        self.angle = 0.0

    def rolling(self):
        return not self.resting()

    def kick(self, vx, vy=-3.0):
        self.vx, self.vy = vx, vy

    def clicked(self):
        self.kick(random.choice((-1, 1)) * random.uniform(6, 10))
        self.notify("used", self)

    def dropped(self, speed):
        self.vx, self.vy = speed
        self.notify("used", self)          # a thrown ball is an invitation to play

    def land(self):
        if self.vy > 4:
            self.vy = -self.vy * self.FLOOR_BOUNCE
        else:
            self.vy = 0

    def roll(self):
        if self.vx == 0:
            return
        self.fx += self.vx
        a = self.area()
        if self.fx <= a.x() or self.fx >= a.x() + a.width() - self.W:
            self.fx = self.clamp_x(self.fx)
            self.vx = -self.vx * self.WALL_BOUNCE
        if self.on_ground():
            self.vx *= self.ROLL_FRICTION
        if abs(self.vx) < 0.1:
            self.vx = 0.0
        self.angle += self.vx / (self.W / 2)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.W / 2 - 1
        p.translate(self.W / 2, self.H / 2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.RED)
        p.drawEllipse(QPointF(0, 0), r, r)
        p.rotate(math.degrees(self.angle))
        p.setPen(QPen(self.STRIPE, 3))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(-r, 0), QPointF(r, 0))
        p.drawArc(QRectF(-r * 0.5, -r, r, 2 * r), 90 * 16, 180 * 16)
        p.end()


KINDS = {"bowl": Bowl, "bed": Bed, "ball": Ball}
DEFAULT_HOME = ["bowl", "bed", "ball"]


class Home:
    """All furniture on the desktop."""

    def __init__(self, data, area, notify):
        entries = data.get("furniture")
        if entries is None:                # older saves: just a bowl
            old_bowl = data.get("bowl") or {}
            entries = [{"kind": k, **(old_bowl if k == "bowl" else {})} for k in DEFAULT_HOME]
        self.items = [KINDS[e["kind"]](e, area, notify) for e in entries if e.get("kind") in KINDS]

    def first(self, kind):
        return next((i for i in self.items if i.kind == kind), None)

    def show(self):
        for i in self.items:
            i.show()

    def tick(self):
        for i in self.items:
            i.tick()

    def to_list(self):
        return [i.to_dict() for i in self.items]
