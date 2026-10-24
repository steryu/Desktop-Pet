import math
import random

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPainterPath
from PySide6.QtWidgets import QApplication, QMenu, QWidget

import save as savemod

# ---------- settings you can tweak ----------
TICK_MS = 33              # ~30 fps
GRAVITY = 1.0             # falling acceleration (pixels / tick^2)
MAX_FALL_SPEED = 30
DRAG_THRESHOLD = 5        # pixels the mouse must move before a click becomes a drag
SLEEP_CHANCE = 0.45       # chance to nap after reaching a spot
IDLE_CHANCE = 0.20        # chance to just stand around for a moment
SLEEP_MIN_S, SLEEP_MAX_S = 6, 20
AUTOSAVE_MS = 15000
PAD_TOP = 44              # empty space above the pet, room for hearts
# --------------------------------------------


class PetWindow(QWidget):
    def __init__(self, species, data):
        super().__init__()
        self.species = species
        self.data = data

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool                      # no taskbar entry
            | Qt.WindowType.WindowDoesNotAcceptFocus  # don't steal focus from your apps
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(species.width, species.height + PAD_TOP)

        self.taskbar_only = bool(data.get("taskbar_only", True))
        self.times_petted = int(data.get("times_petted", 0))

        # state machine
        self.state = "walk"        # walk | idle | sleep | held | fall
        self.facing = 1
        self.frame = 0
        self.t = 0
        self.timer_ticks = 0       # countdown used by idle / sleep
        self.vy = 0.0
        self.hearts = []

        # position (top-left of the window, as floats)
        a = self.area()
        sx, sy = data.get("x"), data.get("y")
        if sx is None or sy is None:
            sx = random.uniform(a.x(), a.x() + a.width() - species.width)
            sy = self.ground_y()
        self.x = min(max(float(sx), a.x()), a.x() + a.width() - species.width)
        self.y = min(max(float(sy), a.y() - PAD_TOP), self.ground_y())
        self.tx, self.ty = self.x, self.y
        self.move(int(self.x), int(self.y))

        # mouse handling
        self._press_pos = None
        self._grab_offset = None
        self._dragging = False

        self.pick_target()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(TICK_MS)

        self.autosave = QTimer(self)
        self.autosave.timeout.connect(self.save_state)
        self.autosave.start(AUTOSAVE_MS)

    # ------------------------------------------------------------------
    # geometry helpers
    # ------------------------------------------------------------------
    def area(self):
        """Usable screen area (excludes the taskbar)."""
        return QGuiApplication.primaryScreen().availableGeometry()

    def ground_y(self, pose="walk"):
        """Window top-y at which the pet stands on top of the taskbar."""
        a = self.area()
        feet = self.species.sleep_feet_y if pose == "sleep" else self.species.feet_y
        return a.y() + a.height() - PAD_TOP - feet

    def on_ground(self):
        return abs(self.y - self.ground_y("walk")) < 6

    # ------------------------------------------------------------------
    # behaviour
    # ------------------------------------------------------------------
    def pick_target(self):
        a = self.area()
        self.tx = random.uniform(a.x(), a.x() + a.width() - self.species.width)
        if self.taskbar_only:
            self.ty = self.ground_y()
        else:
            self.ty = random.uniform(a.y(), self.ground_y())
        self.state = "walk"

    def start_sleep(self):
        self.state = "sleep"
        self.timer_ticks = int(random.uniform(SLEEP_MIN_S, SLEEP_MAX_S) * 1000 / TICK_MS)
        if self.on_ground():
            self.y = self.ground_y("sleep")      # lying body sits a bit lower

    def start_idle(self):
        self.state = "idle"
        self.timer_ticks = int(random.uniform(1, 3) * 1000 / TICK_MS)

    def set_taskbar_only(self, value):
        self.taskbar_only = bool(value)
        if self.state in ("walk", "idle", "sleep"):
            self.pick_target()

    def tick(self):
        self.t += 1

        if self.state == "walk":
            dx, dy = self.tx - self.x, self.ty - self.y
            dist = math.hypot(dx, dy)
            speed = self.species.walk_speed
            if dist <= speed:
                self.x, self.y = self.tx, self.ty
                r = random.random()
                if r < SLEEP_CHANCE:
                    self.start_sleep()
                elif r < SLEEP_CHANCE + IDLE_CHANCE:
                    self.start_idle()
                else:
                    self.pick_target()
            else:
                self.x += dx / dist * speed
                self.y += dy / dist * speed
                if abs(dx) > 1:
                    self.facing = 1 if dx > 0 else -1
                if self.t % 6 == 0:
                    self.frame = (self.frame + 1) % 4

        elif self.state == "idle":
            self.timer_ticks -= 1
            if self.timer_ticks <= 0:
                self.pick_target()

        elif self.state == "sleep":
            self.timer_ticks -= 1
            if self.timer_ticks <= 0:
                self.pick_target()

        elif self.state == "fall":
            self.vy = min(self.vy + GRAVITY, MAX_FALL_SPEED)
            self.y += self.vy
            ground = self.ground_y()
            if self.y >= ground:
                self.y = ground
                self.vy = 0
                self.start_idle()                # brief pause after landing

        # "held": position is controlled by the mouse

        self.update_hearts()
        self.move(int(self.x), int(self.y))
        self.update()

    # ------------------------------------------------------------------
    # hearts
    # ------------------------------------------------------------------
    def spawn_hearts(self):
        hx, hy = self.species.head_for(self.state)
        if self.facing < 0:
            hx = self.species.width - hx
        for i in range(3):
            self.hearts.append({
                "x": hx + random.uniform(-14, 14),
                "y": PAD_TOP + hy - 10 + random.uniform(-4, 4),
                "age": -i * 5,           # negative age = delayed start
                "life": 45,
                "size": random.uniform(5, 8),
            })

    def update_hearts(self):
        for h in self.hearts:
            h["age"] += 1
            if h["age"] > 0:
                h["y"] -= 1.1
                h["x"] += math.sin(h["age"] * 0.2) * 0.6
        self.hearts = [h for h in self.hearts if h["age"] < h["life"]]

    def paint_hearts(self, p):
        p.setPen(Qt.PenStyle.NoPen)
        for h in self.hearts:
            if h["age"] < 0:
                continue
            alpha = int(255 * (1 - h["age"] / h["life"]))
            p.setBrush(QColor(235, 64, 98, alpha))
            s, cx, cy = h["size"], h["x"], h["y"]
            path = QPainterPath()
            path.moveTo(cx, cy + s * 0.9)
            path.cubicTo(cx - s * 1.3, cy + s * 0.1, cx - s * 0.6, cy - s * 0.9, cx, cy - s * 0.3)
            path.cubicTo(cx + s * 0.6, cy - s * 0.9, cx + s * 1.3, cy + s * 0.1, cx, cy + s * 0.9)
            p.drawPath(path)

    # ------------------------------------------------------------------
    # drawing
    # ------------------------------------------------------------------
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.save()
        p.translate(0, PAD_TOP)
        self.species.paint(p, self.state, self.facing, self.t, self.frame)
        p.restore()
        self.paint_hearts(p)
        p.end()

    # ------------------------------------------------------------------
    # mouse: click = pet, drag = pick up, right-click = menu
    # ------------------------------------------------------------------
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._press_pos = e.globalPosition().toPoint()
            self._grab_offset = self._press_pos - self.pos()
            self._dragging = False
        elif e.button() == Qt.MouseButton.RightButton:
            self.show_menu(e.globalPosition().toPoint())

    def mouseMoveEvent(self, e):
        if self._press_pos is None or not (e.buttons() & Qt.MouseButton.LeftButton):
            return
        cur = e.globalPosition().toPoint()
        if not self._dragging and (cur - self._press_pos).manhattanLength() > DRAG_THRESHOLD:
            self._dragging = True
            self.state = "held"
            self.vy = 0
        if self._dragging:
            top_left = cur - self._grab_offset
            self.x, self.y = float(top_left.x()), float(top_left.y())
            self.move(int(self.x), int(self.y))

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton or self._press_pos is None:
            return
        if self._dragging:
            self.state = "fall"                  # let go -> gravity takes over
            self.vy = 0
        else:
            self.times_petted += 1
            self.spawn_hearts()
        self._press_pos = None
        self._dragging = False

    def show_menu(self, global_pos):
        menu = QMenu(self)
        act = menu.addAction("Only walk on taskbar")
        act.setCheckable(True)
        act.setChecked(self.taskbar_only)
        act.toggled.connect(self.set_taskbar_only)
        menu.addSeparator()
        menu.addAction("Quit").triggered.connect(QApplication.quit)
        menu.exec(global_pos)

    # ------------------------------------------------------------------
    def save_state(self):
        self.data.update({
            "species": self.species.name,
            "taskbar_only": self.taskbar_only,
            "x": int(self.x),
            "y": int(self.y),
            "times_petted": self.times_petted,
        })
        savemod.save(self.data)
