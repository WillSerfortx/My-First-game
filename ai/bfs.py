"""Breadth-first search: shortest path (in rolls) from any cell to the goal."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from game.board import Board
from game.constants import GOAL_CELL, NUM_CELLS, START_CELL


@dataclass(frozen=True)
class BFSResult:
    start: int
    found: bool
    rolls: int                 # minimum number of rolls (best-case dice)
    path: tuple[int, ...]      # cells visited, including start and goal


def bfs_shortest_path(board: Board, start: int, goal: int = GOAL_CELL) -> BFSResult:
    """Classic BFS over ``board.graph`` (every edge costs one roll)."""
    if start == goal:
        return BFSResult(start, True, 0, (start,))
    parent: dict[int, int | None] = {start: None}
    queue: deque[int] = deque([start])
    while queue:
        cell = queue.popleft()
        for nxt in board.graph[cell]:
            if nxt in parent:
                continue
            parent[nxt] = cell
            if nxt == goal:
                path = [goal]
                while parent[path[-1]] is not None:
                    path.append(parent[path[-1]])  # type: ignore[arg-type]
                path.reverse()
                return BFSResult(start, True, len(path) - 1, tuple(path))
            queue.append(nxt)
    return BFSResult(start, False, -1, (start,))


class BFSAnalyzer:
    """Runs BFS from every cell once and caches ``min_rolls``."""

    def __init__(self, board: Board) -> None:
        self.board = board
        self._results: dict[int, BFSResult] = {
            cell: bfs_shortest_path(board, cell) for cell in range(START_CELL, NUM_CELLS + 1)
        }
        self.min_rolls_table: dict[int, int] = {c: r.rolls for c, r in self._results.items()}

    def min_rolls(self, cell: int) -> int:
        return self.min_rolls_table[cell]

    def path(self, cell: int) -> tuple[int, ...]:
        return self._results[cell].path
