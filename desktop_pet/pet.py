import math
import random
import time

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QFont, QGuiApplication, QPainter, QPainterPath
from PySide6.QtWidgets import QApplication, QMenu, QWidget

import accessories
import desktop_windows
import paths
import personality
import save as savemod
import screens
import store
from bubble import SpeechBubble
from butterfly import Butterfly
from furniture import Home
from hud import StatusHud
from sounds import Sounds
from species import get_species
from stats import ENERGY_SLEEP_PER_S, Stats

# ---------- settings you can tweak ----------
TICK_MS = 33              # ~30 fps
GRAVITY = 1.0             # falling acceleration (pixels / tick^2)
MAX_FALL_SPEED = 30
DRAG_THRESHOLD = 5        # pixels the mouse must move before a click becomes a drag
SLEEP_CHANCE = 0.15       # base chance to nap after reaching a spot, rises as energy drops
TIRED_AT = 25             # below this energy it always naps at the next stop
BED_AT = 70               # naps below this energy are taken in the bed
IDLE_CHANCE = 0.30        # chance to sit, groom, stretch... after reaching a spot
PLAY_CHANCE = 0.15        # chance to go and play with a toy after reaching a spot
PLAY_MIN_ENERGY = 35      # too tired to play below this
KICKS = (2, 4)            # kicks per play session
RUN = 1.8                 # speed multiplier while chasing something
GIVE_UP_S = {"toy": 8, "cursor": 5, "butterfly": 15}
SLEEP_MIN_S, SLEEP_MAX_S = 6, 20
SLEEP_LONGEST_S = 60      # longest nap in daytime; longer at night
EAT_S = 4
HOP_SPEED = 7             # "Happy hop" unlock
GIFT_EVERY_S = 900        # "Gifts" unlock: on average one gift per 15 awake minutes
GIFT_COINS = 5
AUTOSAVE_MS = 15000
PAD_TOP = 44              # empty space above the pet, room for hearts
MOOD_SPEED = {"happy": 1.2, "sad": 0.6, "tired": 0.6, "hungry": 0.8}
MOPEY = ("sad", "tired", "hungry")
# mouse
LOOK_RANGE = 260          # eyes follow the cursor within this distance
TURN_RANGE = 180          # an idle pet turns round to face a cursor this close behind it
WIGGLE_SPEED = 18         # cursor pixels per tick that count as "wiggling"
WIGGLE_TICKS = 5          # wiggle this long near the pet and it gives chase
CHASE_RANGE = 320
POUNCE_RANGE = 160        # pounces at things at most this far above its head
# windows
PERCH_CHANCE = 0.12       # chance to jump onto a window after reaching a spot
LEAVE_PERCH_CHANCE = 0.3  # chance to jump back down after reaching a spot up there
MAX_JUMP = 500            # highest window top it can jump to (pixels above the ground)
EDGE_MARGIN = 10          # how close to a window's end it can stand
# talking and events
TALK_GAP_S = 30           # minimum gap between things it says by itself
NEEDS_TALK_S = 120        # how often it mentions being hungry / tired / sad
EVENT_EVERY_S = 300       # on average one random event per 5 awake minutes (daytime)
# --------------------------------------------

HEART = (235, 64, 98)
COIN_TEXT = (196, 146, 0)
PURR_TEXT = (140, 96, 170)
AIRBORNE = ("fall", "hop", "jump")
FURNITURE_GOALS = ("eat", "bed", "toy")


class PetWindow(QWidget):
    def __init__(self, species, data):
        super().__init__()
        self._positioned = False
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
        self.climb = bool(data.get("climb_windows", True))
        self.speech = bool(data.get("speech", True))
        self.times_petted = int(data.get("times_petted", 0))
        self.sprite_pack = data.get("sprite_pack")       # None = the built-in drawing
        self.sounds = Sounds(paths.data_dir(), enabled=bool(data.get("sound", True)),
                             volume=float(data.get("volume", 0.5)))
        self.hidden = False
        self.tray = None                                 # set by main when there's a tray
        self.settings_window = None

        self.stats = Stats(data)
        self.mood = self.stats.mood(time.time())
        self.hud = StatusHud(self.stats)
        self.bubble = SpeechBubble()
        self.inventory = store.Inventory(data)
        self.store_window = None
        self.home = Home(data, self.area, self.on_furniture)
        self.resolve_furniture()
        self.toy = None            # the toy it's playing with
        self.sleep_bed = None      # the bed it's sleeping in
        self.hovering = False

        # state machine
        self.state = "walk"        # walk | idle | sleep | eat | held | fall | hop | jump
        self.goal = None           # None = wandering, else heading for something (see goal_x)
        self.goal_side = 1         # approach the goal from the left (1) or right (-1)
        self.goal_tx = 0.0         # fixed target x for "zoom" / "edge" / "perch"
        self.chase_ticks = 0
        self.play_left = 0         # kicks left in this play session
        self.pounces_left = 0      # pounces left at the butterfly
        self.zoom_left = 0         # dashes left in a fit of zoomies
        self.in_bed = False
        self.idle_anim = "stand"   # what it does while idle: stand | sit | groom | ...
        self.look = None           # where the eyes point (dx, dy), or None
        self.facing = 1
        self.frame = 0
        self.t = 0
        self.timer_ticks = 0       # countdown used by idle / sleep / eat
        self.vx = self.vy = 0.0
        self.floaters = []         # hearts and little texts drifting up

        # other windows to sit on
        self.perches = []          # visible window tops, see desktop_windows.perches
        self.perch = None          # the one it's on, or None for the ground
        self.perch_target = None   # the one it's walking under to jump onto
        self.leaving = None        # id of the window it's jumping off (don't land back on it)

        # mouse, talking, events
        self.cursor_prev = QCursor.pos()
        self.cursor_xy = (0, 0)
        self.wiggle = 0
        self.cursor_still = 0
        self.last_talk = 0.0
        self.last_needs_talk = time.time()
        self.night_said = False
        self.butterflies = []

        # position (top-left of the window, as floats), on whichever screen it was saved on
        sx, sy = data.get("x"), data.get("y")
        if sx is None or sy is None:
            a = QGuiApplication.primaryScreen().availableGeometry()
            sx = random.uniform(a.x(), a.x() + a.width() - species.width)
            sy = a.y() + a.height() - PAD_TOP - species.feet_y
        self.x, self.y = float(sx), float(sy)
        self._positioned = True
        a = self.area()
        self.x = min(max(float(sx), a.x()), a.x() + a.width() - species.width)
        self.y = min(max(float(sy), a.y() - PAD_TOP), self.ground_y())
        if self.y < self.ground_y() - 2:
            self.state = "fall"    # saved up on a window: drop and land wherever it can
        self.tx, self.ty = self.x, self.y
        self.move(int(self.x), int(self.y))

        # mouse handling
        self._press_pos = None
        self._grab_offset = None
        self._dragging = False

        self.refresh_perches()
        if self.state != "fall":
            self.next_move()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(TICK_MS)

        self.autosave = QTimer(self)
        self.autosave.timeout.connect(self.save_state)
        self.autosave.start(AUTOSAVE_MS)

        QTimer.singleShot(1500, self.greet)

    # ------------------------------------------------------------------
    # geometry helpers
    # ------------------------------------------------------------------
    def area(self):
        """Usable area (excludes the taskbar) of the screen the pet is on."""
        if not self._positioned:                 # still in __init__
            return QGuiApplication.primaryScreen().availableGeometry()
        return screens.area_at(self.center_x(), self.y + PAD_TOP + self.species.feet_y - 4)

    def floor_top(self):
        a = self.area()
        return a.y() + a.height()

    def ground_y(self, pose="walk"):
        """Window top-y at which the pet stands on top of the taskbar."""
        feet = self.species.sleep_feet_y if pose == "sleep" else self.species.feet_y
        return self.floor_top() - PAD_TOP - feet

    def surface_y(self, pose="walk"):
        """Like ground_y, but on top of the window it's perched on."""
        if self.perch is None:
            return self.ground_y(pose)
        feet = self.species.sleep_feet_y if pose == "sleep" else self.species.feet_y
        return self.perch["top"] - PAD_TOP - feet

    def feet(self):
        return self.y + PAD_TOP + self.species.feet_y

    def on_ground(self):
        return self.perch is None and abs(self.y - self.ground_y()) < 6

    def on_surface(self):
        return abs(self.y - self.surface_y()) < 6

    def center_x(self):
        return self.x + self.species.width / 2

    def clamp_x(self, x):
        a = self.area()
        return min(max(x, a.x()), a.x() + a.width() - self.species.width)

    def walk_range(self):
        """Window x range it can walk in: the whole screen, or along its perch."""
        w = self.species.width
        if self.perch is None:
            a = self.area()
            return a.x(), a.x() + a.width() - w
        return self.perch["x1"] + EDGE_MARGIN - w / 2, self.perch["x2"] - EDGE_MARGIN - w / 2

    def clamp_walk(self, x):
        lo, hi = self.walk_range()
        return min(max(x, lo), max(lo, hi))

    def head_pos(self):
        """Head position on screen."""
        hx, hy = self.species.head_for(self.pose())
        if self.facing < 0:
            hx = self.species.width - hx
        return self.x + hx, self.y + PAD_TOP + hy

    # ------------------------------------------------------------------
    # behaviour
    # ------------------------------------------------------------------
    def pick_target(self):
        lo, hi = self.walk_range()
        self.tx = random.uniform(lo, max(lo, hi))
        if self.taskbar_only or self.perch is not None:
            self.ty = self.surface_y()
        else:
            self.ty = random.uniform(self.area().y(), self.ground_y())
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
        """Reached a wander spot: nap, play, climb, sit about or keep going."""
        if self.wants_food():
            self.set_goal("eat")
            return
        energy = self.stats.energy
        if energy < TIRED_AT:
            self.go_sleep()
            return
        if self.perch is not None and random.random() < LEAVE_PERCH_CHANCE:
            self.set_goal("edge")
            return
        if random.random() < PLAY_CHANCE and self.go_play():
            return
        if random.random() < PERCH_CHANCE and self.go_perch():
            return
        sleep = (SLEEP_CHANCE + (1 - energy / 100) * 0.5) * self.sleepiness()
        idle = IDLE_CHANCE * (1.5 if self.mood in MOPEY else 1)
        r = random.random()
        if r < sleep:
            self.go_sleep()
        elif r < sleep + idle:
            self.start_idle(anim=None)
        else:
            self.pick_target()

    def start_idle(self, anim="stand"):
        """Stand around for a bit; anim=None picks sit / groom / stretch / yawn / look."""
        self.goal = None
        self.state = "idle"
        if anim is None:
            anim = personality.pick_idle(self.species.idle_anims, self.hour(), self.mood)
        self.idle_anim = anim
        lo, hi = self.species.idle_anims.get(anim, (1, 3))
        self.timer_ticks = int(random.uniform(lo, hi) * 1000 / TICK_MS)

    def set_taskbar_only(self, value):
        self.taskbar_only = bool(value)
        if self.state in ("walk", "idle", "sleep"):
            self.next_move()

    def set_climb(self, value):
        self.climb = bool(value)
        self.refresh_perches()

    def set_speech(self, value):
        self.speech = bool(value)
        if not self.speech:
            self.bubble.ticks_left = 0

    # ---------- walking to things ----------
    def goal_item(self):
        return {"eat": self.bowl, "bed": self.bed, "toy": self.toy}.get(self.goal)

    def goal_center(self):
        """Screen x of what it's heading for."""
        if self.goal in FURNITURE_GOALS:
            return self.goal_item().center_x()
        if self.goal == "cursor":
            return self.cursor_xy[0]
        if self.goal == "butterfly":
            return self.butterflies[0].center()[0]
        return self.goal_tx + self.species.width / 2

    def goal_x(self, side):
        """Window x that puts the right body part on the goal, approaching from side."""
        w = self.species.width
        if self.goal == "eat":                   # head over the bowl
            head_x = self.species.head_for("eat")[0]
            bx = self.bowl.center_x()
            return bx - head_x if side > 0 else bx - (w - head_x)
        if self.goal == "bed":                   # centred on the cushion
            return self.bed.center_x() - w / 2
        if self.goal == "toy":                   # nose touching it
            reach = self.species.reach_x
            if side > 0:
                return self.toy.fx - reach + 2
            return self.toy.fx + self.toy.W - (w - reach) - 2
        if self.goal in ("cursor", "butterfly"):  # nose right under it
            cx = self.goal_center()
            reach = self.species.reach_x
            return cx - reach if side > 0 else cx - (w - reach)
        return self.goal_tx

    def set_goal(self, goal):
        if self.perch is not None and goal in FURNITURE_GOALS:
            goal = "edge"                        # furniture is on the ground: get down first
        self.goal = goal
        if goal == "edge":                       # walk off the nearer end of the window
            p, cx = self.perch, self.center_x()
            end = p["x1"] + 4 if cx - p["x1"] < p["x2"] - cx else p["x2"] - 4
            self.goal_tx = end - self.species.width / 2
        side = 1 if self.center_x() < self.goal_center() else -1
        if goal == "eat" and self.clamp_x(self.goal_x(side)) != self.goal_x(side):
            side = -side                         # no room on that side (screen edge)
        self.goal_side = side
        self.chase_ticks = 0
        self.state = "walk"
        self.retarget()

    def retarget(self):
        """Things move (dragged, rolling, flying), so aim again every tick."""
        if self.goal in ("toy", "cursor", "butterfly"):    # follow it round
            self.goal_side = 1 if self.center_x() < self.goal_center() else -1
        tx = self.goal_x(self.goal_side)
        self.tx = self.clamp_x(tx) if self.goal in ("edge", "perch") else self.clamp_walk(tx)
        self.ty = self.surface_y()

    def arrive(self):
        goal, item = self.goal, self.goal_item()
        if goal is None:
            self.decide()
        elif goal == "toy":
            if item.on_ground() and not item.dragging:
                self.kick_toy()
            # else: it's in the air or in your hand, keep waiting under it
        elif goal in FURNITURE_GOALS and not item.resting():
            self.start_idle()                    # it's being carried around: think again
        elif goal == "eat":
            self.start_eat()
        elif goal == "bed":
            self.start_sleep(in_bed=True)
        elif goal == "cursor":
            cx, cy = self.cursor_xy
            if 0 <= self.head_pos()[1] - cy <= POUNCE_RANGE:
                self.pounce(cx, cy)
        elif goal == "butterfly":
            bx, by = self.butterflies[0].center()
            if 0 <= self.head_pos()[1] - by <= POUNCE_RANGE:
                self.butterflies[0].dodge()
                self.pounces_left -= 1
                self.pounce(bx, by)
        elif goal == "zoom":
            self.zoom_left -= 1
            if self.zoom_left > 0:
                lo, hi = self.walk_range()
                self.goal_tx = lo if self.x > (lo + hi) / 2 else hi
                self.set_goal("zoom")
            else:
                self.start_idle("sit")
        elif goal == "perch":
            self.jump_up()
        elif goal == "edge":
            self.jump_down()

    def on_furniture(self, event, item):
        """Something happened to a piece of furniture: "picked", "landed", "used" or "menu"."""
        self.raise_()                            # stay drawn in front of furniture
        if event == "menu":
            self.furniture_menu(item)
            return
        if event == "picked":
            if item is self.bowl and self.state == "eat":
                self.start_idle()
            elif item is self.sleep_bed and self.in_bed:
                self.leave_bed()                 # bed pulled out from under it
            return
        if self.state not in ("walk", "idle"):
            return
        if item is self.bowl and self.goal != "eat" and self.wants_food():
            self.set_goal("eat")
        elif getattr(item, "toy", False) and event == "used" and self.goal is None:
            self.go_play(item)

    # ---------- food ----------
    def wants_food(self):
        return self.bowl is not None and self.bowl.full and self.stats.is_hungry()

    def start_eat(self):
        self.goal = None
        if not self.bowl.full:
            self.pick_target()
            return
        self.state = "eat"
        self.sounds.play("munch")
        self.facing = 1 if self.bowl.center_x() > self.center_x() else -1
        self.timer_ticks = int(EAT_S * 1000 / TICK_MS)

    def finish_eat(self):
        if self.bowl.full:
            food, love = store.meal(self.bowl.food)
            self.bowl.empty()
            ev = self.stats.feed(time.time(), meal=food, love=love)
            self.spawn_hearts()
            self.react(ev)
        self.start_idle()

    # ---------- sleep ----------
    def hour(self):
        return time.localtime().tm_hour

    def sleepiness(self):
        return personality.sleepiness(self.hour())

    def go_sleep(self):
        if self.bed is not None and self.stats.energy < BED_AT:
            self.set_goal("bed")
        else:
            self.start_sleep()                   # right here, even on top of a window

    def start_sleep(self, in_bed=False):
        self.goal = None
        self.state = "sleep"
        self.in_bed = in_bed
        self.sleep_bed = self.bed if in_bed else None
        rate = ENERGY_SLEEP_PER_S * (self.bed.BONUS if in_bed else 1)
        need = (95 - self.stats.energy) / rate
        s = self.sleepiness()
        secs = max(random.uniform(SLEEP_MIN_S, SLEEP_MAX_S) * s, min(need, SLEEP_LONGEST_S * s))
        self.timer_ticks = int(secs * 1000 / TICK_MS)
        if in_bed:
            self.y = self.ground_y("sleep") - self.bed.LIFT
        elif self.on_surface():
            self.y = self.surface_y("sleep")     # lying body sits a bit lower

    def leave_bed(self):
        self.in_bed = False
        self.sleep_bed = None
        self.goal = None
        self.state = "fall"
        self.vy = 0

    # ---------- play ----------
    def go_play(self, toy=None):
        toys = self.home.toys()
        if not toys or self.stats.energy <= PLAY_MIN_ENERGY or self.perch is not None:
            return False
        self.toy = toy if toy in toys else random.choice(toys)
        self.play_left = random.randint(*KICKS)
        self.set_goal("toy")
        return True

    def kick_toy(self):
        self.facing = self.goal_side
        self.toy.kick(self.facing * random.uniform(*self.toy.KICK))
        self.sounds.play("kick")
        self.played()
        self.play_left -= 1
        if self.play_left > 0 and self.stats.energy > PLAY_MIN_ENERGY:
            self.set_goal("toy")                 # chase it again
        else:
            self.start_idle()

    def pounce(self, tx, ty):
        """Leap at something above (the cursor, a butterfly)."""
        hx, hy = self.head_pos()
        rise = max(20.0, hy - ty + 10)
        self.vy = -min(math.sqrt(2 * GRAVITY * rise), 13)
        self.vx = max(-4.0, min(4.0, (tx - hx) / 12))
        self.state = "hop"
        self.sounds.play("boing")
        self.played()

    def played(self):
        ev = self.stats.play(time.time())
        if ev["rewarded"]:
            self.spawn_hearts(2)
            self.react(ev)

    # ---------- windows ----------
    def refresh_perches(self):
        """Re-read where other windows are; follow the one it sits on, or fall if it's gone."""
        if not self.climb:
            self.perches = []
        else:
            a, w = self.area(), self.species.width
            scale = screens.screen_at(self.center_x(), self.feet()).devicePixelRatio()
            self.perches = desktop_windows.perches(
                desktop_windows.window_rects(scale),
                min_width=w + 2 * EDGE_MARGIN,
                min_top=a.y() + self.species.height,
                max_top=self.floor_top() - 60,
                x_range=(a.x(), a.x() + a.width()))      # windows on this screen only
        if self.perch is None:
            return
        old = self.perch
        dx = 0.0
        same = [p for p in self.perches if p["id"] == old["id"]]
        if same:
            dx = same[0]["left"] - old["left"]
        cx = self.center_x() + dx
        here = [p for p in same if p["x1"] + EDGE_MARGIN <= cx <= p["x2"] - EDGE_MARGIN]
        if not here:                             # window closed, moved away or covered
            self.perch = None
            if self.state not in AIRBORNE + ("held",):
                self.in_bed = False
                self.goal = None
                self.state = "fall"
                self.vy = 0
            return
        self.perch = here[0]
        self.x += dx
        self.tx += dx
        if self.state in ("idle", "walk", "eat"):
            self.y = self.surface_y()
        elif self.state == "sleep":
            self.y = self.surface_y("sleep")
        self.ty = self.surface_y()

    def go_perch(self):
        if not self.climb or self.perch is not None or not self.on_ground():
            return False
        floor = self.floor_top()
        options = [p for p in self.perches if floor - p["top"] <= MAX_JUMP]
        if not options:
            return False
        p = random.choice(options)
        self.perch_target = p
        lo, hi = p["x1"] + 2 * EDGE_MARGIN, p["x2"] - 2 * EDGE_MARGIN
        self.goal_tx = min(max(self.center_x(), lo), hi) - self.species.width / 2
        self.set_goal("perch")
        return True

    def jump_up(self):
        t = self.perch_target
        live = [p for p in self.perches if p["id"] == t["id"]
                and p["x1"] + EDGE_MARGIN <= self.center_x() <= p["x2"] - EDGE_MARGIN]
        if not live:
            self.start_idle()                    # that window moved or closed
            return
        rise = self.feet() - live[0]["top"] + 30
        self.vy = -math.sqrt(2 * GRAVITY * rise)
        self.sounds.play("boing")
        self.vx = 0.0
        self.goal = None
        self.state = "jump"

    def jump_down(self):
        self.facing = 1 if self.center_x() > (self.perch["x1"] + self.perch["x2"]) / 2 else -1
        self.leaving = self.perch["id"]
        self.perch = None
        self.vx = self.facing * 3.5
        self.vy = -6.0
        self.goal = None
        self.state = "jump"

    def landing(self, prev_feet, feet):
        """What it lands on while falling from prev_feet to feet: a perch, None
        (the ground) or False (still in the air)."""
        cx = self.center_x()
        best = None
        for p in self.perches:
            if (p["id"] != self.leaving and p["x1"] + EDGE_MARGIN <= cx <= p["x2"] - EDGE_MARGIN
                    and prev_feet <= p["top"] + 1 and feet >= p["top"]
                    and (best is None or p["top"] < best["top"])):
                best = p
        if best is not None:
            return best
        return None if feet >= self.floor_top() else False

    def airborne(self):
        prev = self.feet()
        self.vy = min(self.vy + GRAVITY, MAX_FALL_SPEED)
        self.x = self.clamp_x(self.x + self.vx)
        self.y += self.vy
        if self.vy <= 0:
            return
        where = self.landing(prev, self.feet())
        if where is False:
            return
        jumped = self.state == "jump"
        if self.vy > 12:
            self.sounds.play("thud")             # a proper drop, not a little hop
        self.leaving = None
        self.perch = where
        self.y = self.surface_y()
        self.vx = self.vy = 0.0
        if self.pounces_left > 0 and self.butterflies:
            self.set_goal("butterfly")           # keep after it
            return
        self.start_idle()
        if jumped and where is not None and random.random() < 0.4:
            self.say("perch")

    # ---------- affection ----------
    def react(self, ev, purr=False):
        """Floating texts for coins earned, purring and level-ups."""
        texts = []
        if purr:
            texts.append(("prr", PURR_TEXT))
        if ev.get("coins"):
            texts.append((f"+{ev['coins']}", COIN_TEXT))
            self.sounds.play("coin")
        if ev.get("level_up"):
            texts.append((f"{ev['level_up']}!", HEART))
            self.say("level_up", force=True)
        for i, (text, color) in enumerate(texts):
            self.spawn_text(text, color, delay=i * 14)
        self.mood = self.stats.mood(time.time())

    def petted(self):
        self.times_petted += 1
        ev = self.stats.pet(time.time())
        self.spawn_hearts(5 if self.stats.has(1) else 3)
        self.sounds.play("pop")
        if ev["rewarded"]:
            self.react(ev, purr=self.stats.has(2))
            if self.stats.has(2):
                self.sounds.play("purr")
            if random.random() < 0.25:
                self.say(self.mood, force=True)
        if self.stats.has(3) and self.state in ("walk", "idle") and self.on_surface():
            self.goal = None
            self.state = "hop"
            self.vx, self.vy = 0.0, -HOP_SPEED
            self.sounds.play("boing")

    def maybe_gift(self):
        if not self.stats.has(4) or self.state not in ("walk", "idle"):
            return
        if random.random() < (TICK_MS / 1000) / GIFT_EVERY_S:
            self.stats.add_coins(GIFT_COINS)
            self.sounds.play("coin")
            self.spawn_text("gift!", HEART)
            self.spawn_text(f"+{GIFT_COINS}", COIN_TEXT, delay=14)

    # ------------------------------------------------------------------
    # talking
    # ------------------------------------------------------------------
    def say(self, kind, force=False):
        now = time.time()
        if not self.speech or (not force and now - self.last_talk < TALK_GAP_S):
            return
        self.bubble.say(personality.line(kind))
        self.last_talk = now
        if random.random() < 0.4:
            self.sounds.play("meow")

    def greet(self):
        away = self.stats.away_s
        if away > 8 * 3600:
            self.say("greet_long", force=True)
        elif away > 3600:
            self.say("greet", force=True)
        self.collect_bonus()

    def collect_bonus(self):
        """First visit of the day pays a bonus (checked again when the date changes)."""
        coins = self.stats.daily_bonus(time.time())
        if coins:
            self.sounds.play("coin")
            self.spawn_text(f"+{coins}", COIN_TEXT, delay=20)
            self.spawn_text("daily bonus", COIN_TEXT, delay=34)

    def chatter(self, now):
        """Every so often, mention how it feels; and notice when it gets late."""
        if self.state == "sleep":
            return
        night = personality.is_night(self.hour())
        if night and not self.night_said:
            self.night_said = True
            self.say("night")
        elif not night:
            self.night_said = False
        if self.t % 900 == 0:
            self.collect_bonus()                 # left running past midnight
        if now - self.last_needs_talk < NEEDS_TALK_S:
            return
        self.last_needs_talk = now
        if self.mood == "hungry" or (self.stats.is_hungry() and self.bowl is not None and not self.bowl.full):
            self.say("hungry")
        elif self.mood in ("tired", "sad"):
            self.say(self.mood)

    # ------------------------------------------------------------------
    # random events
    # ------------------------------------------------------------------
    def maybe_event(self):
        if self.state not in ("walk", "idle") or self.goal is not None or self.butterflies:
            return
        if random.random() < (TICK_MS / 1000) / (EVENT_EVERY_S * self.sleepiness()):
            self.run_event(personality.pick_event())

    def run_event(self, name):
        if name == "butterfly":
            if self.perch is not None:
                return                           # it flies low, over the ground
            here = self.area()
            b = Butterfly(lambda: here)          # stays on this screen
            b.show()
            self.butterflies.append(b)
            self.pounces_left = 3
            self.set_goal("butterfly")
        elif name == "zoomies":
            lo, hi = self.walk_range()
            self.goal_tx = lo if self.x > (lo + hi) / 2 else hi
            self.zoom_left = 4
            self.set_goal("zoom")
        elif name == "coin":
            self.stats.add_coins(2)
            self.sounds.play("coin")
            self.spawn_text("+2", COIN_TEXT)
        elif name == "sneeze":
            if self.on_surface():
                self.goal = None
                self.state = "hop"
                self.vx, self.vy = 0.0, -4.0
        self.say(name, force=True)

    def tick_butterflies(self):
        for b in list(self.butterflies):
            b.tick()
            if b.gone():
                b.close()
                self.butterflies.remove(b)
        if self.goal == "butterfly" and (not self.butterflies or self.pounces_left <= 0):
            self.pounces_left = 0
            self.start_idle("sit")

    # ------------------------------------------------------------------
    # the mouse cursor
    # ------------------------------------------------------------------
    def watch_cursor(self):
        cur = QCursor.pos()
        speed = math.hypot(cur.x() - self.cursor_prev.x(), cur.y() - self.cursor_prev.y())
        self.cursor_prev = cur
        self.cursor_xy = (cur.x(), cur.y())
        self.cursor_still = self.cursor_still + 1 if speed < 2 else 0

        hx, hy = self.head_pos()
        dx, dy = cur.x() - hx, cur.y() - hy
        dist = math.hypot(dx, dy)
        near = dist < CHASE_RANGE
        self.wiggle = self.wiggle + 1 if (speed > WIGGLE_SPEED and near) else max(0, self.wiggle - 1)

        awake = self.state in ("walk", "idle")
        if awake and dist < LOOK_RANGE and self._press_pos is None:
            if (self.state == "idle" and self.idle_anim in ("stand", "sit", "look")
                    and dist < TURN_RANGE and dx * self.facing < -20):
                self.facing = -self.facing       # turn round to see you
            self.look = (dx / max(dist, 1) * self.facing, dy / max(dist, 1))
        else:
            self.look = None

        if (self.wiggle >= WIGGLE_TICKS and awake and self.goal is None
                and self.stats.energy > PLAY_MIN_ENERGY and self.on_surface()):
            self.set_goal("cursor")              # a wiggling cursor is irresistible
        elif self.goal == "cursor" and self.cursor_still > 45:
            self.start_idle("sit")               # it stopped moving: lost interest

    # ------------------------------------------------------------------
    def tick(self):
        self.t += 1
        now = time.time()
        if self.hidden:                          # tucked away in the tray: time still passes
            self.stats.update(now, sleeping=True)
            return
        self.home.tick()
        bonus = self.sleep_bed.BONUS if self.sleep_bed is not None else 1
        self.stats.update(now, sleeping=(self.state == "sleep"), in_bed=self.in_bed, bed_bonus=bonus)
        if self.t % 30 == 0:
            self.mood = self.stats.mood(now)
            self.chatter(now)
        if self.t % (6 if self.perch is not None else 30) == 0:
            self.refresh_perches()
        self.watch_cursor()
        self.tick_butterflies()

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

        elif self.state in AIRBORNE:
            self.airborne()

        # "held": position is controlled by the mouse

        self.maybe_gift()
        self.maybe_event()
        self.update_floaters()
        self.move(int(self.x), int(self.y))
        self.update_hud()
        self.update_bubble()
        self.update()

    def walk(self):
        speed = self.species.walk_speed * MOOD_SPEED.get(self.mood, 1.0)
        if self.goal:
            self.chase_ticks += 1
            if self.goal in GIVE_UP_S:
                speed *= RUN
                if self.chase_ticks > GIVE_UP_S[self.goal] * 1000 / TICK_MS:
                    self.pounces_left = 0
                    self.start_idle()            # it got away
                    return
            elif self.goal == "zoom":
                speed = self.species.walk_speed * RUN * 1.5
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
        if self.t % (3 if speed > self.species.walk_speed * 1.5 else 6) == 0:
            self.frame = (self.frame + 1) % 4

    # ------------------------------------------------------------------
    # status panel on hover, speech bubble
    # ------------------------------------------------------------------
    def enterEvent(self, e):
        self.hovering = True

    def leaveEvent(self, e):
        self.hovering = False

    def update_hud(self):
        if self.hovering and self.state != "held":
            self.hud.follow(self.center_x(), self.y + PAD_TOP, self.area())
            if not self.hud.isVisible():
                self.hud.show()
            elif self.t % 10 == 0:
                self.hud.update()
        elif self.hud.isVisible():
            self.hud.hide()

    def update_bubble(self):
        self.bubble.tick()
        if self.bubble.speaking() and not self.hud.isVisible():
            hx, hy = self.head_pos()
            self.bubble.follow(hx, hy - 26, self.area())
            if not self.bubble.isVisible():
                self.bubble.show()
        elif self.bubble.isVisible():
            self.bubble.hide()

    # ------------------------------------------------------------------
    # hearts and floating texts
    # ------------------------------------------------------------------
    def spawn_hearts(self, n=3):
        hx, hy = self.species.head_for(self.pose())
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
        _hx, hy = self.species.head_for(self.pose())
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
    def pose(self):
        """What the species should draw for the current state."""
        if self.state == "idle":
            return "idle" if self.idle_anim == "stand" else self.idle_anim
        if self.state in ("hop", "jump"):
            return "idle"
        return self.state

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.save()
        p.translate(0, PAD_TOP)
        self.species.paint(p, self.pose(), self.facing, self.t, self.frame, look=self.look)
        if self.inventory.worn:
            if self.facing < 0:
                p.translate(self.species.width, 0)
                p.scale(-1, 1)
            accessories.paint(p, self.inventory.worn, self.species, self.pose())
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
            self.perch = None
            self.vx = self.vy = 0.0
            if random.random() < 0.35:
                self.say("held", force=True)
        if self._dragging:
            top_left = cur - self._grab_offset
            self.x, self.y = float(top_left.x()), float(top_left.y())
            self.move(int(self.x), int(self.y))

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton or self._press_pos is None:
            return
        if self._dragging:
            self.state = "fall"                  # let go -> gravity takes over, lands on
            self.vx = self.vy = 0.0              # a window top if it's dropped above one
            self.refresh_perches()
        else:
            self.petted()
        self._press_pos = None
        self._dragging = False

    def show_menu(self, global_pos):
        menu = QMenu(self)
        menu.addAction(f"Store…   🪙 {self.stats.coins}").triggered.connect(self.open_store)
        treats = self.inventory.food.get("treat", 0)
        if treats:
            menu.addAction(f"Give a treat (× {treats})").triggered.connect(self.give_treat)
        if self.bowl is not None:
            self.add_fill_actions(menu)
        menu.addSeparator()
        for label, value, slot in (("Walk on surfaces only", self.taskbar_only, self.set_taskbar_only),
                                   ("Climb on windows", self.climb, self.set_climb),
                                   ("Speech bubbles", self.speech, self.set_speech)):
            act = menu.addAction(label)
            act.setCheckable(True)
            act.setChecked(value)
            act.toggled.connect(slot)
        menu.addSeparator()
        menu.addAction("Settings…").triggered.connect(self.open_settings)
        if self.tray is not None:
            menu.addAction("Hide (find me in the tray)").triggered.connect(lambda: self.set_hidden(True))
        menu.addAction("Quit").triggered.connect(QApplication.quit)
        menu.exec(global_pos)

    def add_fill_actions(self, menu):
        if self.bowl.full:
            menu.addAction("Food bowl is full").setEnabled(False)
            return
        meals = {k: n for k, n in self.inventory.food.items() if store.ITEMS[k]["kind"] == "meal"}
        if not meals:
            menu.addAction("Fill food bowl").triggered.connect(lambda: self.fill_bowl("kibble"))
            return
        sub = menu.addMenu("Fill food bowl")
        sub.addAction("Kibble (free)").triggered.connect(lambda: self.fill_bowl("kibble"))
        for k, n in meals.items():
            it = store.ITEMS[k]
            sub.addAction(f"{it['icon']} {it['name']} (× {n})").triggered.connect(
                lambda _=False, food=k: self.fill_bowl(food))

    def furniture_menu(self, item):
        menu = QMenu()
        if item is self.bowl:
            self.add_fill_actions(menu)
            menu.addSeparator()
        menu.addAction("Put away").triggered.connect(lambda: self.put_away(item.kind))
        menu.addAction("Store…").triggered.connect(self.open_store)
        menu.exec(QCursor.pos())

    # ------------------------------------------------------------------
    # settings (the settings window, tray and menus call these)
    # ------------------------------------------------------------------
    def open_settings(self):
        from settings_window import SettingsWindow  # only built when first opened
        if self.settings_window is None:
            self.settings_window = SettingsWindow(self)
        self.settings_window.sync()
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def set_hidden(self, hidden):
        self.hidden = bool(hidden)
        windows = [self] + self.home.items + self.butterflies
        for w in windows:
            w.setVisible(not self.hidden)
        if self.hidden:
            self.hud.hide()
            self.bubble.hide()
            self.bubble.ticks_left = 0
        else:
            self.raise_()
            if self.state == "held":
                self.state = "fall"

    def set_sound(self, on):
        self.sounds.set_enabled(on)

    def set_volume(self, v):
        self.sounds.set_volume(v)

    def set_art(self, pack):
        """Switch between the built-in drawing (None) and a sprite pack."""
        species = get_species(self.data.get("species", "cat"), pack, paths.sprite_folders())
        self.sprite_pack = pack if getattr(species, "pack", None) == pack else None
        self.species = species
        self.setFixedSize(species.width, species.height + PAD_TOP)
        self.goal = None
        self.in_bed = False
        self.perch = None
        self.state, self.vx, self.vy = "fall", 0.0, 0.0   # settle onto the ground again

    # ------------------------------------------------------------------
    # store actions (the store window and menus call these)
    # ------------------------------------------------------------------
    def open_store(self):
        from store_window import StoreWindow       # only built when first opened
        if self.store_window is None:
            self.store_window = StoreWindow(self)
        else:
            self.store_window.rebuild()
        self.store_window.show()
        self.store_window.raise_()
        self.store_window.activateWindow()

    def buy(self, item_id):
        if not self.inventory.buy(item_id, self.stats, self.species.name):
            return False
        self.sounds.play("coin")
        kind = store.ITEMS[item_id]["kind"]
        if kind == "furniture":
            self.place(item_id)
        elif kind == "wear":
            self.inventory.wear(item_id)
        self.spawn_hearts()
        self.say("gift", force=True)
        return True

    def resolve_furniture(self):
        self.bowl = self.home.first("bowl")
        self.bed = self.home.best_bed()

    def place(self, kind):
        if kind in self.inventory.owned and self.home.add(kind) is not None:
            self.resolve_furniture()
            self.raise_()

    def put_away(self, kind):
        item = self.home.first(kind)
        if item is None:
            return
        if self.goal_item() is item:
            self.start_idle()
        if item is self.sleep_bed and self.in_bed:
            self.leave_bed()
        if item is self.bowl and self.state == "eat":
            self.start_idle()
        if item is self.toy:
            self.toy = None
        self.home.remove(kind)
        self.resolve_furniture()

    def wear(self, item_id):
        if self.inventory.wear(item_id):
            self.spawn_hearts(2)

    def take_off(self, slot):
        self.inventory.take_off(slot)

    def give_treat(self):
        if self.state == "held" or not self.inventory.use_food("treat"):
            return
        it = store.ITEMS["treat"]
        ev = self.stats.snack(time.time(), food=it["food"], love=it["love"])
        self.sounds.play("munch")
        self.spawn_hearts(4)
        self.react(ev)
        self.say("treat", force=True)

    def fill_bowl(self, food="kibble"):
        if self.bowl is None or self.bowl.full:
            return
        if food != "kibble" and not self.inventory.use_food(food):
            return
        self.bowl.fill(food)

    # ------------------------------------------------------------------
    def save_state(self):
        self.data.pop("bowl", None)              # pre-furniture saves kept it here
        self.data.update({
            "species": self.species.name,
            "taskbar_only": self.taskbar_only,
            "climb_windows": self.climb,
            "speech": self.speech,
            "sound": self.sounds.enabled,
            "volume": round(self.sounds.volume, 2),
            "sprite_pack": self.sprite_pack,
            "x": int(self.x),
            "y": int(self.y),
            "times_petted": self.times_petted,
            "stats": self.stats.to_dict(time.time()),
            "furniture": self.home.to_list(),
            "inventory": self.inventory.to_dict(),
        })
        savemod.save(self.data)
