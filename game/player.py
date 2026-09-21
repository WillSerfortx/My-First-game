"""
Player module for AI-Powered Snake & Ladder.
Defines player state, positions, shield inventory, statistics, and visual interpolation.
"""

from typing import Tuple, List, Optional


class Player:
    """
    Represents a player (Human or AI) in the Snake & Ladder game.
    """

    def __init__(
        self,
        name: str,
        is_ai: bool,
        primary_color: Tuple[int, int, int],
        secondary_color: Tuple[int, int, int],
        initial_shields: int = 2,
    ):
        self.name: str = name
        self.is_ai: bool = is_ai
        self.primary_color: Tuple[int, int, int] = primary_color
        self.secondary_color: Tuple[int, int, int] = secondary_color
        self.initial_shields: int = initial_shields

        self.position: int = 1
        self.shields: int = initial_shields

        # Visual animation state
        self.visual_cell: float = 1.0
        self.target_cell: float = 1.0
        self.move_path: List[int] = []
        self.is_animating: bool = False
        self.glow_timer: float = 0.0

        # Game statistics
        self.turns_played: int = 0
        self.snakes_encountered: int = 0
        self.ladders_climbed: int = 0
        self.shields_used: int = 0
        self.total_dice_rolls: int = 0
        self.history: List[int] = [1]

    def reset(self) -> None:
        """Resets the player state for a new game."""
        self.position = 1
        self.shields = self.initial_shields
        self.visual_cell = 1.0
        self.target_cell = 1.0
        self.move_path = []
        self.is_animating = False
        self.glow_timer = 0.0

        self.turns_played = 0
        self.snakes_encountered = 0
        self.ladders_climbed = 0
        self.shields_used = 0
        self.total_dice_rolls = 0
        self.history = [1]

    def queue_movement_path(self, path: List[int]) -> None:
        """
        Queues a sequence of cells for animated movement.
        Path should include all intermediate step cells, plus any ladder/snake transitions.
        """
        self.move_path = list(path)
        if self.move_path:
            self.target_cell = float(self.move_path.pop(0))
            self.is_animating = True

    def update_animation(self, dt: float) -> bool:
        """
        Updates smooth visual interpolation towards the current target cell.
        Returns True when all queued movement animations have completed.
        """
        self.glow_timer += dt

        if not self.is_animating:
            return True

        speed = 24.0 * dt  # cells per second
        diff = self.target_cell - self.visual_cell

        if abs(diff) <= speed:
            self.visual_cell = self.target_cell
            if self.move_path:
                self.target_cell = float(self.move_path.pop(0))
            else:
                self.is_animating = False
                self.position = int(round(self.visual_cell))
                return True
        else:
            self.visual_cell += speed if diff > 0 else -speed

        return False

    def use_shield(self) -> bool:
        """Consumes a shield if available."""
        if self.shields > 0:
            self.shields -= 1
            self.shields_used += 1
            return True
        return False

    def has_shields(self) -> bool:
        return self.shields > 0

    def record_turn(self, new_pos: int, hit_snake: bool, hit_ladder: bool, used_shield: bool) -> None:
        """Updates player game statistics after a move."""
        self.turns_played += 1
        self.position = new_pos
        self.history.append(new_pos)
        if hit_snake:
            self.snakes_encountered += 1
        if hit_ladder:
            self.ladders_climbed += 1
        if used_shield:
            # Shield tracking is handled in use_shield()
            pass
