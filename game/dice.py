"""
Dice module for AI-Powered Snake & Ladder.
Handles dual-dice roll mechanics, rolling animation physics, and pip configurations.
"""

import random
from typing import Tuple, Optional, List


class DualDice:
    """
    Manages dual-dice mechanics, rolling animation states, and selection.
    """

    # Normalized pip coordinates (x, y in [0.0, 1.0]) for each face 1..6
    PIP_LAYOUTS = {
        1: [(0.5, 0.5)],
        2: [(0.25, 0.25), (0.75, 0.75)],
        3: [(0.25, 0.25), (0.5, 0.5), (0.75, 0.75)],
        4: [(0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)],
        5: [(0.25, 0.25), (0.75, 0.25), (0.5, 0.5), (0.25, 0.75), (0.75, 0.75)],
        6: [
            (0.25, 0.25),
            (0.75, 0.25),
            (0.25, 0.5),
            (0.75, 0.5),
            (0.25, 0.75),
            (0.75, 0.75),
        ],
    }

    def __init__(self, roll_duration: float = 0.25):
        self.roll_duration: float = roll_duration
        self.values: Tuple[int, int] = (1, 1)
        self.display_values: Tuple[int, int] = (1, 1)

        self.is_rolling: bool = False
        self.roll_timer: float = 0.0
        self.selected_index: Optional[int] = None  # 0 for Dice 1, 1 for Dice 2
        self.hovered_index: Optional[int] = None

        self.rotation_angles: List[float] = [0.0, 0.0]

    def roll(self) -> Tuple[int, int]:
        """
        Initiates a new dual-dice roll with random outcomes.
        Returns the final (dice_1, dice_2) values.
        """
        self.values = (random.randint(1, 6), random.randint(1, 6))
        self.display_values = (random.randint(1, 6), random.randint(1, 6))
        self.is_rolling = True
        self.roll_timer = self.roll_duration
        self.selected_index = None
        return self.values

    def update(self, dt: float) -> bool:
        """
        Updates the roll animation timer and randomizes display faces while tumbling.
        Returns True when rolling is completed.
        """
        if not self.is_rolling:
            return True

        self.roll_timer -= dt
        # Jitter rotation angles and randomize face numbers rapidly while rolling
        self.rotation_angles[0] = (self.rotation_angles[0] + 720.0 * dt) % 360.0
        self.rotation_angles[1] = (self.rotation_angles[1] - 680.0 * dt) % 360.0

        if self.roll_timer > 0:
            self.display_values = (random.randint(1, 6), random.randint(1, 6))
            return False
        else:
            self.is_rolling = False
            self.display_values = self.values
            self.rotation_angles = [0.0, 0.0]
            return True

    def select(self, index: int) -> int:
        """
        Selects dice 0 or 1.
        Returns the chosen dice value.
        """
        if index not in (0, 1):
            raise ValueError("Dice index must be 0 or 1")
        self.selected_index = index
        return self.values[index]

    def get_selected_value(self) -> Optional[int]:
        if self.selected_index is not None:
            return self.values[self.selected_index]
        return None

    def reset(self) -> None:
        self.values = (1, 1)
        self.display_values = (1, 1)
        self.is_rolling = False
        self.roll_timer = 0.0
        self.selected_index = None
        self.hovered_index = None
