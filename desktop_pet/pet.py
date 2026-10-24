import math
import random
import time

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPainterPath
from PySide6.QtWidgets import QApplication, QMenu, QWidget

import save as savemod
from bowl import BowlWindow
from hud import StatusHud
from stats import ENERGY_SLEEP_PER_S, Stats

# ---------- settings you can tweak ----------
TICK_MS = 33              # ~30 fps
GRAVITY = 1.0             # falling acceleration (pixels / tick^2)
MAX_FALL_SPEED = 30
DRAG_THRESHOLD = 5        # pixels the mouse must move before a click becomes a drag
SLEEP_CHANCE = 0.15       # base chance to nap after reaching a spot, rises as energy drops
TIRED_AT = 25             # below this energy it always naps at the next stop
IDLE_CHANCE = 0.20        # chance to just stand around for a moment
SLEEP_MIN_S, SLEEP_MAX_S = 6, 20
SLEEP_LONGEST_S = 60
EAT_S = 4
HOP_SPEED = 7             # "Happy hop" unlock
GIFT_EVERY_S = 900        # "Gifts" unlock: on average one gift per 15 awake minutes
GIFT_COINS = 5
AUTOSAVE_MS = 15000
PAD_TOP = 44              # empty space above the pet, room for hearts
MOOD_SPEED = {"happy": 1.2, "sad": 0.6, "tired": 0.6, "hungry": 0.8}
MOPEY = ("sad", "tired", "hungry")
# --------------------------------------------

HEART = (235, 64, 98)
COIN_TEXT = (196, 146, 0)
PURR_TEXT = (140, 96, 170)


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

        self.stats = Stats(data)
        self.mood = self.stats.mood(time.time())
        self.hud = StatusHud(self.stats)
        self.bowl = BowlWindow(data.get("bowl") or {}, self.area, self.on_bowl_filled)
        self.hovering = False

        # state machine
        self.state = "walk"        # walk | idle | sleep | eat | held | fall | hop
        self.goal = None           # None = wandering, "eat" = heading for the bowl
        self.facing = 1
        self.frame = 0
        self.t = 0
        self.timer_ticks = 0       # countdown used by idle / sleep / eat
        self.vy = 0.0
        self.floaters = []         # hearts and little texts drifting up

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

        self.next_move()

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
        self.goal = None
        self.state = "walk"

    def next_move(self):
        """After a rest: eat if hungry and there's food, otherwise wander."""
        if self.wants_food():
            self.go_eat()
        else:
            self.pick_target()

    def decide(self):
        """Reached a wander spot: nap, stand around or keep going."""
        if self.wants_food():
            self.go_eat()
            return
        energy = self.stats.energy
        if energy < TIRED_AT:
            self.start_sleep()
            return
        sleep = SLEEP_CHANCE + (1 - energy / 100) * 0.5
        idle = IDLE_CHANCE * (2 if self.mood in MOPEY else 1)
        r = random.random()
        if r < sleep:
            self.start_sleep()
        elif r < sleep + idle:
            self.start_idle()
        else:
            self.pick_target()

    def start_sleep(self):
        self.state = "sleep"
        need = (95 - self.stats.energy) / ENERGY_SLEEP_PER_S
        secs = max(random.uniform(SLEEP_MIN_S, SLEEP_MAX_S), min(need, SLEEP_LONGEST_S))
        self.timer_ticks = int(secs * 1000 / TICK_MS)
        if self.on_ground():
            self.y = self.ground_y("sleep")      # lying body sits a bit lower

    def start_idle(self):
        self.state = "idle"
        self.timer_ticks = int(random.uniform(1, 3) * 1000 / TICK_MS)

    def set_taskbar_only(self, value):
        self.taskbar_only = bool(value)
        if self.state in ("walk", "idle", "sleep"):
            self.next_move()

    # ---------- food ----------
    def wants_food(self):
        return self.bowl.full and self.stats.is_hungry()

    def on_bowl_filled(self):
        self.raise_()                            # stay drawn in front of the bowl
        if self.state in ("walk", "idle") and self.goal != "eat" and self.wants_food():
            self.go_eat()

    def go_eat(self):
        """Walk to the spot where the head ends up right over the bowl."""
        w = self.species.width
        head_x = self.species.head_for("eat")[0]
        bx = self.bowl.center_x()
        from_left = self.x + w / 2 < bx
        tx = bx - head_x if from_left else bx - (w - head_x)
        a = self.area()
        self.tx = min(max(tx, a.x()), a.x() + a.width() - w)
        self.ty = self.ground_y()
        self.goal = "eat"
        self.state = "walk"

    def start_eat(self):
        self.goal = None
        if not self.bowl.full:
            self.pick_target()
            return
        self.state = "eat"
        self.facing = 1 if self.bowl.center_x() > self.x + self.species.width / 2 else -1
        self.timer_ticks = int(EAT_S * 1000 / TICK_MS)

    def finish_eat(self):
        if self.bowl.full:
            self.bowl.empty()
            ev = self.stats.feed(time.time())
            self.spawn_hearts()
            self.react(ev)
        self.start_idle()

    # ---------- affection ----------
    def react(self, ev, purr=False):
        """Floating texts for coins earned, purring and level-ups."""
        texts = []
        if purr:
            texts.append(("prr", PURR_TEXT))
        if ev.get("coins"):
            texts.append((f"+{ev['coins']}", COIN_TEXT))
        if ev.get("level_up"):
            texts.append((f"{ev['level_up']}!", HEART))
        for i, (text, color) in enumerate(texts):
            self.spawn_text(text, color, delay=i * 14)
        self.mood = self.stats.mood(time.time())

    def petted(self):
        self.times_petted += 1
        ev = self.stats.pet(time.time())
        self.spawn_hearts(5 if self.stats.has(1) else 3)
        if ev["rewarded"]:
            self.react(ev, purr=self.stats.has(2))
        if self.stats.has(3) and self.state in ("walk", "idle") and self.on_ground():
            self.state = "hop"
            self.vy = -HOP_SPEED

    def maybe_gift(self):
        if not self.stats.has(4) or self.state not in ("walk", "idle"):
            return
        if random.random() < (TICK_MS / 1000) / GIFT_EVERY_S:
            self.stats.add_coins(GIFT_COINS)
            self.spawn_text("gift!", HEART)
            self.spawn_text(f"+{GIFT_COINS}", COIN_TEXT, delay=14)

    # ------------------------------------------------------------------
    def tick(self):
        self.t += 1
        now = time.time()
        self.stats.update(now, sleeping=(self.state == "sleep"))
        if self.t % 30 == 0:
            self.mood = self.stats.mood(now)

        if self.state == "walk":
            dx, dy = self.tx - self.x, self.ty - self.y
            dist = math.hypot(dx, dy)
            speed = self.species.walk_speed * MOOD_SPEED.get(self.mood, 1.0)
            if dist <= speed:
                self.x, self.y = self.tx, self.ty
                if self.goal == "eat":
                    self.start_eat()
                else:
                    self.decide()
            else:
                self.x += dx / dist * speed
                self.y += dy / dist * speed
                if abs(dx) > 1:
                    self.facing = 1 if dx > 0 else -1
                if self.t % 6 == 0:
                    self.frame = (self.frame + 1) % 4

        elif self.state in ("idle", "sleep"):
            self.timer_ticks -= 1
            if self.timer_ticks <= 0:
                self.next_move()

        elif self.state == "eat":
            self.timer_ticks -= 1
            if self.timer_ticks <= 0:
                self.finish_eat()

        elif self.state in ("fall", "hop"):
            self.vy = min(self.vy + GRAVITY, MAX_FALL_SPEED)
            self.y += self.vy
            ground = self.ground_y()
            if self.y >= ground:
                self.y = ground
                self.vy = 0
                self.start_idle()                # brief pause after landing

        # "held": position is controlled by the mouse

        self.maybe_gift()
        self.update_floaters()
        self.move(int(self.x), int(self.y))
        self.update_hud()
        self.update()

    # ------------------------------------------------------------------
    # status panel on hover
    # ------------------------------------------------------------------
    def enterEvent(self, e):
        self.hovering = True

    def leaveEvent(self, e):
        self.hovering = False

    def update_hud(self):
        if self.hovering and self.state != "held":
            self.hud.follow(self.x + self.species.width / 2, self.y + PAD_TOP, self.area())
            if not self.hud.isVisible():
                self.hud.show()
            elif self.t % 10 == 0:
                self.hud.update()
        elif self.hud.isVisible():
            self.hud.hide()

    # ------------------------------------------------------------------
    # hearts and floating texts
    # ------------------------------------------------------------------
    def spawn_hearts(self, n=3):
        hx, hy = self.species.head_for(self.state)
        if self.facing < 0:
            hx = self.species.width - hx
        for i in range(n):
            self.floaters.append({
                "kind": "heart",
                "x": hx + random.uniform(-14, 14),
                "y": PAD_TOP + hy - 10 + random.uniform(-4, 4),
                "age": -i * 5,           # negative age = delayed start
                "life": 45,
                "size": random.uniform(5, 8),
            })

    def spawn_text(self, text, color, delay=0):
        _hx, hy = self.species.head_for(self.state)
        self.floaters.append({
            "kind": "text",
            "text": text,
            "color": color,
            "x": self.species.width / 2,
            "y": PAD_TOP + hy - 20,
            "age": -delay,
            "life": 55,
        })

    def update_floaters(self):
        for f in self.floaters:
            f["age"] += 1
            if f["age"] > 0:
                if f["kind"] == "heart":
                    f["y"] -= 1.1
                    f["x"] += math.sin(f["age"] * 0.2) * 0.6
                else:
                    f["y"] -= 0.7
        self.floaters = [f for f in self.floaters if f["age"] < f["life"]]

    def paint_floaters(self, p):
        p.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        for f in self.floaters:
            if f["age"] < 0:
                continue
            alpha = int(255 * (1 - f["age"] / f["life"]))
            if f["kind"] == "text":
                p.setPen(QColor(*f["color"], alpha))
                p.drawText(QRectF(f["x"] - 55, f["y"] - 10, 110, 20),
                           Qt.AlignmentFlag.AlignCenter, f["text"])
                continue
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(*HEART, alpha))
            s, cx, cy = f["size"], f["x"], f["y"]
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
        pose = "idle" if self.state == "hop" else self.state
        self.species.paint(p, pose, self.facing, self.t, self.frame)
        p.restore()
        self.paint_floaters(p)
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
            self.goal = None
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
            self.petted()
        self._press_pos = None
        self._dragging = False

    def show_menu(self, global_pos):
        menu = QMenu(self)
        fill = menu.addAction("Fill food bowl")
        fill.setEnabled(not self.bowl.full)
        fill.triggered.connect(self.bowl.fill)
        coins = menu.addAction(f"Coins: {self.stats.coins}")
        coins.setEnabled(False)
        menu.addSeparator()
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
            "stats": self.stats.to_dict(time.time()),
            "bowl": self.bowl.to_dict(),
        })
        savemod.save(self.data)
