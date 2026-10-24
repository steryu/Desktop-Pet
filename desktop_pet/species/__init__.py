from .cat import Cat
from .sprite import SpriteSpecies, find_packs

# Register new animals here, e.g. "dog": Dog
SPECIES = {"cat": Cat}


def get_species(name: str, pack=None, folders=()):
    """The built-in drawn species, or a sprite pack by folder name if one is chosen."""
    if pack:
        path = find_packs(folders).get(pack)
        if path is not None:
            try:
                return SpriteSpecies(path)
            except Exception as e:                # broken pack: fall back to the drawn one
                print(f"Can't load sprite pack {pack}:", e)
    return SPECIES.get(name, Cat)()
