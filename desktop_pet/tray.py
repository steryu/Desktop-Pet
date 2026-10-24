"""System tray (menu bar on macOS) icon: show/hide the pet, store, settings, sound, quit."""
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

import icons


class Tray(QSystemTrayIcon):
    def __init__(self, pet):
        super().__init__(icons.app_icon(pet.species))
        self.pet = pet
        self.setToolTip("Desktop Pet")
        self.menu = QMenu()
        self.toggle = self.menu.addAction("Hide pet")
        self.toggle.triggered.connect(lambda: pet.set_hidden(not pet.hidden))
        self.menu.addAction("Store…").triggered.connect(pet.open_store)
        self.menu.addAction("Settings…").triggered.connect(pet.open_settings)
        self.sound = self.menu.addAction("Sound effects")
        self.sound.setCheckable(True)
        self.sound.toggled.connect(pet.set_sound)
        self.menu.addSeparator()
        self.menu.addAction("Quit").triggered.connect(QApplication.quit)
        self.menu.aboutToShow.connect(self.sync)
        self.setContextMenu(self.menu)
        self.activated.connect(self.on_click)

    def sync(self):
        self.toggle.setText("Show pet" if self.pet.hidden else "Hide pet")
        self.sound.blockSignals(True)
        self.sound.setChecked(self.pet.sounds.enabled)
        self.sound.blockSignals(False)

    def on_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger and self.pet.hidden:
            self.pet.set_hidden(False)           # click the icon to bring the pet back

    def refresh_icon(self):
        self.setIcon(icons.app_icon(self.pet.species))
