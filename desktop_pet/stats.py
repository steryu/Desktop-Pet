"""Pet needs and progress: fullness, energy, affection, coins and mood.

Plain numbers only (no Qt), so they save, load and test on their own.
A neglected pet gets sad, never harmed: needs stop at FLOOR and affection
only ever goes up.
"""
import time

# ---------- settings you can tweak ----------
FULLNESS_PER_S = 20 / 3600         # food drops 20 points an hour
ENERGY_DRAIN_PER_S = 100 / 5400    # awake: empty after 90 minutes
ENERGY_SLEEP_PER_S = 1.5           # napping recovers fast
BED_BONUS = 2                      # ...and twice as fast in the pet bed (deluxe bed: 3)
OFFLINE_REST_PER_S = 100 / 1800    # app closed: fully rested after 30 minutes
OFFLINE_CAP_S = 8 * 3600           # a long absence counts as at most 8 hours
ONLINE_GAP_S = 60                  # bigger gaps while running (laptop slept) count as offline
FLOOR = 10                         # needs never drop below this
HUNGRY_AT = 70                     # eats from the bowl below this
MEAL = 45
FEED_COINS = 3
FEED_AFFECTION = 3
PET_COOLDOWN_S = 3                 # petting faster than this earns nothing extra
PET_COINS_PER_DAY = 20
PLAY_COOLDOWN_S = 8
PLAY_AFFECTION = 1
PLAY_ENERGY = 2                    # every kick of the ball tires it a little
PLAY_COINS_PER_DAY = 15
DAILY_BONUS = 10                   # first launch of the day
DAILY_STREAK_STEP = 2              # +2 more for each day in a row...
DAILY_STREAK_MAX = 5               # ...up to +10
RECENT_PET_S = 600                 # petting and playing cheer it up for 10 minutes

# (affection needed, name); reaching a level unlocks UNLOCKS[level]
LEVELS = [
    (0, "Stranger"),
    (15, "Acquaintance"),
    (50, "Friend"),
    (120, "Best friend"),
    (250, "Soulmate"),
]
UNLOCKS = {
    1: "More hearts",
    2: "Purring",
    3: "Happy hop",
    4: "Gifts",
}
# --------------------------------------------


def _day(now):
    return time.strftime("%Y-%m-%d", time.localtime(now))


def _clamp(v):
    return max(FLOOR, min(100.0, v))


class Stats:
    def __init__(self, data, now=None):
        now = time.time() if now is None else now
        s = data.get("stats") or {}
        self.fullness = float(s.get("fullness", 70))
        self.energy = float(s.get("energy", 100))
        self.affection = int(s.get("affection", 0))
        self.coins = int(s.get("coins", 0))
        self.pet_coin_day = s.get("pet_coin_day", "")
        self.pet_coins_today = int(s.get("pet_coins_today", 0))
        self.play_coin_day = s.get("play_coin_day", "")
        self.play_coins_today = int(s.get("play_coins_today", 0))
        self.bonus_day = s.get("bonus_day", "")
        self.streak = int(s.get("streak", 0))
        self._last_reward = None
        self._last_play_reward = None
        self._recent_pets = []
        self._last_update = now
        self.away_s = 0                    # how long the app was closed
        if s.get("last_seen") is not None:
            self.away_s = max(0.0, now - float(s["last_seen"]))
            self.catch_up(self.away_s)

    # ------------------------------------------------------------------
    # time passing
    # ------------------------------------------------------------------
    def update(self, now, sleeping, in_bed=False, bed_bonus=BED_BONUS):
        dt = now - self._last_update
        self._last_update = now
        if dt > ONLINE_GAP_S:
            self.catch_up(dt)
        elif dt > 0:
            self.fullness = _clamp(self.fullness - FULLNESS_PER_S * dt)
            if sleeping:
                rate = ENERGY_SLEEP_PER_S * (bed_bonus if in_bed else 1)
                self.energy = _clamp(self.energy + rate * dt)
            else:
                self.energy = _clamp(self.energy - ENERGY_DRAIN_PER_S * dt)

    def catch_up(self, elapsed):
        e = min(max(elapsed, 0), OFFLINE_CAP_S)
        self.fullness = _clamp(self.fullness - FULLNESS_PER_S * e)
        self.energy = _clamp(self.energy + OFFLINE_REST_PER_S * e)

    # ------------------------------------------------------------------
    # care actions; each returns what happened so the pet can react
    # ------------------------------------------------------------------
    def pet(self, now):
        ev = {"rewarded": False, "coins": 0, "level_up": None}
        if self._last_reward is not None and now - self._last_reward < PET_COOLDOWN_S:
            return ev
        self._last_reward = now
        self._recent_pets.append(now)
        before = self.level()
        self.affection += 1
        if self.pet_coin_day != _day(now):
            self.pet_coin_day, self.pet_coins_today = _day(now), 0
        if self.pet_coins_today < PET_COINS_PER_DAY:
            self.pet_coins_today += 1
            self.coins += 1
            ev["coins"] = 1
        ev["rewarded"] = True
        ev["level_up"] = self._level_up(before)
        return ev

    def feed(self, now, meal=MEAL, love=FEED_AFFECTION):
        """Ate a bowl of food (kibble by default; store food is bigger)."""
        before = self.level()
        self.fullness = min(100.0, self.fullness + meal)
        self.affection += love
        self.coins += FEED_COINS
        return {"coins": FEED_COINS, "level_up": self._level_up(before)}

    def snack(self, now, food, love):
        """A treat from your hand: no coins, it's already a reward."""
        before = self.level()
        self.fullness = min(100.0, self.fullness + food)
        self.affection += love
        self._recent_pets.append(now)
        return {"coins": 0, "level_up": self._level_up(before)}

    def play(self, now):
        """The pet kicked its ball."""
        ev = {"rewarded": False, "coins": 0, "level_up": None}
        self.energy = _clamp(self.energy - PLAY_ENERGY)
        if self._last_play_reward is not None and now - self._last_play_reward < PLAY_COOLDOWN_S:
            return ev
        self._last_play_reward = now
        self._recent_pets.append(now)
        before = self.level()
        self.affection += PLAY_AFFECTION
        if self.play_coin_day != _day(now):
            self.play_coin_day, self.play_coins_today = _day(now), 0
        if self.play_coins_today < PLAY_COINS_PER_DAY:
            self.play_coins_today += 1
            self.coins += 1
            ev["coins"] = 1
        ev["rewarded"] = True
        ev["level_up"] = self._level_up(before)
        return ev

    def daily_bonus(self, now):
        """Coins for the first visit of the day (0 if already collected).
        Coming back on consecutive days grows the bonus."""
        today = _day(now)
        if self.bonus_day == today:
            return 0
        self.streak = self.streak + 1 if self.bonus_day == _day(now - 86400) else 1
        self.bonus_day = today
        coins = DAILY_BONUS + DAILY_STREAK_STEP * min(self.streak - 1, DAILY_STREAK_MAX)
        self.coins += coins
        return coins

    def add_coins(self, n):
        self.coins += n

    def spend(self, n):
        if n > self.coins:
            return False
        self.coins -= n
        return True

    def is_hungry(self):
        return self.fullness < HUNGRY_AT

    # ------------------------------------------------------------------
    # affection levels
    # ------------------------------------------------------------------
    def level(self):
        lvl = 0
        for i, (need, _name) in enumerate(LEVELS):
            if self.affection >= need:
                lvl = i
        return lvl

    def level_name(self):
        return LEVELS[self.level()][1]

    def has(self, level):
        return self.level() >= level

    def level_progress(self):
        lvl = self.level()
        if lvl == len(LEVELS) - 1:
            return 1.0
        lo, hi = LEVELS[lvl][0], LEVELS[lvl + 1][0]
        return (self.affection - lo) / (hi - lo)

    def next_unlock(self):
        """(affection needed, unlock name) for the next level, or None at max."""
        lvl = self.level() + 1
        if lvl >= len(LEVELS):
            return None
        return LEVELS[lvl][0], UNLOCKS[lvl]

    def _level_up(self, before):
        return self.level_name() if self.level() > before else None

    # ------------------------------------------------------------------
    def mood(self, now):
        """sad | hungry | tired | content | happy"""
        if self.fullness < 30 and self.energy < 30:
            return "sad"
        if self.fullness < 30:
            return "hungry"
        if self.energy < 25:
            return "tired"
        self._recent_pets = [t for t in self._recent_pets if now - t < RECENT_PET_S]
        score = (self.fullness + self.energy) / 2 + min(20, 5 * len(self._recent_pets))
        if score >= 80:
            return "happy"
        if score >= 50:
            return "content"
        return "sad"

    def to_dict(self, now):
        return {
            "fullness": round(self.fullness, 2),
            "energy": round(self.energy, 2),
            "affection": self.affection,
            "coins": self.coins,
            "pet_coin_day": self.pet_coin_day,
            "pet_coins_today": self.pet_coins_today,
            "play_coin_day": self.play_coin_day,
            "play_coins_today": self.play_coins_today,
            "bonus_day": self.bonus_day,
            "streak": self.streak,
            "last_seen": now,
        }
