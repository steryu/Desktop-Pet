import math
import random
import time

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPainterPath
from PySide6.QtWidgets import QApplication, QMenu, QWidget

import save as savemod
from furniture import Home
from hud import StatusHud
from stats import BED_BONUS, ENERGY_SLEEP_PER_S, Stats

# ---------- settings you can tweak ----------
TICK_MS = 33              # ~30 fps
GRAVITY = 1.0             # falling acceleration (pixels / tick^2)
MAX_FALL_SPEED = 30
DRAG_THRESHOLD = 5        # pixels the mouse must move before a click becomes a drag
SLEEP_CHANCE = 0.15       # base chance to nap after reaching a spot, rises as energy drops
TIRED_AT = 25             # below this energy it always naps at the next stop
BED_AT = 70               # naps below this energy are taken in the bed
IDLE_CHANCE = 0.20        # chance to just stand around for a moment
PLAY_CHANCE = 0.15        # chance to go and play with the ball after reaching a spot
PLAY_MIN_ENERGY = 35      # too tired to play below this
KICKS = (2, 4)            # kicks per play session
RUN = 1.8                 # speed multiplier while chasing the ball
CHASE_GIVE_UP_S = 8
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
        self.home = Home(data, self.area, self.on_furniture)
        self.bowl = self.home.first("bowl")
        self.bed = self.home.first("bed")
        self.ball = self.home.first("ball")
        self.hovering = False

        # state machine
        self.state = "walk"        # walk | idle | sleep | eat | held | fall | hop
        self.goal = None           # None = wandering, else heading for: "eat" | "bed" | "ball"
        self.goal_side = 1         # approach the goal from the left (1) or right (-1)
        self.chase_ticks = 0
        self.play_left = 0         # kicks left in this play session
        self.in_bed = False
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

    def clamp_x(self, x):
        a = self.area()
        return min(max(x, a.x()), a.x() + a.width() - self.species.width)

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
        """After a rest: eat if hungry and there's food, nap if exhausted, else wander."""
        self.in_bed = False
        if self.wants_food():
            self.set_goal("eat")
        elif self.stats.energy < TIRED_AT:
            self.go_sleep()
        else:
            self.pick_target()

    def decide(self):
        """Reached a wander spot: nap, play, stand around or keep going."""
        if self.wants_food():
            self.set_goal("eat")
            return
        energy = self.stats.energy
        if energy < TIRED_AT:
            self.go_sleep()
            return
        if random.random() < PLAY_CHANCE and self.go_play():
            return
        sleep = SLEEP_CHANCE + (1 - energy / 100) * 0.5
        idle = IDLE_CHANCE * (2 if self.mood in MOPEY else 1)
        r = random.random()
        if r < sleep:
            self.go_sleep()
        elif r < sleep + idle:
            self.start_idle()
        else:
            self.pick_target()

    def start_idle(self):
        self.goal = None
        self.state = "idle"
        self.timer_ticks = int(random.uniform(1, 3) * 1000 / TICK_MS)

    def set_taskbar_only(self, value):
        self.taskbar_only = bool(value)
        if self.state in ("walk", "idle", "sleep"):
            self.next_move()

    # ---------- walking to furniture ----------
    def goal_item(self):
        return {"eat": self.bowl, "bed": self.bed, "ball": self.ball}.get(self.goal)

    def goal_x(self, side):
        """Window x that puts the right body part on the goal, approaching from side."""
        w = self.species.width
        if self.goal == "eat":                   # head over the bowl
            head_x = self.species.head_for("eat")[0]
            bx = self.bowl.center_x()
            return bx - head_x if side > 0 else bx - (w - head_x)
        if self.goal == "bed":                   # centred on the cushion
            return self.bed.center_x() - w / 2
        reach = self.species.reach_x             # ball: nose touching it
        if side > 0:
            return self.ball.fx - reach + 2
        return self.ball.fx + self.ball.W - (w - reach) - 2

    def set_goal(self, goal):
        self.goal = goal
        side = 1 if self.x + self.species.width / 2 < self.goal_item().center_x() else -1
        if self.clamp_x(self.goal_x(side)) != self.goal_x(side):
            side = -side                         # no room on that side (screen edge)
        self.goal_side = side
        self.chase_ticks = 0
        self.state = "walk"
        self.retarget()

    def retarget(self):
        """Furniture can move (dragged, rolling), so aim again every tick."""
        if self.goal == "ball":                  # the ball rolls past: follow it round
            w = self.species.width
            self.goal_side = 1 if self.x + w / 2 < self.ball.center_x() else -1
        self.tx = self.clamp_x(self.goal_x(self.goal_side))
        self.ty = self.ground_y()

    def arrive(self):
        goal, item = self.goal, self.goal_item()
        if goal is None:
            self.decide()
        elif goal == "ball":
            if item.on_ground() and not item.dragging:
                self.kick_ball()
            # else: it's in the air or in your hand, keep waiting under it
        elif not item.resting():
            self.start_idle()                    # it's being carried around: think again
        elif goal == "eat":
            self.start_eat()
        elif goal == "bed":
            self.start_sleep(in_bed=True)

    def on_furniture(self, event, item):
        """Something happened to a piece of furniture: "picked", "landed" or "used"."""
        self.raise_()                            # stay drawn in front of furniture
        if event == "picked":
            if item is self.bowl and self.state == "eat":
                self.start_idle()
            elif item is self.bed and self.in_bed:
                self.in_bed = False              # bed pulled out from under it
                self.state = "fall"
                self.vy = 0
            return
        if self.state not in ("walk", "idle"):
            return
        if item is self.bowl and self.goal != "eat" and self.wants_food():
            self.set_goal("eat")
        elif item is self.ball and event == "used" and self.goal is None:
            self.go_play()

    # ---------- food ----------
    def wants_food(self):
        return self.bowl is not None and self.bowl.full and self.stats.is_hungry()

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

    # ---------- sleep ----------
    def go_sleep(self):
        if self.bed is not None and self.stats.energy < BED_AT:
            self.set_goal("bed")
        else:
            self.start_sleep()

    def start_sleep(self, in_bed=False):
        self.goal = None
        self.state = "sleep"
        self.in_bed = in_bed
        rate = ENERGY_SLEEP_PER_S * (BED_BONUS if in_bed else 1)
        need = (95 - self.stats.energy) / rate
        secs = max(random.uniform(SLEEP_MIN_S, SLEEP_MAX_S), min(need, SLEEP_LONGEST_S))
        self.timer_ticks = int(secs * 1000 / TICK_MS)
        if in_bed:
            self.y = self.ground_y("sleep") - self.bed.LIFT
        elif self.on_ground():
            self.y = self.ground_y("sleep")      # lying body sits a bit lower

    # ---------- play ----------
    def go_play(self):
        if self.ball is None or self.stats.energy <= PLAY_MIN_ENERGY:
            return False
        self.play_left = random.randint(*KICKS)
        self.set_goal("ball")
        return True

    def kick_ball(self):
        self.facing = self.goal_side
        self.ball.kick(self.facing * random.uniform(5, 9))
        ev = self.stats.play(time.time())
        if ev["rewarded"]:
            self.spawn_hearts(2)
            self.react(ev)
        self.play_left -= 1
        if self.play_left > 0 and self.stats.energy > PLAY_MIN_ENERGY:
            self.set_goal("ball")                # chase it again
        else:
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
            self.goal = None
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
        self.home.tick()
        self.stats.update(now, sleeping=(self.state == "sleep"), in_bed=self.in_bed)
        if self.t % 30 == 0:
            self.mood = self.stats.mood(now)

        if self.state == "walk":
            self.walk()

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

    def walk(self):
        speed = self.species.walk_speed * MOOD_SPEED.get(self.mood, 1.0)
        if self.goal:
            self.chase_ticks += 1
            if self.goal == "ball":
                speed *= RUN
                if self.chase_ticks > CHASE_GIVE_UP_S * 1000 / TICK_MS:
                    self.start_idle()            # it got away
                    return
            self.retarget()
        dx, dy = self.tx - self.x, self.ty - self.y
        dist = math.hypot(dx, dy)
        if dist <= speed:
            self.x, self.y = self.tx, self.ty
            self.arrive()
            return
        self.x += dx / dist * speed
        self.y += dy / dist * speed
        if abs(dx) > 1:
            self.facing = 1 if dx > 0 else -1
        if self.t % (3 if self.goal == "ball" else 6) == 0:
            self.frame = (self.frame + 1) % 4

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
            self.in_bed = False
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
        if self.bowl is not None:
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
        self.data.pop("bowl", None)              # pre-furniture saves kept it here
        self.data.update({
            "species": self.species.name,
            "taskbar_only": self.taskbar_only,
            "x": int(self.x),
            "y": int(self.y),
            "times_petted": self.times_petted,
            "stats": self.stats.to_dict(time.time()),
            "furniture": self.home.to_list(),
        })
        savemod.save(self.data)
