from .cat import Cat

# Register new animals here, e.g. "dog": Dog
SPECIES = {"cat": Cat}


def get_species(name: str):
    return SPECIES.get(name, Cat)()
