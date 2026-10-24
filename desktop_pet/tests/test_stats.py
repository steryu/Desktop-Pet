import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import stats as st  # noqa: E402

T0 = time.mktime((2026, 10, 24, 12, 0, 0, 0, 0, -1))   # local noon, a fixed day


def fresh(**over):
    s = st.Stats({}, now=T0)
    for k, v in over.items():
        setattr(s, k, v)
    return s


class Decay(unittest.TestCase):
    def test_awake_hour_drains_food_and_energy(self):
        s = fresh(fullness=100.0, energy=100.0)
        for i in range(1, 3601):
            s.update(T0 + i, sleeping=False)
        self.assertAlmostEqual(s.fullness, 100 - st.FULLNESS_PER_S * 3600, places=3)
        self.assertAlmostEqual(s.energy, 100 - st.ENERGY_DRAIN_PER_S * 3600, places=3)

    def test_sleep_recovers_energy(self):
        s = fresh(energy=20.0)
        s.update(T0 + 10, sleeping=True)
        self.assertAlmostEqual(s.energy, 20 + st.ENERGY_SLEEP_PER_S * 10, places=3)

    def test_bed_recovers_faster(self):
        s = fresh(energy=20.0)
        s.update(T0 + 10, sleeping=True, in_bed=True)
        self.assertAlmostEqual(s.energy, 20 + st.ENERGY_SLEEP_PER_S * st.BED_BONUS * 10, places=3)

    def test_needs_never_drop_below_floor(self):
        s = fresh(fullness=st.FLOOR + 1, energy=st.FLOOR + 1)
        s.update(T0 + 50, sleeping=False)
        for i in range(2, 2000):
            s.update(T0 + 50 * i, sleeping=False)
        self.assertEqual(s.fullness, st.FLOOR)
        self.assertEqual(s.energy, st.FLOOR)

    def test_values_capped_at_100(self):
        s = fresh(energy=99.0)
        s.update(T0 + 30, sleeping=True)
        self.assertEqual(s.energy, 100)


class Offline(unittest.TestCase):
    def data_seen(self, hours_ago, fullness=100.0, energy=40.0):
        return {"stats": {"fullness": fullness, "energy": energy,
                          "last_seen": T0 - hours_ago * 3600}}

    def test_short_absence_applies_decay_and_rest(self):
        s = st.Stats(self.data_seen(1), now=T0)
        self.assertAlmostEqual(s.fullness, 100 - st.FULLNESS_PER_S * 3600, places=3)
        self.assertEqual(s.energy, 100)          # it napped while you were away

    def test_long_absence_is_capped(self):
        a = st.Stats(self.data_seen(st.OFFLINE_CAP_S / 3600, fullness=100), now=T0)
        b = st.Stats(self.data_seen(24 * 30, fullness=100), now=T0)
        self.assertEqual(a.fullness, b.fullness)
        self.assertGreaterEqual(b.fullness, st.FLOOR)

    def test_big_gap_while_running_counts_as_offline(self):
        # e.g. the laptop slept: no energy drain for the whole gap
        s = fresh(fullness=100.0, energy=50.0)
        s.update(T0 + 3 * 3600, sleeping=False)
        self.assertEqual(s.energy, 100)

    def test_clock_going_backwards_is_harmless(self):
        s = st.Stats(self.data_seen(-5), now=T0)
        self.assertEqual(s.fullness, 100)


class Petting(unittest.TestCase):
    def test_first_pet_rewards(self):
        s = fresh()
        ev = s.pet(T0)
        self.assertTrue(ev["rewarded"])
        self.assertEqual((s.affection, s.coins, ev["coins"]), (1, 1, 1))

    def test_cooldown_blocks_spam(self):
        s = fresh()
        s.pet(T0)
        ev = s.pet(T0 + 1)
        self.assertFalse(ev["rewarded"])
        self.assertEqual((s.affection, s.coins), (1, 1))
        s.pet(T0 + st.PET_COOLDOWN_S)
        self.assertEqual((s.affection, s.coins), (2, 2))

    def test_daily_coin_cap_but_affection_keeps_growing(self):
        s = fresh()
        for i in range(st.PET_COINS_PER_DAY + 5):
            s.pet(T0 + i * st.PET_COOLDOWN_S)
        self.assertEqual(s.coins, st.PET_COINS_PER_DAY)
        self.assertEqual(s.affection, st.PET_COINS_PER_DAY + 5)

    def test_coin_cap_resets_next_day(self):
        s = fresh()
        for i in range(st.PET_COINS_PER_DAY):
            s.pet(T0 + i * st.PET_COOLDOWN_S)
        s.pet(T0 + 86400)
        self.assertEqual(s.coins, st.PET_COINS_PER_DAY + 1)

    def test_level_up_reported_once(self):
        s = fresh(affection=st.LEVELS[1][0] - 1)
        ev = s.pet(T0)
        self.assertEqual(ev["level_up"], st.LEVELS[1][1])
        self.assertIsNone(s.pet(T0 + st.PET_COOLDOWN_S)["level_up"])


class Feeding(unittest.TestCase):
    def test_feed_fills_and_rewards(self):
        s = fresh(fullness=40.0)
        ev = s.feed(T0)
        self.assertEqual(s.fullness, 40 + st.MEAL)
        self.assertEqual((s.coins, ev["coins"]), (st.FEED_COINS, st.FEED_COINS))
        self.assertEqual(s.affection, st.FEED_AFFECTION)

    def test_feed_caps_at_100(self):
        s = fresh(fullness=90.0)
        s.feed(T0)
        self.assertEqual(s.fullness, 100)

    def test_hungry_threshold(self):
        self.assertTrue(fresh(fullness=st.HUNGRY_AT - 1).is_hungry())
        self.assertFalse(fresh(fullness=st.HUNGRY_AT).is_hungry())


class Playing(unittest.TestCase):
    def test_play_rewards_affection_and_costs_energy(self):
        s = fresh(energy=80.0)
        ev = s.play(T0)
        self.assertTrue(ev["rewarded"])
        self.assertEqual(s.affection, st.PLAY_AFFECTION)
        self.assertAlmostEqual(s.energy, 80 - st.PLAY_ENERGY)

    def test_play_cooldown_still_tires(self):
        s = fresh(energy=80.0)
        s.play(T0)
        ev = s.play(T0 + 1)
        self.assertFalse(ev["rewarded"])
        self.assertEqual(s.affection, st.PLAY_AFFECTION)
        self.assertAlmostEqual(s.energy, 80 - 2 * st.PLAY_ENERGY)

    def test_play_cheers_up(self):
        s = fresh(fullness=75.0, energy=75.0 + 4 * st.PLAY_ENERGY)
        for i in range(4):
            s.play(T0 + i * st.PLAY_COOLDOWN_S)
        self.assertEqual(s.mood(T0 + 60), "happy")

    def test_play_level_up(self):
        s = fresh(affection=st.LEVELS[1][0] - 1)
        self.assertEqual(s.play(T0)["level_up"], st.LEVELS[1][1])


class Levels(unittest.TestCase):
    def test_level_and_progress(self):
        s = fresh(affection=0)
        self.assertEqual((s.level(), s.level_name()), (0, st.LEVELS[0][1]))
        lo, hi = st.LEVELS[1][0], st.LEVELS[2][0]
        s.affection = (lo + hi) // 2
        self.assertEqual(s.level(), 1)
        self.assertAlmostEqual(s.level_progress(), (s.affection - lo) / (hi - lo))

    def test_max_level(self):
        s = fresh(affection=10 ** 6)
        self.assertEqual(s.level(), len(st.LEVELS) - 1)
        self.assertEqual(s.level_progress(), 1.0)
        self.assertIsNone(s.next_unlock())

    def test_next_unlock(self):
        s = fresh(affection=0)
        need, name = s.next_unlock()
        self.assertEqual(need, st.LEVELS[1][0])
        self.assertEqual(name, st.UNLOCKS[1])


class Mood(unittest.TestCase):
    def test_moods(self):
        self.assertEqual(fresh(fullness=20.0, energy=20.0).mood(T0), "sad")
        self.assertEqual(fresh(fullness=20.0, energy=90.0).mood(T0), "hungry")
        self.assertEqual(fresh(fullness=90.0, energy=15.0).mood(T0), "tired")
        self.assertEqual(fresh(fullness=60.0, energy=60.0).mood(T0), "content")
        self.assertEqual(fresh(fullness=40.0, energy=40.0).mood(T0), "sad")

    def test_petting_cheers_up(self):
        s = fresh(fullness=75.0, energy=75.0)
        self.assertEqual(s.mood(T0), "content")
        for i in range(4):
            s.pet(T0 + i * st.PET_COOLDOWN_S)
        self.assertEqual(s.mood(T0 + 20), "happy")
        self.assertEqual(s.mood(T0 + 3600), "content")   # the glow wears off


class Persistence(unittest.TestCase):
    def test_roundtrip(self):
        s = fresh(fullness=55.5, energy=66.0, affection=42, coins=7)
        s.pet(T0)
        d = {"stats": s.to_dict(T0)}
        r = st.Stats(d, now=T0)
        for k in ("fullness", "energy", "affection", "coins", "pet_coins_today", "pet_coin_day"):
            self.assertEqual(getattr(r, k), getattr(s, k), k)


if __name__ == "__main__":
    unittest.main()
