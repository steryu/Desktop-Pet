"""Store catalog and the player's inventory.

Items are data: add one here (and, for furniture, a class in furniture.KINDS;
for something to wear, a drawing in accessories.py) without new code paths.
Plain Python (no Qt) so it can be tested.

kinds:
  snack      given from your hand (pet menu)    food, love
  meal       goes in the bowl                   food, love
  furniture  placed on the desktop, bought once
  wear       worn by the pet, bought once       slot: hat | collar
"species": which species can use it (None = all).
"""
from stats import FEED_AFFECTION, MEAL

CATEGORIES = ["Food", "Toys", "Furniture", "Accessories"]

ITEMS = {
    # ---- food ----
    "treat": {"name": "Cat treat", "category": "Food", "price": 3, "icon": "🍪",
              "kind": "snack", "food": 10, "love": 3,
              "desc": "A snack from your hand. +10 food, +3 love."},
    "fish": {"name": "Fresh fish", "category": "Food", "price": 8, "icon": "🐟",
             "kind": "meal", "food": 60, "love": 5,
             "desc": "A bowl of fish. +60 food, +5 love."},
    "tuna": {"name": "Tuna feast", "category": "Food", "price": 15, "icon": "🥫",
             "kind": "meal", "food": 90, "love": 8,
             "desc": "The good stuff. +90 food, +8 love."},
    # ---- toys ----
    "ball": {"name": "Ball", "category": "Toys", "price": 20, "icon": "🔴",
             "kind": "furniture", "desc": "Bouncy. Click to kick, or throw it."},
    "yarn": {"name": "Yarn ball", "category": "Toys", "price": 40, "icon": "🧶",
             "kind": "furniture", "desc": "Rolls slowly. Cats can't resist it."},
    "mouse": {"name": "Toy mouse", "category": "Toys", "price": 60, "icon": "🐭",
              "kind": "furniture", "desc": "Skitters fast when batted around."},
    # ---- furniture ----
    "bed": {"name": "Pet bed", "category": "Furniture", "price": 50, "icon": "🛏️",
            "kind": "furniture", "desc": "Naps here recover energy twice as fast."},
    "deluxe_bed": {"name": "Deluxe bed", "category": "Furniture", "price": 150, "icon": "🛋️",
                   "kind": "furniture", "desc": "Plush. Naps recover energy three times as fast."},
    "plant": {"name": "Potted plant", "category": "Furniture", "price": 30, "icon": "🪴",
              "kind": "furniture", "desc": "A bit of green for the desktop."},
    "fishbowl": {"name": "Fish bowl", "category": "Furniture", "price": 80, "icon": "🐠",
                 "kind": "furniture", "desc": "A goldfish to watch. Just watch."},
    # ---- accessories ----
    "red_collar": {"name": "Red collar", "category": "Accessories", "price": 25, "icon": "⭕",
                   "kind": "wear", "slot": "collar", "species": ["cat"],
                   "desc": "Classic."},
    "bell_collar": {"name": "Bell collar", "category": "Accessories", "price": 45, "icon": "🔔",
                    "kind": "wear", "slot": "collar", "species": ["cat"],
                    "desc": "Jingles. You'll always know where it is."},
    "bow": {"name": "Pink bow", "category": "Accessories", "price": 35, "icon": "🎀",
            "kind": "wear", "slot": "hat", "species": ["cat"],
            "desc": "Very fancy."},
    "party_hat": {"name": "Party hat", "category": "Accessories", "price": 60, "icon": "🎉",
                  "kind": "wear", "slot": "hat", "species": ["cat"],
                  "desc": "Every day is a party."},
    "crown": {"name": "Crown", "category": "Accessories", "price": 300, "icon": "👑",
              "kind": "wear", "slot": "hat", "species": ["cat"],
              "desc": "For royalty. Which it already knew it was."},
}

DEFAULT_OWNED = ["bowl", "bed", "ball"]     # what a new pet starts with ("bowl" isn't sold)


def in_category(category):
    return [iid for iid, it in ITEMS.items() if it["category"] == category]


def meal(food):
    """(fullness, love) for a bowl of this food; kibble (or None) is the free default."""
    it = ITEMS.get(food)
    if it is None or it["kind"] != "meal":
        return MEAL, FEED_AFFECTION
    return it["food"], it["love"]


class Inventory:
    def __init__(self, data):
        inv = data.get("inventory")
        if inv is None:                          # older saves: whatever was placed is owned
            placed = [f.get("kind") for f in data.get("furniture") or []]
            inv = {"owned": DEFAULT_OWNED + [k for k in placed if k not in DEFAULT_OWNED]}
        self.food = {k: int(v) for k, v in (inv.get("food") or {}).items() if int(v) > 0}
        self.owned = list(inv.get("owned") or DEFAULT_OWNED)
        self.worn = dict(inv.get("worn") or {})

    def can_buy(self, item_id, coins, species):
        """(ok, reason shown when not ok)"""
        it = ITEMS.get(item_id)
        if it is None:
            return False, "Not sold here"
        if it.get("species") and species not in it["species"]:
            return False, f"Not for a {species}"
        if it["kind"] in ("furniture", "wear") and item_id in self.owned:
            return False, "Owned"
        if coins < it["price"]:
            return False, f"Need {it['price'] - coins} more coins"
        return True, ""

    def buy(self, item_id, stats, species):
        if not self.can_buy(item_id, stats.coins, species)[0]:
            return False
        it = ITEMS[item_id]
        stats.spend(it["price"])
        if it["kind"] in ("snack", "meal"):
            self.food[item_id] = self.food.get(item_id, 0) + 1
        else:
            self.owned.append(item_id)
        return True

    def use_food(self, item_id):
        if self.food.get(item_id, 0) <= 0:
            return False
        self.food[item_id] -= 1
        if self.food[item_id] == 0:
            del self.food[item_id]
        return True

    def wear(self, item_id):
        it = ITEMS.get(item_id)
        if it is None or it["kind"] != "wear" or item_id not in self.owned:
            return False
        self.worn[it["slot"]] = item_id
        return True

    def take_off(self, slot):
        self.worn.pop(slot, None)

    def to_dict(self):
        return {"food": dict(self.food), "owned": list(self.owned), "worn": dict(self.worn)}
