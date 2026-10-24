"""Load / save pet data as JSON in %APPDATA%\\DesktopPet\\save.json"""
import json
import os
from pathlib import Path

DEFAULTS = {
    "species": "cat",
    "taskbar_only": True,
    "x": None,
    "y": None,
    "times_petted": 0,
}


def save_path() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "DesktopPet" / "save.json"


def load() -> dict:
    data = dict(DEFAULTS)
    try:
        with open(save_path(), "r", encoding="utf-8") as f:
            data.update(json.load(f))
    except Exception:
        pass  # first run or unreadable file: use defaults
    return data


def save(data: dict) -> None:
    try:
        path = save_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    except Exception as e:
        print("Could not save:", e)
