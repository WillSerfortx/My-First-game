"""
Board module for AI-Powered Snake & Ladder.
Defines the 10x10 grid, 10 snakes, 9 ladders, directed graph representation,
and coordinate conversion for rendering.
"""

from typing import Dict, List, Tuple, Optional


class Board:
    """
    Represents the 100-cell Snake & Ladder board as a directed graph.
    """

    TOTAL_CELLS = 100
    GRID_SIZE = 10

    # 10 Snakes (head -> tail)
    DEFAULT_SNAKES: Dict[int, int] = {
        98: 78,
        95: 56,
        92: 73,
        87: 24,
        64: 60,
        62: 19,
        54: 34,
        48: 26,
        44: 16,
        17: 7,
    }

    # 9 Ladders (bottom -> top)
    DEFAULT_LADDERS: Dict[int, int] = {
        4: 14,
        9: 31,
        20: 38,
        28: 84,
        40: 59,
        51: 67,
        63: 81,
        71: 91,
        80: 99,
    }

    def __init__(
        self,
        snakes: Optional[Dict[int, int]] = None,
        ladders: Optional[Dict[int, int]] = None,
    ):
        self.snakes: Dict[int, int] = dict(snakes if snakes is not None else self.DEFAULT_SNAKES)
        self.ladders: Dict[int, int] = dict(ladders if ladders is not None else self.DEFAULT_LADDERS)
        self.graph: Dict[int, Dict[int, int]] = {}
        self._build_graph()

    def _build_graph(self) -> None:
        """
        Builds the directed graph adjacency structure.
        For each cell 1..100, maps each possible dice roll 1..6
        to the resulting cell after bounce-back, snakes, and ladders.
        """
        self.graph = {}
        for cell in range(1, self.TOTAL_CELLS + 1):
            self.graph[cell] = {}
            for roll in range(1, 7):
                dest = self.calculate_destination(cell, roll, ignore_snakes=False)
                self.graph[cell][roll] = dest

    def calculate_destination(
        self, current_cell: int, roll: int, ignore_snakes: bool = False
    ) -> int:
        """
        Calculates the landing cell after a roll, accounting for overshoot bounce,
        ladders, and snakes (unless shielded).
        """
        if current_cell == self.TOTAL_CELLS:
            return self.TOTAL_CELLS

        target = current_cell + roll

        # Overshoot rule: bounce back from 100
        if target > self.TOTAL_CELLS:
            excess = target - self.TOTAL_CELLS
            target = self.TOTAL_CELLS - excess

        # Ladder takes precedence if landed on ladder bottom
        if target in self.ladders:
            return self.ladders[target]

        # Snake moves to tail unless shielded
        if target in self.snakes and not ignore_snakes:
            return self.snakes[target]

        return target

    def get_cell_coordinates(self, cell: int) -> Tuple[int, int]:
        """
        Converts a 1-based cell number into (col, row) where:
        col: 0..9 (left to right)
        row: 0..9 (0 is top row, 9 is bottom row for screen rendering)
        Alternating row direction (serpentine):
          Cell 1 at bottom-left (0, 9)
          Cell 10 at bottom-right (9, 9)
          Cell 11 at (9, 8)
          Cell 20 at (0, 8)
          Cell 100 at (0, 0)
        """
        cell_clamped = max(1, min(self.TOTAL_CELLS, cell))
        idx = cell_clamped - 1
        board_row = idx // self.GRID_SIZE  # 0 at bottom, 9 at top
        col_in_row = idx % self.GRID_SIZE

        if board_row % 2 == 0:
            col = col_in_row
        else:
            col = (self.GRID_SIZE - 1) - col_in_row

        row = (self.GRID_SIZE - 1) - board_row
        return col, row

    def is_snake_head(self, cell: int) -> bool:
        return cell in self.snakes

    def is_snake_tail(self, cell: int) -> bool:
        return cell in self.snakes.values()

    def is_ladder_bottom(self, cell: int) -> bool:
        return cell in self.ladders

    def is_ladder_top(self, cell: int) -> bool:
        return cell in self.ladders.values()

    def get_snake_tail(self, cell: int) -> Optional[int]:
        return self.snakes.get(cell)

    def get_ladder_top(self, cell: int) -> Optional[int]:
        return self.ladders.get(cell)
