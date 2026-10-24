"""The store window: a tab per category, plus the inventory.

It only shows things and calls the pet's actions (buy, place, wear, ...);
the rules live in store.py.
"""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QTabWidget, QVBoxLayout, QWidget)

import store

CARD_STYLE = """
QFrame#card { border: 1px solid palette(mid); border-radius: 8px; background: palette(base); }
QLabel#muted { color: palette(placeholder-text); }
QLabel#section { font-weight: bold; margin-top: 8px; }
"""
EXTRA_NAMES = {"bowl": ("Food bowl", "🥣")}      # owned from the start, not sold


def name_icon(item_id):
    if item_id in store.ITEMS:
        return store.ITEMS[item_id]["name"], store.ITEMS[item_id]["icon"]
    return EXTRA_NAMES.get(item_id, (item_id, "•"))


class StoreWindow(QWidget):
    def __init__(self, pet):
        super().__init__()
        self.pet = pet
        self.setWindowTitle("Pet Store")
        self.resize(560, 500)
        self.setStyleSheet(CARD_STYLE)
        self._buy_buttons = []                   # (button, item id), re-checked every second

        root = QVBoxLayout(self)
        top = QHBoxLayout()
        title = QLabel("🐾 Pet Store")
        title.setFont(QFont(title.font().family(), 16, QFont.Weight.Bold))
        self.coins = QLabel()
        self.coins.setFont(QFont(self.coins.font().family(), 14, QFont.Weight.Bold))
        top.addWidget(title)
        top.addStretch()
        top.addWidget(self.coins)
        root.addLayout(top)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs)

        self.rebuild()
        self.timer = QTimer(self)                # coins change while it's open (petting...)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)

    # ------------------------------------------------------------------
    def rebuild(self):
        current = self.tabs.currentIndex()
        self._buy_buttons = []
        self.tabs.clear()
        for cat in store.CATEGORIES:
            self.tabs.addTab(self._scroll(self._shop_page(cat)), cat)
        self.tabs.addTab(self._scroll(self._inventory_page()), "Inventory")
        self.tabs.setCurrentIndex(max(current, 0))
        self.refresh()

    def refresh(self):
        self.coins.setText(f"🪙 {self.pet.stats.coins}")
        for button, iid in self._buy_buttons:
            ok, why = self.pet.inventory.can_buy(iid, self.pet.stats.coins, self.pet.species.name)
            button.setEnabled(ok)
            button.setText("Buy" if ok or why != "Owned" else "Owned")
            button.setToolTip(why)

    def _scroll(self, page):
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.Shape.NoFrame)
        area.setWidget(page)
        return area

    # ------------------------------------------------------------------
    def _shop_page(self, category):
        page = QWidget()
        grid = QGridLayout(page)
        for n, iid in enumerate(store.in_category(category)):
            it = store.ITEMS[iid]
            buy = QPushButton("Buy")
            buy.clicked.connect(lambda _=False, i=iid: self._act(self.pet.buy, i))
            self._buy_buttons.append((buy, iid))
            grid.addWidget(self._card(it["icon"], it["name"], it["desc"], f"🪙 {it['price']}", buy),
                           n // 2, n % 2)
        grid.setRowStretch(grid.rowCount(), 1)
        return page

    def _card(self, icon, name, desc, price, button):
        card = QFrame()
        card.setObjectName("card")
        row = QHBoxLayout(card)
        ic = QLabel(icon)
        ic.setFont(QFont(ic.font().family(), 28))
        ic.setFixedWidth(48)
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(ic)
        col = QVBoxLayout()
        title = QLabel(f"<b>{name}</b>")
        text = QLabel(desc)
        text.setObjectName("muted")
        text.setWordWrap(True)
        bottom = QHBoxLayout()
        bottom.addWidget(QLabel(price))
        bottom.addStretch()
        bottom.addWidget(button)
        col.addWidget(title)
        col.addWidget(text)
        col.addLayout(bottom)
        row.addLayout(col, 1)
        return card

    # ------------------------------------------------------------------
    def _inventory_page(self):
        pet, inv = self.pet, self.pet.inventory
        page = QWidget()
        col = QVBoxLayout(page)

        col.addWidget(self._section("Food"))
        if not inv.food:
            col.addWidget(self._muted("No food yet. Kibble is always free; buy treats and meals under Food."))
        for iid, count in inv.food.items():
            if store.ITEMS[iid]["kind"] == "snack":
                b = QPushButton("Give")
                b.clicked.connect(lambda _=False: self._act(pet.give_treat))
            else:
                b = QPushButton("Put in bowl")
                b.setEnabled(pet.bowl is not None and not pet.bowl.full)
                b.setToolTip("" if b.isEnabled() else "The bowl needs to be on the desktop and empty")
                b.clicked.connect(lambda _=False, i=iid: self._act(pet.fill_bowl, i))
            col.addWidget(self._row(iid, f"× {count}", b))

        col.addWidget(self._section("On the desktop"))
        for iid in inv.owned:
            if iid in store.ITEMS and store.ITEMS[iid]["kind"] == "wear":
                continue
            placed = pet.home.placed(iid)
            b = QPushButton("Put away" if placed else "Place")
            b.clicked.connect(lambda _=False, i=iid, p=placed:
                              self._act(pet.put_away if p else pet.place, i))
            col.addWidget(self._row(iid, "out" if placed else "stored", b))

        col.addWidget(self._section("Accessories"))
        worn = [i for i in inv.owned if i in store.ITEMS and store.ITEMS[i]["kind"] == "wear"]
        if not worn:
            col.addWidget(self._muted("Nothing to wear yet. Have a look under Accessories."))
        for iid in worn:
            slot = store.ITEMS[iid]["slot"]
            wearing = inv.worn.get(slot) == iid
            b = QPushButton("Take off" if wearing else "Wear")
            b.clicked.connect(lambda _=False, i=iid, s=slot, w=wearing:
                              self._act(pet.take_off, s) if w else self._act(pet.wear, i))
            col.addWidget(self._row(iid, "wearing" if wearing else "", b))

        col.addStretch()
        return page

    def _section(self, text):
        label = QLabel(text)
        label.setObjectName("section")
        return label

    def _muted(self, text):
        label = QLabel(text)
        label.setObjectName("muted")
        label.setWordWrap(True)
        return label

    def _row(self, iid, note, button):
        name, icon = name_icon(iid)
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(4, 0, 4, 0)
        row.addWidget(QLabel(f"{icon}  {name}"))
        n = self._muted(note)
        row.addWidget(n)
        row.addStretch()
        row.addWidget(button)
        return w

    def _act(self, action, *args):
        action(*args)
        self.rebuild()
