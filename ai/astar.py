"""A* search with a risk-aware cost, used to score candidate positions.

Search space: the board graph restricted to *snake-free* edges (a route may
not land on a snake head). Edge cost for stepping onto cell ``m``::

    cost(m) = 1 + EXPOSURE_WEIGHT * snakes_within_6(m) / 6

i.e. one roll plus the probability that the *next* single-die roll would hit a
snake from ``m``. The heuristic is the BFS minimum-roll table computed on the
full graph, which is admissible and consistent (every edge costs >= 1 and the
snake-free graph is a subgraph of the full graph).
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass

from game.board import Board, SpecialKind
from game.constants import DICE_SIDES, GOAL_CELL, NUM_CELLS, START_CELL

from .bfs import BFSAnalyzer
from .features import FeatureExtractor

EXPOSURE_WEIGHT = 1.0
UNREACHABLE_PENALTY = 5.0   # only used if no snake-free route exists


@dataclass(frozen=True)
class AStarResult:
    start: int
    found: bool
    path: tuple[int, ...]
    rolls: int          # number of rolls along the found path
    cost: float         # risk-adjusted cost (>= rolls)
    expanded: int       # nodes expanded (search effort)


def astar_search(board: Board, start: int, goal: int, heuristic, edge_cost,
                 allow_snakes: bool = False) -> AStarResult:
    """Generic A* over the board graph."""
    if start == goal:
        return AStarResult(start, True, (start,), 0, 0.0, 0)
    counter = 0
    open_heap: list[tuple[float, float, int, int]] = [(heuristic(start), 0.0, counter, start)]
    best_g: dict[int, float] = {start: 0.0}
    parent: dict[int, int | None] = {start: None}
    closed: set[int] = set()
    expanded = 0
    while open_heap:
        _, neg_g, _, cell = heapq.heappop(open_heap)
        g = -neg_g
        if cell in closed:
            continue
        closed.add(cell)
        expanded += 1
        if cell == goal:
            path = [cell]
            while parent[path[-1]] is not None:
                path.append(parent[path[-1]])  # type: ignore[arg-type]
            path.reverse()
            return AStarResult(start, True, tuple(path), len(path) - 1, g, expanded)
        for edge in board.edges[cell]:
            if edge.kind is SpecialKind.SNAKE and not allow_snakes:
                continue
            nxt = edge.destination
            ng = g + edge_cost(nxt)
            if nxt not in best_g or ng < best_g[nxt] - 1e-12:
                best_g[nxt] = ng
                parent[nxt] = cell
                counter += 1
                # negative g as tie-breaker => prefer deeper nodes on equal f
                heapq.heappush(open_heap, (ng + heuristic(nxt), -ng, counter, nxt))
    return AStarResult(start, False, (start,), -1, float("inf"), expanded)


class AStarScorer:
    """Turns A* route costs into a normalised 0..1 desirability score."""

    def __init__(self, board: Board, bfs: BFSAnalyzer, features: FeatureExtractor) -> None:
        self.board = board
        self.bfs = bfs
        self.features = features
        self._cache: dict[int, AStarResult] = {}
        for cell in range(START_CELL, NUM_CELLS + 1):
            self._cache[cell] = self._run(cell)
        self.max_cost = max(r.cost for c, r in self._cache.items() if c != GOAL_CELL)

    def _edge_cost(self, cell: int) -> float:
        return 1.0 + EXPOSURE_WEIGHT * self.features.snakes_within_6(cell) / DICE_SIDES

    def _run(self, cell: int) -> AStarResult:
        res = astar_search(self.board, cell, GOAL_CELL, self.bfs.min_rolls,
                           self._edge_cost, allow_snakes=False)
        if res.found:
            return res
        fallback = astar_search(self.board, cell, GOAL_CELL, self.bfs.min_rolls,
                                self._edge_cost, allow_snakes=True)
        return AStarResult(cell, fallback.found, fallback.path, fallback.rolls,
                           fallback.cost + UNREACHABLE_PENALTY, fallback.expanded)

    def result(self, cell: int) -> AStarResult:
        return self._cache[cell]

    def score(self, cell: int) -> float:
        """1.0 at the goal, approaching 0.0 for the costliest cells."""
        cost = self._cache[cell].cost
        return float(min(1.0, max(0.0, 1.0 - cost / self.max_cost)))
