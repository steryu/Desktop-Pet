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
- Right-click: fill food bowl / coins / toggle "Only walk on taskbar" / Quit

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

## Project layout
- `main.pyw`        starts the app
- `pet.py`          pet window, state machine, dragging, hearts, feeding, unlocks
- `stats.py`        food, energy, affection, coins, mood (no Qt, unit-tested)
- `furniture.py`    bed, food bowl, ball: one shared furniture system. Add new objects to `KINDS`.
- `hud.py`          status panel shown on hover
- `save.py`         load/save JSON in %APPDATA%\DesktopPet\save.json (~/DesktopPet/save.json elsewhere)
- `species/`        one file per animal (drawing + traits). Add new animals here.
- `tests/`          `python -m unittest discover -s tests`
