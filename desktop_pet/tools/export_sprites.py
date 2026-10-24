"""Export the built-in drawn cat as a sprite pack: a template to paint over.

    python tools/export_sprites.py [out_folder]      (default: sprites/cat_template)

Writes sheet.png (one row per animation, drawn at 2x for sharp high-DPI art)
and sprite.json. Edit the PNG in any paint program, keep the grid, and pick the
pack under Settings > Look. See species/sprite.py for the sprite.json format.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter  # noqa: E402

from species.cat import Cat  # noqa: E402

SCALE = 2
OFFSET_Y = 16             # room above the drawing area for ears and raised paws
# animation: (frames, ticks between frames); fps = 30 / step
ANIMS = {
    "idle": (8, 5), "walk": (4, 6), "sleep": (8, 10), "eat": (6, 2), "held": (6, 3),
    "sit": (8, 6), "groom": (8, 3), "stretch": (4, 8), "yawn": (8, 4), "look": (8, 11),
}


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "sprites" / "cat_template"
    if QGuiApplication.instance() is None:
        main.app = QGuiApplication(sys.argv[:1])   # needed to paint text; kept alive on main
    cat = Cat()
    fw, fh = cat.width, cat.height + OFFSET_Y
    cols = max(n for n, _ in ANIMS.values())
    sheet = QImage(fw * cols * SCALE, fh * len(ANIMS) * SCALE, QImage.Format.Format_ARGB32_Premultiplied)
    sheet.fill(QColor(0, 0, 0, 0))
    p = QPainter(sheet)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(SCALE, SCALE)
    manifest_anims = {}
    for row, (pose, (frames, step)) in enumerate(ANIMS.items()):
        for i in range(frames):
            p.save()
            p.translate(i * fw, row * fh + OFFSET_Y)
            p.setClipRect(0, -OFFSET_Y, fw, fh)
            cat.paint(p, pose, 1, i * step, i % 4)
            p.restore()
        manifest_anims[pose] = {"row": row, "frames": frames, "fps": round(30 / step, 2)}
    p.end()

    out.mkdir(parents=True, exist_ok=True)
    sheet.save(str(out / "sheet.png"))
    poses = list(ANIMS) + ["fall"]
    manifest = {
        "species": cat.name, "sheet": "sheet.png", "scale": SCALE,
        "frame_w": cat.width, "frame_h": cat.height, "offset_y": OFFSET_Y,
        "feet_y": cat.feet_y, "sleep_feet_y": cat.sleep_feet_y,
        "walk_speed": cat.walk_speed, "reach_x": cat.reach_x,
        "animations": manifest_anims,
        "idle_anims": {k: list(v) for k, v in cat.idle_anims.items()},
        "head": {pose: list(cat.head_for(pose)) for pose in poses},
        "hat": {pose: list(cat.hat_anchor(pose)) for pose in poses},
        "neck": {pose: (list(a) if (a := cat.neck_anchor(pose)) else None) for pose in poses},
    }
    (out / "sprite.json").write_text(json.dumps(manifest, indent=2))
    print("wrote", out)


if __name__ == "__main__":
    main()
