# Desktop Pet

## Run
**Windows**
1. Install Python 3.10+ (tick "Add Python to PATH").
2. In this folder:  `pip install -r requirements.txt`
3. Double-click `main.pyw` (or run `python main.py` to see errors in a console).

**macOS**
1. In this folder:  `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
2. `.venv/bin/python main.py`

## Controls
- Drag the pet with the left mouse button, drop it and it falls to the taskbar (Dock on macOS)
- Click the pet to pet it (hearts, affection, coins)
- Hover over the pet to see its status: mood, food, energy, love level, coins
- Click the food bowl to fill it; the pet walks over and eats when it's hungry
- Click the ball to kick it, or drag and throw it; the pet chases it and plays
- Drag the bowl, bed or ball anywhere; let go and it falls back to the ground
- Wiggle the mouse near the pet and it chases the cursor and pounces; its eyes follow the cursor
- Drop the pet above a window and it lands on top of it
- Right-click: fill food bowl / coins / toggles (walk on surfaces only, climb on windows,
  speech bubbles) / Quit

## Care
- Food drops slowly and energy drains while awake; naps refill energy.
  Tired pets nap more often and for longer, and go to their bed, where they recover twice as fast.
- Playing with the ball tires the pet a little and grows affection (at most once every 8 s).
- While the app is closed, food keeps dropping (counted for at most 8 hours) and the
  pet rests. A neglected pet only gets sad: needs never drop below 10 and affection
  never goes down.
- Affection grows from petting and feeding. Levels unlock behaviours:
  Acquaintance (15) more hearts, Friend (50) purring, Best friend (120) happy hop,
  Soulmate (250) the odd gift of coins.
- Coins: +1 per petting (up to 20 a day, 3 s cooldown), +3 per meal. Spent in the store later.

## Personality
- Idle animations: sits, grooms, stretches, yawns and looks around.
- Sleepier in the evening and much sleepier at night (more and longer naps, more yawns).
- Climbs onto the tops of other windows, walks along them, rides along when you move the
  window, and falls off if you close it. macOS and Windows only.
- Speech bubbles: greets you when you come back, says when it's hungry, tired or sad, comments
  on petting, being carried and events. At most one unprompted line every 30 s.
- Random events, about one per 5 awake minutes: a butterfly to chase, zoomies, finding a coin, sneezing.

## Project layout
- `main.pyw`        starts the app
- `pet.py`          pet window, state machine, dragging, hearts, feeding, unlocks
- `stats.py`        food, energy, affection, coins, mood (no Qt, unit-tested)
- `furniture.py`    bed, food bowl, ball: one shared furniture system. Add new objects to `KINDS`.
- `hud.py`          status panel shown on hover
- `personality.py`  time of day, idle choices, speech lines, random events (data, no Qt)
- `bubble.py`       speech bubble window
- `butterfly.py`    butterfly for the random event
- `desktop_windows.py` reads other apps' windows (ctypes, macOS + Windows) for perching
- `save.py`         load/save JSON in %APPDATA%\DesktopPet\save.json (~/DesktopPet/save.json elsewhere)
- `species/`        one file per animal (drawing + traits). Add new animals here.
- `tests/`          `python -m unittest discover -s tests`
