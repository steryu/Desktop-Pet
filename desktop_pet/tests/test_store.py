import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import stats as st  # noqa: E402
import store  # noqa: E402

T0 = time.mktime((2026, 10, 24, 12, 0, 0, 0, 0, -1))
DAY = 86400


def rich(coins=1000):
    s = st.Stats({}, now=T0)
    s.coins = coins
    return s


class Catalog(unittest.TestCase):
    def test_every_item_is_complete(self):
        for iid, it in store.ITEMS.items():
            for field in ("name", "category", "price", "icon", "desc", "kind"):
                self.assertIn(field, it, f"{iid}.{field}")
            self.assertIn(it["category"], store.CATEGORIES, iid)
            self.assertIn(it["kind"], ("snack", "meal", "furniture", "wear"), iid)
            self.assertGreater(it["price"], 0, iid)
            if it["kind"] in ("snack", "meal"):
                self.assertGreater(it["food"], 0, iid)
            if it["kind"] == "wear":
                self.assertIn(it["slot"], ("hat", "collar"), iid)

    def test_items_have_code_behind_them(self):
        import accessories
        import furniture
        for iid, it in store.ITEMS.items():
            if it["kind"] == "furniture":
                self.assertIn(iid, furniture.KINDS, iid)
                self.assertEqual(furniture.KINDS[iid].kind, iid)
            if it["kind"] == "wear":
                drawings = accessories.HATS if it["slot"] == "hat" else accessories.COLLARS
                self.assertIn(iid, drawings, iid)
        for kind in store.DEFAULT_OWNED:
            self.assertIn(kind, furniture.KINDS)

    def test_every_category_has_items(self):
        for cat in store.CATEGORIES:
            self.assertTrue(store.in_category(cat), cat)

    def test_bigger_meals_cost_more(self):
        meals = sorted((it["price"], it["food"]) for it in store.ITEMS.values() if it["kind"] == "meal")
        self.assertEqual(meals, sorted(meals, key=lambda m: m[1]))

    def test_kibble_is_the_free_default_meal(self):
        self.assertEqual(store.meal("kibble"), (st.MEAL, st.FEED_AFFECTION))
        self.assertEqual(store.meal("fish"), (store.ITEMS["fish"]["food"], store.ITEMS["fish"]["love"]))
        self.assertEqual(store.meal(None), (st.MEAL, st.FEED_AFFECTION))


class Buying(unittest.TestCase):
    def test_buy_food_stacks_and_costs(self):
        inv, s = store.Inventory({}), rich(100)
        self.assertTrue(inv.buy("fish", s, "cat"))
        self.assertTrue(inv.buy("fish", s, "cat"))
        self.assertEqual(inv.food["fish"], 2)
        self.assertEqual(s.coins, 100 - 2 * store.ITEMS["fish"]["price"])

    def test_cannot_afford(self):
        inv, s = store.Inventory({}), rich(1)
        ok, why = inv.can_buy("crown", s.coins, "cat")
        self.assertFalse(ok)
        self.assertIn("coins", why)
        self.assertFalse(inv.buy("crown", s, "cat"))
        self.assertEqual(s.coins, 1)

    def test_furniture_and_wearables_are_bought_once(self):
        inv, s = store.Inventory({}), rich()
        self.assertTrue(inv.buy("yarn", s, "cat"))
        self.assertFalse(inv.can_buy("yarn", s.coins, "cat")[0])
        self.assertFalse(inv.can_buy("bed", s.coins, "cat")[0])      # owned from the start
        self.assertTrue(inv.buy("crown", s, "cat"))
        self.assertFalse(inv.buy("crown", s, "cat"))

    def test_species_restriction(self):
        inv = store.Inventory({})
        ok, why = inv.can_buy("bell_collar", 1000, "dragon")
        self.assertFalse(ok)
        self.assertTrue(inv.can_buy("bell_collar", 1000, "cat")[0])

    def test_unknown_item(self):
        self.assertFalse(store.Inventory({}).can_buy("spaceship", 10 ** 6, "cat")[0])


class Using(unittest.TestCase):
    def test_use_food(self):
        inv, s = store.Inventory({}), rich()
        inv.buy("treat", s, "cat")
        self.assertTrue(inv.use_food("treat"))
        self.assertFalse(inv.use_food("treat"))
        self.assertNotIn("treat", inv.food)

    def test_wear_replaces_same_slot(self):
        inv, s = store.Inventory({}), rich()
        inv.buy("party_hat", s, "cat")
        inv.buy("crown", s, "cat")
        inv.buy("red_collar", s, "cat")
        self.assertTrue(inv.wear("party_hat"))
        self.assertTrue(inv.wear("red_collar"))
        self.assertTrue(inv.wear("crown"))
        self.assertEqual(inv.worn, {"hat": "crown", "collar": "red_collar"})
        inv.take_off("hat")
        self.assertEqual(inv.worn, {"collar": "red_collar"})

    def test_cannot_wear_what_you_do_not_own(self):
        self.assertFalse(store.Inventory({}).wear("crown"))


class Saving(unittest.TestCase):
    def test_defaults_and_migration(self):
        self.assertEqual(store.Inventory({}).owned, store.DEFAULT_OWNED)
        old = {"furniture": [{"kind": "bowl"}, {"kind": "ball"}]}
        self.assertTrue(set(store.DEFAULT_OWNED) <= set(store.Inventory(old).owned))

    def test_roundtrip(self):
        inv, s = store.Inventory({}), rich()
        inv.buy("fish", s, "cat")
        inv.buy("crown", s, "cat")
        inv.wear("crown")
        again = store.Inventory({"inventory": inv.to_dict()})
        self.assertEqual((again.food, again.owned, again.worn), (inv.food, inv.owned, inv.worn))


class CoinSources(unittest.TestCase):
    def test_spend(self):
        s = rich(10)
        self.assertFalse(s.spend(11))
        self.assertTrue(s.spend(10))
        self.assertEqual(s.coins, 0)

    def test_daily_bonus_once_a_day(self):
        s = rich(0)
        self.assertEqual(s.daily_bonus(T0), st.DAILY_BONUS)
        self.assertEqual(s.daily_bonus(T0 + 3600), 0)
        self.assertEqual(s.coins, st.DAILY_BONUS)

    def test_daily_bonus_streak_grows_and_caps(self):
        s = rich(0)
        got = [s.daily_bonus(T0 + d * DAY) for d in range(10)]
        step, cap = st.DAILY_STREAK_STEP, st.DAILY_STREAK_MAX
        self.assertEqual(got[:3], [st.DAILY_BONUS, st.DAILY_BONUS + step, st.DAILY_BONUS + 2 * step])
        self.assertEqual(got[-1], st.DAILY_BONUS + cap * step)

    def test_missing_a_day_resets_streak(self):
        s = rich(0)
        s.daily_bonus(T0)
        s.daily_bonus(T0 + DAY)
        self.assertEqual(s.daily_bonus(T0 + 3 * DAY), st.DAILY_BONUS)

    def test_bonus_state_is_saved(self):
        s = rich(0)
        s.daily_bonus(T0)
        r = st.Stats({"stats": s.to_dict(T0)}, now=T0)
        self.assertEqual(r.daily_bonus(T0 + 60), 0)

    def test_play_earns_coins_with_daily_cap(self):
        s = rich(0)
        s.energy = 100.0
        for i in range(st.PLAY_COINS_PER_DAY + 5):
            s.energy = 100.0
            s.play(T0 + i * st.PLAY_COOLDOWN_S)
        self.assertEqual(s.coins, st.PLAY_COINS_PER_DAY)

    def test_custom_meal_and_snack(self):
        s = rich(0)
        s.fullness = 20.0
        s.feed(T0, meal=60, love=5)
        self.assertEqual((s.fullness, s.affection), (80.0, 5))
        ev = s.snack(T0, food=10, love=3)
        self.assertEqual((s.fullness, s.affection, s.coins), (90.0, 8, st.FEED_COINS))
        self.assertIn("level_up", ev)


if __name__ == "__main__":
    unittest.main()
