# Desktop Pet

## Run
**Windows**
1. Install Python 3.10+ (tick "Add Python to PATH").
2. In this folder:  `pip install -r requirements.txt`
3. Double-click `main.pyw` (or run `python main.py` to see errors in a console).

**macOS**
1. In this folder:  `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
2. `.venv/bin/python main.py`

## Build an app to share
- Windows: run `build_windows.bat` → `dist\DesktopPet.exe` (one file, no Python needed)
- macOS: run `./build_mac.sh` → `dist/Desktop Pet.app` (lives in the menu bar, no Dock icon)

Both use `desktop_pet.spec` (PyInstaller). Build on the system you're building for.

## Controls
- Drag the pet with the left mouse button, drop it and it falls to the taskbar (Dock on macOS)
- Click the pet to pet it (hearts, affection, coins)
- Hover over the pet to see its status: mood, food, energy, love level, coins
- Click the food bowl to fill it; the pet walks over and eats when it's hungry
- Click the ball to kick it, or drag and throw it; the pet chases it and plays
- Drag the bowl, bed or ball anywhere; let go and it falls back to the ground
- Wiggle the mouse near the pet and it chases the cursor and pounces; its eyes follow the cursor
- Drop the pet above a window and it lands on top of it
- Right-click the pet: Store, give a treat, fill the food bowl (kibble or store food), toggles
  (walk on surfaces only, climb on windows, speech bubbles), Quit
- Right-click furniture: fill the bowl, put it away, open the store
- Tray icon (menu bar on macOS): hide / show the pet, store, settings, sound, quit
- Settings: behaviour toggles, sound on/off and volume, art style, start at login

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
- Coins: +1 per petting (up to 20 a day), +1 per play (up to 15 a day), +3 per meal, and a daily
  bonus of 10 for the first visit of the day, +2 for each day in a row (up to 20).

## Polish
- Sound effects (meow, purr, munch, coins, boing...), generated in code; mute or set the volume
  in Settings or the tray.
- Multi-monitor: drag the pet to another screen and it lives there; furniture remembers its screen.
- Start at login: Windows (Run key), macOS (LaunchAgent), Linux (autostart entry).
- Sprite art: pick a sprite pack under Settings > Look. `tools/export_sprites.py` writes the
  built-in cat as `sprites/cat_template` to paint over; put your own packs in
  `<save folder>/sprites/<name>/`. Format: see `species/sprite.py`.

## Store
- Food: treats (from your hand), fresh fish and tuna (go in the bowl; bigger meals, more love).
  Kibble is always free.
- Toys: ball, yarn ball, toy mouse. The pet plays with any toy that's out.
- Furniture: pet bed, deluxe bed (naps recover 3x), potted plant, fish bowl.
- Accessories: collars and hats, one of each worn at a time.
- Inventory tab: give or serve food, place or put away furniture, wear or take off accessories.

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
- `furniture.py`    beds, food bowl, toys, decorations: one shared furniture system. Add new objects to `KINDS`.
- `hud.py`          status panel shown on hover
- `personality.py`  time of day, idle choices, speech lines, random events (data, no Qt)
- `bubble.py`       speech bubble window
- `butterfly.py`    butterfly for the random event
- `store.py`        store catalog and inventory (data, no Qt). Add new items here.
- `store_window.py` the store window
- `accessories.py`  draws hats and collars where the species says they go
- `desktop_windows.py` reads other apps' windows (ctypes, macOS + Windows) for perching
- `save.py`         load/save JSON in %APPDATA%\DesktopPet\save.json (~/DesktopPet/save.json elsewhere)
- `species/`        one file per animal (drawing + traits). Add new animals here.
- `sounds.py`       synthesised sound effects + player
- `tray.py`, `settings_window.py`  tray icon and settings window
- `autostart.py`    start at login on Windows / macOS / Linux
- `screens.py`      which monitor a point is on
- `icons.py`        app / tray icon drawn from the species
- `paths.py`        app folder vs save folder (works when packaged)
- `species/sprite.py`  sprite-sheet species; `sprites/` holds packs
- `tools/`          `export_sprites.py` (sprite template), `make_icons.py` (assets/ icons)
- `desktop_pet.spec`, `build_windows.bat`, `build_mac.sh`  packaging
- `tests/`          `python -m unittest discover -s tests`
