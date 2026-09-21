"""Dual-dice mechanics."""
from __future__ import annotations

import random
from dataclasses import dataclass

from .constants import DICE_SIDES


@dataclass(frozen=True)
class DiceRoll:
    """Two dice values; the active player picks one of them."""
    values: tuple[int, int]

    def __getitem__(self, index: int) -> int:
        return self.values[index]


def roll_two_dice(rng: random.Random | None = None) -> DiceRoll:
    rng = rng or random
    return DiceRoll((rng.randint(1, DICE_SIDES), rng.randint(1, DICE_SIDES)))
