# Desktop Pet

## Run
1. Install Python 3.10+ (tick "Add Python to PATH").
2. In this folder:  `pip install -r requirements.txt`
3. Double-click `main.pyw` (or run `python main.py` to see errors in a console).

## Controls
- Drag the pet with the left mouse button, drop it and it falls to the taskbar
- Click the pet to pet it (hearts)
- Right-click: toggle "Only walk on taskbar" / Quit

## Project layout
- `main.pyw`        starts the app
- `pet.py`          pet window, state machine, dragging, hearts
- `save.py`         load/save JSON in %APPDATA%\DesktopPet\save.json
- `species/`        one file per animal (drawing + traits). Add new animals here.
