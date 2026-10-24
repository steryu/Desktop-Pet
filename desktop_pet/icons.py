"""The app icon, drawn from the species itself (sitting), so it always matches the pet."""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap


def render(species, size, background=None):
    """A square image of the pet sitting (or idle if it has no sit pose)."""
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    if background is not None:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(background))
        p.drawRoundedRect(QRectF(0, 0, size, size), size * 0.22, size * 0.22)
    pose = "sit" if "sit" in getattr(species, "idle_anims", {}) else "idle"
    # the sitting cat spans roughly x 6..92, y -6..82 in drawing coords
    box = QRectF(2, -10, 96, 96)
    pad = size * (0.12 if background is not None else 0.02)
    k = (size - 2 * pad) / box.width()
    p.translate(pad - box.x() * k, pad - box.y() * k)
    p.scale(k, k)
    species.paint(p, pose, 1, 0, 0)
    p.end()
    return img


def app_icon(species):
    icon = QIcon()
    for size in (16, 32, 64, 128, 256):
        icon.addPixmap(QPixmap.fromImage(render(species, size)))
    return icon
