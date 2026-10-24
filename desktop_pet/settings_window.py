"""Settings window: behaviour, sound, look and system options, applied immediately."""
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
                               QMessageBox, QPushButton, QSlider, QVBoxLayout, QWidget)

import autostart
import paths
from species import find_packs


class SettingsWindow(QWidget):
    def __init__(self, pet):
        super().__init__()
        self.pet = pet
        self.setWindowTitle("Desktop Pet Settings")
        self.setMinimumWidth(380)
        root = QVBoxLayout(self)

        behaviour = QGroupBox("Behaviour")
        b = QVBoxLayout(behaviour)
        self.surfaces = QCheckBox("Walk on surfaces only (no floating around the screen)")
        self.climb = QCheckBox("Climb on top of other windows")
        self.speech = QCheckBox("Speech bubbles")
        for box in (self.surfaces, self.climb, self.speech):
            b.addWidget(box)
        self.surfaces.toggled.connect(lambda on: self._apply(pet.set_taskbar_only, on))
        self.climb.toggled.connect(lambda on: self._apply(pet.set_climb, on))
        self.speech.toggled.connect(lambda on: self._apply(pet.set_speech, on))
        root.addWidget(behaviour)

        sound = QGroupBox("Sound")
        s = QFormLayout(sound)
        self.sound_on = QCheckBox("Sound effects")
        self.sound_on.toggled.connect(lambda on: self._apply(pet.set_sound, on))
        s.addRow(self.sound_on)
        row = QHBoxLayout()
        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.valueChanged.connect(lambda v: self._apply(pet.set_volume, v / 100))
        test = QPushButton("Test")
        test.clicked.connect(lambda: pet.sounds.play("meow"))
        row.addWidget(self.volume, 1)
        row.addWidget(test)
        s.addRow("Volume", row)
        root.addWidget(sound)

        look = QGroupBox("Look")
        lk = QFormLayout(look)
        self.art = QComboBox()
        self.art.currentIndexChanged.connect(self._art_changed)
        lk.addRow("Art style", self.art)
        hint = QLabel("Sprite packs are folders in “sprites” next to the app or in your save "
                      "folder. tools/export_sprites.py makes a template to paint over.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: palette(placeholder-text);")
        lk.addRow(hint)
        root.addWidget(look)

        system = QGroupBox("System")
        sy = QVBoxLayout(system)
        login = {"win32": "Start with Windows", "darwin": "Open at login"}.get(sys.platform, "Start at login")
        self.autostart = QCheckBox(login)
        self.autostart.toggled.connect(self._autostart_changed)
        sy.addWidget(self.autostart)
        where = QLabel(f"Save file: {paths.data_dir() / 'save.json'}")
        where.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        where.setWordWrap(True)
        where.setStyleSheet("color: palette(placeholder-text);")
        sy.addWidget(where)
        root.addWidget(system)

        close = QPushButton("Close")
        close.clicked.connect(self.close)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(close)
        root.addLayout(row)

    def sync(self):
        """Show the current values (they can also change from the menus)."""
        pet = self.pet
        widgets = (self.surfaces, self.climb, self.speech, self.sound_on, self.volume,
                   self.art, self.autostart)
        for w in widgets:
            w.blockSignals(True)
        self.surfaces.setChecked(pet.taskbar_only)
        self.climb.setChecked(pet.climb)
        self.speech.setChecked(pet.speech)
        self.sound_on.setChecked(pet.sounds.enabled)
        self.volume.setValue(int(pet.sounds.volume * 100))
        self.art.clear()
        self.art.addItem("Drawn (built-in)", None)
        for name in find_packs(paths.sprite_folders()):
            self.art.addItem(f"Sprite pack: {name}", name)
        self.art.setCurrentIndex(max(0, self.art.findData(pet.sprite_pack)))
        try:
            self.autostart.setChecked(autostart.is_enabled())
        except Exception:
            self.autostart.setEnabled(False)
        for w in widgets:
            w.blockSignals(False)

    def _apply(self, setter, value):
        setter(value)
        self.pet.save_state()

    def _art_changed(self, _index):
        self._apply(self.pet.set_art, self.art.currentData())
        if self.pet.tray is not None:
            self.pet.tray.refresh_icon()

    def _autostart_changed(self, on):
        try:
            autostart.set_enabled(on)
        except Exception as e:
            QMessageBox.warning(self, "Desktop Pet", f"Couldn't change the login setting:\n{e}")
            self.sync()
