"""Personality rules and data: time of day, idle choices, speech lines, random events.

Plain Python (no Qt) so it can be tested. Lines and events are data:
add a line or an event here without touching the pet code (an event also
needs a handler in pet.py's run_event).
"""
import random


def is_night(hour):
    return hour >= 22 or hour < 7


def sleepiness(hour):
    """How much sleepier than normal the pet is at this hour (1.0 = daytime)."""
    if hour < 7:
        return 2.0
    if hour >= 22:
        return 1.6
    if hour >= 20:
        return 1.25
    if hour < 9:
        return 1.2
    return 1.0


# idle animation -> base weight ("stand" is always available)
IDLE_WEIGHTS = {"stand": 4, "sit": 3, "groom": 2, "stretch": 1, "yawn": 1, "look": 2}


def pick_idle(available, hour, mood, rng=random):
    """Choose an idle animation among the species' ones (plus plain standing)."""
    weights = {"stand": IDLE_WEIGHTS["stand"]}
    for name in available:
        weights[name] = IDLE_WEIGHTS.get(name, 1)
    if "yawn" in weights:
        weights["yawn"] *= 3 * sleepiness(hour) if is_night(hour) or mood == "tired" else 1
    if "sit" in weights and mood in ("sad", "tired"):
        weights["sit"] *= 2
    names = list(weights)
    return rng.choices(names, weights=[weights[n] for n in names])[0]


LINES = {
    "greet_long": ["You're back! I missed you!", "Finally! Where were you?"],
    "greet": ["Welcome back!", "Oh, hi again!"],
    "happy": ["I like you!", "Purrrr...", "Best day ever!"],
    "content": ["Hehe.", "Mrrp?", "That's nice."],
    "sad": ["Pet me?", "...", "Play with me?"],
    "hungry": ["I'm hungry...", "Food, please?", "*stares at bowl*"],
    "tired": ["So sleepy...", "*yawn*", "Nap time?"],
    "held": ["Wheee!", "Put me down!", "Hey!"],
    "night": ["*yawn* Getting late...", "Bedtime soon?"],
    "level_up": ["We're closer now!", "You're the best!"],
    "perch": ["Nice view up here.", "King of the hill!"],
    "butterfly": ["A butterfly!", "Ooh! Wings!"],
    "zoomies": ["Zoomies!", "Gotta go fast!"],
    "coin": ["Ooh, shiny!", "Found a coin!"],
    "sneeze": ["Achoo!", "*sneeze*"],
}


def line(kind, rng=random):
    return rng.choice(LINES[kind])


# random event -> weight
EVENTS = {"butterfly": 3, "zoomies": 2, "coin": 2, "sneeze": 2}


def pick_event(rng=random):
    names = list(EVENTS)
    return rng.choices(names, weights=[EVENTS[n] for n in names])[0]
