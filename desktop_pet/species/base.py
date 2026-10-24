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
    idle_anims = {}      # extra idle animations -> (min s, max s), e.g. {"sit": (5, 12)}
    reach_x = 90         # x of the front of the body (nose), facing right: where it touches toys

    def head_for(self, pose: str):
        """Where hearts should appear (x, y), facing right, in drawing coords."""
        return self.width * 0.7, self.height * 0.4

    def hat_anchor(self, pose: str):
        """(x, y, tilt degrees) of the top of the head for hats, facing right; None = hidden."""
        return None

    def neck_anchor(self, pose: str):
        """(x, y, tilt degrees) of the neck for collars, facing right; None = hidden."""
        return None

    def paint(self, p, pose: str, facing: int, t: int, frame: int, look=None):
        """Draw the pet. pose: walk | idle | sleep | eat | held | fall, or one of idle_anims.
        facing: 1 = right, -1 = left. t = tick counter, frame = walk frame 0-3.
        look: where the eyes point, (dx, dy) in -1..1 relative to facing, or None."""
        raise NotImplementedError
