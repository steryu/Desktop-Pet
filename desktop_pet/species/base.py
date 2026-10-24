class Species:
    """Everything animal-specific lives in a subclass of this.

    The pet window only knows this interface, so a new animal (or a sprite-sheet
    renderer) can be added without touching the behaviour code.
    """

    name = "base"
    width = 100          # drawing area size in pixels
    height = 100
    feet_y = 90          # y of the feet inside the drawing area while standing
    sleep_feet_y = 90    # y of the bottom of the body while sleeping
    walk_speed = 2.0     # pixels per tick

    def head_for(self, pose: str):
        """Where hearts should appear (x, y), facing right, in drawing coords."""
        return self.width * 0.7, self.height * 0.4

    def paint(self, p, pose: str, facing: int, t: int, frame: int):
        """Draw the pet. pose: walk | idle | sleep | held | fall.
        facing: 1 = right, -1 = left. t = tick counter, frame = walk frame 0-3."""
        raise NotImplementedError
