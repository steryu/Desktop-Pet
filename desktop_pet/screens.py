"""Multi-monitor helpers: which screen is a point on?"""
from PySide6.QtCore import QPoint
from PySide6.QtGui import QGuiApplication


def screen_at(x, y):
    """The screen containing (x, y), or the nearest one (e.g. a monitor was unplugged)."""
    s = QGuiApplication.screenAt(QPoint(int(x), int(y)))
    if s is not None:
        return s

    def dist(scr):
        g = scr.geometry()
        dx = max(g.left() - x, 0, x - g.right())
        dy = max(g.top() - y, 0, y - g.bottom())
        return dx * dx + dy * dy

    return min(QGuiApplication.screens(), key=dist, default=QGuiApplication.primaryScreen())


def area_at(x, y):
    """Usable area (no taskbar / Dock / menu bar) of the screen at (x, y)."""
    return screen_at(x, y).availableGeometry()
