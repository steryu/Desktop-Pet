"""Drawing hats and collars on the pet.

The species says where they go (hat_anchor / neck_anchor: x, y, tilt in
degrees, in its facing-right drawing coords); this module draws them there,
so every species gets every accessory for free.
"""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainterPath, QPen, QPolygonF

RED = QColor("#d63a3a")
GOLD = QColor("#e8b923")
GOLD_DARK = QColor("#b88a10")
PINK = QColor("#f07aa8")
PINK_DARK = QColor("#c9578a")
BLUE = QColor("#4a8fe0")
WHITE = QColor("#ffffff")


def paint(p, worn, species, pose):
    """worn: {"hat": item id, "collar": item id}"""
    collar = worn.get("collar")
    if collar in COLLARS:
        a = species.neck_anchor(pose)
        if a:
            _at(p, a, COLLARS[collar])
    hat = worn.get("hat")
    if hat in HATS:
        a = species.hat_anchor(pose)
        if a:
            _at(p, a, HATS[hat])


def _at(p, anchor, draw):
    x, y, tilt = anchor
    p.save()
    p.translate(x, y)
    p.rotate(tilt)
    draw(p)
    p.restore()


# ---------- collars: drawn as a band across (0, 0), across the neck ----------
def _band(p, color):
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    p.drawRoundedRect(QRectF(-3, -10, 6, 20), 3, 3)


def red_collar(p):
    _band(p, RED)
    p.setBrush(GOLD)
    p.drawEllipse(QPointF(3, 4), 2, 2)              # tag


def bell_collar(p):
    _band(p, BLUE)
    p.setBrush(GOLD)
    p.setPen(QPen(GOLD_DARK, 1))
    p.drawEllipse(QPointF(5, 5), 4, 4)
    p.drawLine(QPointF(3, 6), QPointF(7, 6))


# ---------- hats: (0, 0) is the middle of the top of the head ----------
def bow(p):
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(PINK)
    p.drawPolygon(QPolygonF([QPointF(0, 0), QPointF(-11, -7), QPointF(-11, 6)]))
    p.drawPolygon(QPolygonF([QPointF(0, 0), QPointF(11, -7), QPointF(11, 6)]))
    p.setBrush(PINK_DARK)
    p.drawEllipse(QPointF(0, 0), 3.5, 3.5)


def party_hat(p):
    cone = QPainterPath()
    cone.moveTo(-9, 2)
    cone.lineTo(0, -22)
    cone.lineTo(9, 2)
    cone.closeSubpath()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(BLUE)
    p.drawPath(cone)
    p.setPen(QPen(GOLD, 2.5))
    p.drawLine(QPointF(-6, -6), QPointF(5, -3))
    p.drawLine(QPointF(-3, -14), QPointF(3, -12))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(PINK)
    p.drawEllipse(QPointF(0, -23), 3.5, 3.5)


def crown(p):
    p.setPen(QPen(GOLD_DARK, 1))
    p.setBrush(GOLD)
    p.drawPolygon(QPolygonF([QPointF(-11, 2), QPointF(-11, -9), QPointF(-6, -3), QPointF(0, -12),
                             QPointF(6, -3), QPointF(11, -9), QPointF(11, 2)]))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(RED)
    p.drawEllipse(QPointF(0, -3), 2.2, 2.2)
    p.setBrush(WHITE)
    for x in (-11, 0, 11):
        p.drawEllipse(QPointF(x, -10 if x else -13), 1.6, 1.6)


COLLARS = {"red_collar": red_collar, "bell_collar": bell_collar}
HATS = {"bow": bow, "party_hat": party_hat, "crown": crown}
