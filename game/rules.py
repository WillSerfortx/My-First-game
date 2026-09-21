"""Pure movement rules shared by the engine, the AI and the simulator."""
from __future__ import annotations

from dataclasses import dataclass

from .board import Board, SpecialKind
from .constants import GOAL_CELL


@dataclass(frozen=True)
class MovePlan:
    """Everything known about a move *before* the shield decision."""
    start: int
    die_index: int
    die_value: int
    walk_path: tuple[int, ...]      # cells stepped through, ending at ``landing``
    landing: int
    special: SpecialKind            # what the landing cell does
    destination: int                # where the special takes the player
    shield_available: bool          # snake + player still owns a shield

    @property
    def needs_shield_decision(self) -> bool:
        return self.special is SpecialKind.SNAKE and self.shield_available


def is_valid_move(pos: int, die: int) -> bool:
    """Exact finish is required: overshooting cell 100 is illegal."""
    return pos + die <= GOAL_CELL


def plan_move(board: Board, pos: int, die_index: int, die_value: int,
              shields: int) -> MovePlan | None:
    """Build a MovePlan or return None when the move overshoots the goal."""
    if not is_valid_move(pos, die_value):
        return None
    landing = pos + die_value
    special = board.kind_at(landing)
    return MovePlan(
        start=pos,
        die_index=die_index,
        die_value=die_value,
        walk_path=tuple(range(pos + 1, landing + 1)),
        landing=landing,
        special=special,
        destination=board.jumps.get(landing, landing),
        shield_available=special is SpecialKind.SNAKE and shields > 0,
    )


def final_cell(plan: MovePlan, use_shield: bool) -> tuple[int, SpecialKind]:
    """Final cell and the special actually applied after the shield decision.

    A shield blocks the snake's bite: the player keeps the snake-head cell.
    """
    if plan.special is SpecialKind.SNAKE and use_shield and plan.shield_available:
        return plan.landing, SpecialKind.NONE
    return plan.destination, plan.special
