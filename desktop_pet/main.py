import sys

from PySide6.QtWidgets import QApplication, QSystemTrayIcon

import icons
import paths
import save as savemod
from pet import PetWindow
from species import get_species
from tray import Tray


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Desktop Pet")
    app.setQuitOnLastWindowClosed(False)   # closing the store mustn't quit; use the pet's menu
    data = savemod.load()
    species = get_species(data["species"], data.get("sprite_pack"), paths.sprite_folders())
    app.setWindowIcon(icons.app_icon(species))
    pet = PetWindow(species, data)
    pet.home.show()
    pet.show()                      # shown last so the pet is in front of the furniture
    if QSystemTrayIcon.isSystemTrayAvailable():
        pet.tray = Tray(pet)
        pet.tray.show()
    app.aboutToQuit.connect(pet.save_state)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
