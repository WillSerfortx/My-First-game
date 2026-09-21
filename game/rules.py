"""
Rules module for AI-Powered Snake & Ladder.
Encapsulates movement calculations, overshoot bounce rules, snake/ladder triggers,
shield protection logic, and win-condition checks.
"""

from typing import Tuple, List, Dict, Any
from .board import Board


class GameRules:
    """
    Core game rules engine for Snake & Ladder.
    """

    WINNING_CELL = 100

    @classmethod
    def calculate_forward_steps(cls, start: int, roll: int) -> Tuple[List[int], int, bool]:
        """
        Calculates the step-by-step path for ordinary movement and bounce-back.
        Returns:
            steps: List of intermediate cell numbers
            landing_cell: Cell landed on prior to snake/ladder resolution
            bounced: True if overshoot occurred
        """
        raw_target = start + roll
        steps: List[int] = []
        bounced = False

        if raw_target <= cls.WINNING_CELL:
            for c in range(start + 1, raw_target + 1):
                steps.append(c)
            landing = raw_target
        else:
            # Step up to 100
            for c in range(start + 1, cls.WINNING_CELL + 1):
                steps.append(c)
            excess = raw_target - cls.WINNING_CELL
            landing = cls.WINNING_CELL - excess
            # Bounce backward
            for c in range(cls.WINNING_CELL - 1, landing - 1, -1):
                steps.append(c)
            bounced = True

        return steps, landing, bounced

    @classmethod
    def resolve_move(
        cls,
        start_cell: int,
        roll: int,
        board: Board,
        use_shield: bool = False,
    ) -> Dict[str, Any]:
        """
        Computes the complete trajectory and final result of a move.
        Returns a dictionary containing:
            - path: Full sequence of cells to animate through
            - landing_cell: Cell landed before snake/ladder
            - final_cell: Final resting cell
            - hit_snake: bool
            - hit_ladder: bool
            - shield_used: bool
            - bounced: bool
            - snake_loss: int (cells lost if snake was not blocked)
            - ladder_gain: int (cells gained if ladder climbed)
        """
        steps, landing, bounced = cls.calculate_forward_steps(start_cell, roll)
        hit_snake = False
        hit_ladder = False
        shield_used = False
        snake_loss = 0
        ladder_gain = 0
        final_cell = landing
        full_path = list(steps)

        # Check for ladder bottom
        if board.is_ladder_bottom(landing):
            ladder_top = board.get_ladder_top(landing)
            if ladder_top is not None:
                hit_ladder = True
                ladder_gain = ladder_top - landing
                final_cell = ladder_top
                full_path.append(ladder_top)

        # Check for snake head
        elif board.is_snake_head(landing):
            snake_tail = board.get_snake_tail(landing)
            if snake_tail is not None:
                hit_snake = True
                snake_loss = landing - snake_tail
                if use_shield:
                    shield_used = True
                    final_cell = landing  # Shield prevents sliding
                else:
                    final_cell = snake_tail
                    full_path.append(snake_tail)

        return {
            "path": full_path,
            "landing_cell": landing,
            "final_cell": final_cell,
            "hit_snake": hit_snake,
            "hit_ladder": hit_ladder,
            "shield_used": shield_used,
            "bounced": bounced,
            "snake_loss": snake_loss,
            "ladder_gain": ladder_gain,
        }

    @classmethod
    def is_game_over(cls, position: int) -> bool:
        """Returns True when a player has reached the final cell 100."""
        return position >= cls.WINNING_CELL
