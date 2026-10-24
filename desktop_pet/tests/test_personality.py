import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import desktop_windows as dw  # noqa: E402
import personality as pe  # noqa: E402
import stats as st  # noqa: E402


class Perches(unittest.TestCase):
    def test_single_window(self):
        p = dw.perches([(1, 100, 300, 600, 700)], min_width=100, min_top=50, max_top=900)
        self.assertEqual(p, [{"id": 1, "left": 100, "x1": 100, "x2": 600, "top": 300}])

    def test_front_window_hides_part_of_top_edge(self):
        rects = [(2, 250, 200, 400, 500),          # in front, covers y=300 between 250..400
                 (1, 100, 300, 600, 700)]
        p = dw.perches(rects, min_width=100, min_top=50, max_top=900)
        mine = [(s["x1"], s["x2"]) for s in p if s["id"] == 1]
        self.assertEqual(mine, [(100, 250), (400, 600)])
        self.assertTrue(all(s["left"] == 100 for s in p if s["id"] == 1))

    def test_front_window_below_edge_does_not_hide_it(self):
        rects = [(2, 0, 400, 1000, 800), (1, 100, 300, 600, 700)]
        p = dw.perches(rects, min_width=100, min_top=50, max_top=900)
        self.assertIn((100, 600), [(s["x1"], s["x2"]) for s in p if s["id"] == 1])

    def test_too_narrow_or_too_high_or_low_is_skipped(self):
        rects = [(1, 0, 300, 80, 600), (2, 0, 10, 900, 600), (3, 0, 950, 900, 1000)]
        self.assertEqual(dw.perches(rects, min_width=100, min_top=50, max_top=900), [])

    def test_maximized_window_hides_everything_behind(self):
        rects = [(1, 0, 33, 1728, 1117), (2, 519, 148, 1209, 772)]
        self.assertEqual(dw.perches(rects, min_width=140, min_top=120, max_top=900), [])


class TimeOfDay(unittest.TestCase):
    def test_sleepier_at_night(self):
        self.assertGreater(pe.sleepiness(2), pe.sleepiness(23))
        self.assertGreater(pe.sleepiness(23), pe.sleepiness(21))
        self.assertGreater(pe.sleepiness(21), pe.sleepiness(14))
        self.assertEqual(pe.sleepiness(14), 1.0)

    def test_is_night(self):
        self.assertTrue(pe.is_night(23) and pe.is_night(3))
        self.assertFalse(pe.is_night(7) or pe.is_night(12) or pe.is_night(21))


class Lines(unittest.TestCase):
    def test_every_kind_has_lines(self):
        for kind, lines in pe.LINES.items():
            self.assertTrue(lines, kind)
            self.assertTrue(all(len(s) <= 28 for s in lines), kind)   # fits a small bubble

    def test_every_mood_has_a_line(self):
        for mood in ("happy", "content", "sad", "hungry", "tired"):
            self.assertIn(pe.line(mood, random.Random(1)), pe.LINES[mood])

    def test_every_event_has_a_line(self):
        for ev in pe.EVENTS:
            self.assertIn(ev, pe.LINES)


class Picking(unittest.TestCase):
    def test_pick_event_follows_weights(self):
        rng = random.Random(3)
        counts = {k: 0 for k in pe.EVENTS}
        for _ in range(4000):
            counts[pe.pick_event(rng)] += 1
        total = sum(pe.EVENTS.values())
        for k, w in pe.EVENTS.items():
            self.assertAlmostEqual(counts[k] / 4000, w / total, delta=0.04)

    def test_pick_idle_only_offers_what_the_species_has(self):
        rng = random.Random(5)
        seen = {pe.pick_idle(["sit"], 12, "content", rng) for _ in range(200)}
        self.assertEqual(seen, {"stand", "sit"})

    def test_more_yawns_at_night(self):
        anims = ["sit", "groom", "stretch", "yawn", "look"]
        rng = random.Random(9)
        day = sum(pe.pick_idle(anims, 13, "content", rng) == "yawn" for _ in range(3000))
        night = sum(pe.pick_idle(anims, 2, "content", rng) == "yawn" for _ in range(3000))
        self.assertGreater(night, day * 1.8)


class Away(unittest.TestCase):
    def test_away_time_recorded(self):
        s = st.Stats({"stats": {"last_seen": 1000.0}}, now=1000.0 + 7200)
        self.assertEqual(s.away_s, 7200)
        self.assertEqual(st.Stats({}, now=5.0).away_s, 0)


if __name__ == "__main__":
    unittest.main()
