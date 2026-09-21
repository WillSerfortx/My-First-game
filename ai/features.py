"""Per-cell feature engineering (five features per cell)."""
from __future__ import annotations

import numpy as np

from game.board import Board
from game.constants import DIST_CAP, NEAR_WINDOW, NUM_CELLS

FEATURE_NAMES: tuple[str, ...] = (
    "dist_to_snake",
    "dist_to_ladder",
    "snakes_within_6",
    "ladders_within_6",
    "position_pct",
)

FEATURE_DESCRIPTIONS: dict[str, str] = {
    "dist_to_snake": f"Cells to the nearest snake head ahead (capped at {DIST_CAP})",
    "dist_to_ladder": f"Cells to the nearest ladder bottom ahead (capped at {DIST_CAP})",
    "snakes_within_6": "Snake heads within one die roll (6 cells) ahead",
    "ladders_within_6": "Ladder bottoms within one die roll (6 cells) ahead",
    "position_pct": "Board progress in percent (cell / 100 * 100)",
}


class FeatureExtractor:
    """Computes and caches the 5-feature vector for every cell."""

    def __init__(self, board: Board) -> None:
        self.board = board
        self._matrix = np.vstack([self._compute(c) for c in range(1, NUM_CELLS + 1)])

    def _compute(self, cell: int) -> np.ndarray:
        b = self.board
        snakes = b.snake_heads_ahead(cell)
        ladders = b.ladder_bottoms_ahead(cell)
        dist_snake = min(snakes[0] - cell, DIST_CAP) if snakes else DIST_CAP
        dist_ladder = min(ladders[0] - cell, DIST_CAP) if ladders else DIST_CAP
        return np.array([
            dist_snake,
            dist_ladder,
            len(b.snake_heads_ahead(cell, NEAR_WINDOW)),
            len(b.ladder_bottoms_ahead(cell, NEAR_WINDOW)),
            cell / NUM_CELLS * 100.0,
        ], dtype=np.float64)

    def features_for(self, cell: int) -> np.ndarray:
        """Feature vector (shape ``(5,)``) of a cell."""
        return self._matrix[cell - 1].copy()

    def matrix(self) -> np.ndarray:
        """Feature matrix for cells 1..100 (shape ``(100, 5)``, row = cell - 1)."""
        return self._matrix.copy()

    def snakes_within_6(self, cell: int) -> int:
        return int(self._matrix[cell - 1, 2])
