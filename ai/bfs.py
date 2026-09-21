"""
BFS Module for AI-Powered Snake & Ladder.
Performs Breadth-First Search on the board graph to compute the minimum number of rolls
required to reach cell 100 from every cell on the board.
"""

from collections import deque
from typing import Dict, List, Optional
from game.board import Board


class BFSAnalyzer:
    """
    Computes and caches the shortest path (minimum dice rolls) from every cell to cell 100.
    """

    def __init__(self, board: Optional[Board] = None):
        self.board: Board = board if board is not None else Board()
        self.min_rolls: Dict[int, int] = {}
        self.optimal_moves: Dict[int, List[int]] = {}
        self.compute_all_min_rolls()

    def compute_all_min_rolls(self) -> Dict[int, int]:
        """
        Runs BFS for each cell 1..100 to determine the minimum rolls to reach 100.
        Cell 100 has 0 rolls required.
        """
        self.min_rolls = {100: 0}
        self.optimal_moves = {100: []}

        for cell in range(1, self.board.TOTAL_CELLS):
            dist, best_rolls = self._bfs_from_cell(cell)
            self.min_rolls[cell] = dist
            self.optimal_moves[cell] = best_rolls

        return self.min_rolls

    def _bfs_from_cell(self, start_cell: int) -> tuple[int, List[int]]:
        """
        Finds the shortest path from start_cell to 100 using standard BFS.
        Returns:
            min_rolls: Minimum number of rolls needed
            best_first_rolls: List of dice values 1..6 that achieve this minimum distance
        """
        if start_cell == self.board.TOTAL_CELLS:
            return 0, []

        queue: deque = deque([(start_cell, 0, None)])
        visited: Dict[int, int] = {start_cell: 0}
        first_roll_to_min: Dict[int, int] = {}

        min_distance = float("inf")

        while queue:
            curr, dist, first_roll = queue.popleft()

            if dist >= min_distance:
                continue

            for roll in range(1, 7):
                dest = self.board.calculate_destination(curr, roll)
                assigned_first = first_roll if first_roll is not None else roll

                if dest == self.board.TOTAL_CELLS:
                    total_rolls = dist + 1
                    if total_rolls < min_distance:
                        min_distance = total_rolls
                    if assigned_first not in first_roll_to_min or total_rolls < first_roll_to_min[assigned_first]:
                        first_roll_to_min[assigned_first] = total_rolls
                    continue

                if dest not in visited or dist + 1 < visited[dest]:
                    visited[dest] = dist + 1
                    queue.append((dest, dist + 1, assigned_first))

        if min_distance == float("inf"):
            # Fallback theoretical estimate based on remaining distance
            min_distance = max(1, (self.board.TOTAL_CELLS - start_cell + 5) // 6)
            best_rolls = [6]
        else:
            best_rolls = [r for r, d in first_roll_to_min.items() if d == min_distance]

        return int(min_distance), best_rolls

    def get_min_rolls(self, cell: int) -> int:
        """Returns the minimum rolls to 100 for a given cell."""
        return self.min_rolls.get(cell, max(1, (100 - cell + 5) // 6))

    def get_optimal_rolls(self, cell: int) -> List[int]:
        """Returns the list of first rolls (1..6) that yield the minimum path to 100."""
        return self.optimal_moves.get(cell, [6])
