"""A species drawn from a sprite sheet instead of code.

A sprite pack is a folder with sheet.png and sprite.json, in either
  <app>/sprites/<pack>/        (shipped with the app)
  <save folder>/sprites/<pack>/  (your own)

sprite.json:
  species        which species this is ("cat"): decides what it can wear, etc.
  frame_w/h      size of one frame in the pet's own units (the sheet may be drawn
                 at "scale" times that, e.g. 2 for sharp art on high-DPI screens)
  offset_y       rows of empty space above the drawing area (ears, hats, raised paws)
  feet_y, sleep_feet_y, walk_speed, reach_x    like the Species attributes
  animations     pose -> {"row": r, "frames": n, "fps": f}; at least "idle".
                 Missing poses fall back (look/yawn -> idle, fall -> held, ...).
  idle_anims     idle animation -> [min s, max s] (only ones with an animation)
  head, hat, neck   pose -> [x, y] or [x, y, tilt], plus "default"; null = hidden

tools/export_sprites.py writes the built-in cat as a pack, a template to paint over.
"""
import json
from pathlib import Path

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPixmap

from .base import Species

FALLBACK = {"fall": "held", "hop": "idle", "jump": "idle", "look": "idle", "yawn": "idle",
            "groom": "sit", "walk": "idle", "eat": "idle", "sleep": "idle", "held": "idle",
            "sit": "idle", "stretch": "idle"}


def find_packs(folders):
    """{pack name: folder} for every folder/<pack>/sprite.json that exists."""
    packs = {}
    for base in folders:
        base = Path(base)
        if base.is_dir():
            for d in sorted(base.iterdir()):
                if (d / "sprite.json").is_file():
                    packs[d.name] = d
    return packs


class SpriteSpecies(Species):
    def __init__(self, folder):
        folder = Path(folder)
        m = json.loads((folder / "sprite.json").read_text(encoding="utf-8"))
        self.pack = folder.name
        self.name = m.get("species", "cat")
        self.width, self.height = int(m["frame_w"]), int(m["frame_h"])
        self.offset_y = int(m.get("offset_y", 0))
        self.scale = float(m.get("scale", 1))
        self.feet_y = m.get("feet_y", self.height - 8)
        self.sleep_feet_y = m.get("sleep_feet_y", self.feet_y)
        self.walk_speed = m.get("walk_speed", 2.0)
        self.reach_x = m.get("reach_x", self.width * 0.9)
        self.anims = m["animations"]
        if "idle" not in self.anims:
            raise ValueError(f"{folder}: sprite.json needs an 'idle' animation")
        self.idle_anims = {k: tuple(v) for k, v in m.get("idle_anims", {}).items() if k in self.anims}
        self.points = {k: m.get(k, {}) for k in ("head", "hat", "neck")}
        self.sheet = QPixmap(str(folder / m.get("sheet", "sheet.png")))
        if self.sheet.isNull():
            raise ValueError(f"{folder}: can't read the sprite sheet")

    # ---------- anchor points ----------
    def _point(self, kind, pose, default):
        table = self.points[kind]
        v = table.get(pose, table.get("default", default))
        return tuple(v) if v else None

    def head_for(self, pose):
        return self._point("head", pose, (self.width * 0.7, self.height * 0.4))[:2]

    def hat_anchor(self, pose):
        a = self._point("hat", pose, None)
        return (a + (0,))[:3] if a else None

    def neck_anchor(self, pose):
        a = self._point("neck", pose, None)
        return (a + (0,))[:3] if a else None

    # ---------- drawing ----------
    def animation(self, pose):
        seen = set()
        while pose not in self.anims and pose not in seen:
            seen.add(pose)
            pose = FALLBACK.get(pose, "idle")
        return self.anims.get(pose, self.anims["idle"])

    def source_rect(self, pose, t):
        a = self.animation(pose)
        i = int(t * a.get("fps", 8) / 30) % max(1, a.get("frames", 1))
        fw, fh, s = self.width, self.height + self.offset_y, self.scale
        return QRectF(i * fw * s, a["row"] * fh * s, fw * s, fh * s)

    def paint(self, p, pose, facing, t, frame, look=None):
        p.save()
        if facing < 0:
            p.translate(self.width, 0)
            p.scale(-1, 1)
        target = QRectF(0, -self.offset_y, self.width, self.height + self.offset_y)
        p.drawPixmap(target, self.sheet, self.source_rect(pose, t))
        p.restore()
