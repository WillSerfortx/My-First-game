"""Board model: a 10x10 Snake & Ladder board represented as a directed graph."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum

from .constants import (
    BOARD_SIZE, DICE_SIDES, GOAL_CELL, LADDERS, NUM_CELLS, SNAKES, START_CELL,
)


class SpecialKind(Enum):
    """What a landing cell does."""
    NONE = "none"
    SNAKE = "snake"
    LADDER = "ladder"


@dataclass(frozen=True)
class Edge:
    """One graph edge: rolling ``die`` from a cell.

    ``landing`` is the cell reached by walking; ``destination`` is where the
    player ends up after the snake/ladder (if any) is applied.
    """
    die: int
    landing: int
    destination: int
    kind: SpecialKind


class Board:
    """Directed graph over cells 1..100.

    ``graph[cell]`` is the adjacency list of destination cells reachable with
    one die roll (1..6). Rolls that would overshoot cell 100 produce no edge
    (exact finish is required). Snake/ladder redirections are already applied
    to the destinations, so BFS/A*/simulation all share the same structure.
    """

    def __init__(self, snakes: dict[int, int] | None = None,
                 ladders: dict[int, int] | None = None) -> None:
        self.snakes: dict[int, int] = dict(SNAKES if snakes is None else snakes)
        self.ladders: dict[int, int] = dict(LADDERS if ladders is None else ladders)
        self._validate()
        self.jumps: dict[int, int] = {**self.snakes, **self.ladders}
        self.edges: dict[int, list[Edge]] = {}
        self.graph: dict[int, list[int]] = {}
        # move_table[cell][die] = (landing, destination, is_snake) or None -- fast path for simulation
        self.move_table: list[list[tuple[int, int, bool] | None]] = []
        self._build_graph()
        self._snake_heads_sorted = sorted(self.snakes)
        self._ladder_bottoms_sorted = sorted(self.ladders)

    # ------------------------------------------------------------------ setup
    def _validate(self) -> None:
        for head, tail in self.snakes.items():
            if not (START_CELL < tail < head < GOAL_CELL):
                raise ValueError(f"Invalid snake {head}->{tail}")
        for bottom, top in self.ladders.items():
            if not (START_CELL < bottom < top <= GOAL_CELL):
                raise ValueError(f"Invalid ladder {bottom}->{top}")
        overlap = set(self.snakes) & set(self.ladders)
        if overlap:
            raise ValueError(f"Cells used by both a snake and a ladder: {sorted(overlap)}")
        starts = set(self.snakes) | set(self.ladders)
        ends = set(self.snakes.values()) | set(self.ladders.values())
        chained = starts & ends
        if chained:
            raise ValueError(f"Chained jumps are not allowed: {sorted(chained)}")

    def _build_graph(self) -> None:
        self.move_table = [[None] * (DICE_SIDES + 1) for _ in range(NUM_CELLS + 1)]
        for cell in range(START_CELL, NUM_CELLS + 1):
            edges: list[Edge] = []
            for die in range(1, DICE_SIDES + 1):
                landing = cell + die
                if landing > GOAL_CELL:
                    continue
                kind = self.kind_at(landing)
                dest = self.jumps.get(landing, landing)
                edges.append(Edge(die, landing, dest, kind))
                self.move_table[cell][die] = (landing, dest, kind is SpecialKind.SNAKE)
            self.edges[cell] = edges
            self.graph[cell] = [e.destination for e in edges]

    # ---------------------------------------------------------------- queries
    def kind_at(self, cell: int) -> SpecialKind:
        if cell in self.snakes:
            return SpecialKind.SNAKE
        if cell in self.ladders:
            return SpecialKind.LADDER
        return SpecialKind.NONE

    def edge(self, cell: int, die: int) -> Edge | None:
        """Edge for rolling ``die`` from ``cell`` (None when it overshoots)."""
        for e in self.edges.get(cell, ()):
            if e.die == die:
                return e
        return None

    def snake_heads_ahead(self, cell: int, window: int | None = None) -> list[int]:
        """Snake heads strictly ahead of ``cell`` (optionally within ``window``)."""
        return [h for h in self._snake_heads_sorted
                if h > cell and (window is None or h - cell <= window)]

    def ladder_bottoms_ahead(self, cell: int, window: int | None = None) -> list[int]:
        return [b for b in self._ladder_bottoms_sorted
                if b > cell and (window is None or b - cell <= window)]

    def signature(self) -> str:
        """Stable hash of the board layout (used to invalidate caches)."""
        payload = json.dumps([sorted(self.snakes.items()), sorted(self.ladders.items())])
        return hashlib.sha1(payload.encode()).hexdigest()[:12]

    # --------------------------------------------------------------- geometry
    @staticmethod
    def cell_to_grid(cell: int) -> tuple[int, int]:
        """(row_from_bottom, column) with boustrophedon numbering."""
        if not START_CELL <= cell <= NUM_CELLS:
            raise ValueError(f"cell out of range: {cell}")
        idx = cell - 1
        row, col = divmod(idx, BOARD_SIZE)
        if row % 2 == 1:
            col = BOARD_SIZE - 1 - col
        return row, col

    @staticmethod
    def grid_to_cell(row: int, col: int) -> int:
        actual_col = col if row % 2 == 0 else BOARD_SIZE - 1 - col
        return row * BOARD_SIZE + actual_col + 1
