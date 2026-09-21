"""
A* Search & Strategic Scorer module for AI-Powered Snake & Ladder.
Uses BFS shortest-path distance as an admissible heuristic h(s) combined with
board progress and ladder/snake outcomes to produce a normalized score in [0.0, 1.0].
"""

from typing import Dict, Any, Optional
from game.board import Board
from .bfs import BFSAnalyzer


class AStarScorer:
    """
    Evaluates candidate board states using A* pathfinding principles.
    """

    def __init__(self, board: Optional[Board] = None, bfs: Optional[BFSAnalyzer] = None):
        self.board: Board = board if board is not None else Board()
        self.bfs: BFSAnalyzer = bfs if bfs is not None else BFSAnalyzer(self.board)
        self.max_bfs_rolls: int = max(self.bfs.min_rolls.values()) if self.bfs.min_rolls else 8

    def evaluate_candidate(
        self,
        current_cell: int,
        roll: int,
        destination_cell: int,
        hit_ladder: bool = False,
        hit_snake: bool = False,
    ) -> Dict[str, Any]:
        """
        Evaluates a candidate move from current_cell to destination_cell.
        Returns detailed A* evaluation metrics and a normalized score in [0.0, 1.0].
        """
        # Step cost g(s'): 1 roll taken
        g_cost = 1.0

        # Admissible heuristic h(s'): minimum rolls from destination to 100
        h_cost = float(self.bfs.get_min_rolls(destination_cell))

        # Overall f(s') = g(s') + h(s')
        f_cost = g_cost + h_cost

        # Goal proximity component: cell 100 is 1.0, cell 1 is 0.01
        progress = destination_cell / float(self.board.TOTAL_CELLS)

        # Efficiency component based on heuristic: lower h_cost is better
        # Normalizes h_cost from 0 (at 100) to max_bfs_rolls (at worst cell)
        heuristic_score = max(0.0, 1.0 - (h_cost / float(self.max_bfs_rolls + 1)))

        # Strategic bonuses/penalties
        bonus = 0.0
        if destination_cell == self.board.TOTAL_CELLS:
            bonus += 0.25
        elif hit_ladder:
            bonus += 0.10
        elif hit_snake:
            bonus -= 0.15

        # Weighted combination: 60% heuristic efficiency, 30% board progress, 10% bonus
        raw_score = (0.60 * heuristic_score) + (0.30 * progress) + bonus
        normalized_score = max(0.01, min(1.0, raw_score))

        return {
            "roll": roll,
            "destination": destination_cell,
            "g_cost": g_cost,
            "h_cost": h_cost,
            "f_cost": f_cost,
            "min_rolls_to_goal": int(h_cost),
            "progress_pct": progress,
            "astar_score": round(float(normalized_score), 4),
        }
