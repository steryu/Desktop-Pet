import sys

from PySide6.QtWidgets import QApplication

import save as savemod
from pet import PetWindow
from species import get_species


def main():
    app = QApplication(sys.argv)
    data = savemod.load()
    pet = PetWindow(get_species(data["species"]), data)
    pet.show()
    app.aboutToQuit.connect(pet.save_state)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
