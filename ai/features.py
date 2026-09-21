"""
Feature extraction module for AI-Powered Snake & Ladder.
Computes the 5 mandatory ML features for any cell on the 100-cell board:
1. dist_to_snake: Distance to nearest relevant snake head ahead
2. dist_to_ladder: Distance to nearest relevant ladder base ahead
3. snakes_within_6: Count of snake heads within roll range (next 6 cells)
4. ladders_within_6: Count of ladder bases within roll range (next 6 cells)
5. position_pct: Current position as board percentage (cell / 100.0)
"""

from typing import List, Dict, Optional, Union
import numpy as np
from game.board import Board


class FeatureExtractor:
    """
    Extracts the 5 strategic features for any board cell or batch of cells.
    """

    FEATURE_NAMES: List[str] = [
        "dist_to_snake",
        "dist_to_ladder",
        "snakes_within_6",
        "ladders_within_6",
        "position_pct",
    ]

    def __init__(self, board: Optional[Board] = None):
        self.board: Board = board if board is not None else Board()
        self.snake_heads: List[int] = sorted(self.board.snakes.keys())
        self.ladder_bases: List[int] = sorted(self.board.ladders.keys())

        # Precompute features for all 100 cells for lightning-fast lookup
        self._cell_features: np.ndarray = np.zeros((self.board.TOTAL_CELLS + 1, 5), dtype=np.float64)
        self._precompute_all()

    def _precompute_all(self) -> None:
        """Precomputes feature vectors for cells 1 through 100."""
        for c in range(1, self.board.TOTAL_CELLS + 1):
            self._cell_features[c] = self._extract_raw(c)

    def _extract_raw(self, cell: int) -> np.ndarray:
        """Computes the 5 features for a single cell."""
        # 1. Distance to nearest snake head ahead
        snakes_ahead = [h - cell for h in self.snake_heads if h > cell]
        dist_to_snake = min(snakes_ahead) if snakes_ahead else 100.0

        # 2. Distance to nearest ladder bottom ahead
        ladders_ahead = [b - cell for b in self.ladder_bases if b > cell]
        dist_to_ladder = min(ladders_ahead) if ladders_ahead else 100.0

        # 3. Snakes within next 6 cells (immediate threat window)
        snakes_w6 = sum(1 for h in self.snake_heads if cell < h <= min(100, cell + 6))

        # 4. Ladders within next 6 cells (immediate opportunity window)
        ladders_w6 = sum(1 for b in self.ladder_bases if cell < b <= min(100, cell + 6))

        # 5. Position progress percentage
        pos_pct = cell / float(self.board.TOTAL_CELLS)

        return np.array([
            float(dist_to_snake),
            float(dist_to_ladder),
            float(snakes_w6),
            float(ladders_w6),
            float(pos_pct),
        ], dtype=np.float64)

    def extract_cell(self, cell: int) -> np.ndarray:
        """Returns the 5-element feature vector for a given cell (1..100)."""
        clamped = max(1, min(self.board.TOTAL_CELLS, int(cell)))
        return self._cell_features[clamped].copy()

    def extract_dict(self, cell: int) -> Dict[str, float]:
        """Returns the features as a human-readable dictionary."""
        feats = self.extract_cell(cell)
        return {
            self.FEATURE_NAMES[i]: float(feats[i])
            for i in range(len(self.FEATURE_NAMES))
        }

    def extract_all_cells(self) -> np.ndarray:
        """Returns a (100, 5) numpy matrix for cells 1 to 100."""
        return self._cell_features[1:].copy()
