"""Where things live: the app's own files, and the user's save folder."""
import sys
from pathlib import Path

import save


def app_dir():
    """Folder with the app's files (inside the bundle when packaged)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


def data_dir():
    """The user's save folder (save.json, sounds, their own sprite packs)."""
    return save.save_path().parent


def sprite_folders():
    return [app_dir() / "sprites", data_dir() / "sprites"]
