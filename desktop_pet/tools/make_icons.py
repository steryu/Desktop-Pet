"""Render the app icons used for packaging into assets/: icon.png, icon.ico, icon.icns.

    python tools/make_icons.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtGui import QGuiApplication  # noqa: E402

import icons  # noqa: E402
from species.cat import Cat  # noqa: E402

BACKGROUND = "#fde7c4"


def main():
    if QGuiApplication.instance() is None:
        main.app = QGuiApplication(sys.argv[:1])
    out = Path(__file__).resolve().parent.parent / "assets"
    out.mkdir(exist_ok=True)
    cat = Cat()
    icons.render(cat, 512, BACKGROUND).save(str(out / "icon.png"))
    icons.render(cat, 256, BACKGROUND).save(str(out / "icon.ico"))
    icons.render(cat, 1024, BACKGROUND).save(str(out / "icon.icns"))
    print("wrote", ", ".join(sorted(p.name for p in out.iterdir())))


if __name__ == "__main__":
    main()
