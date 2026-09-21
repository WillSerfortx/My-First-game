"""Random-play simulation that produces the machine-learning training data.

Each game is played by two random players that follow the *real* rules
(two dice -> choose one at random, exact finish, snakes, ladders, 2 shields
used with probability 0.5 when a snake is hit). Every cell a player visits
(the landing cell and, after a jump, the destination cell) becomes one row,
labelled ``won = 1`` if that player eventually won the game, else ``0``.
"""
from __future__ import annotations

import random
from array import array
from dataclasses import dataclass
from typing import Callable

import numpy as np

from game.board import Board
from game.constants import GOAL_CELL, SHIELDS_PER_PLAYER, SIMULATED_GAMES, SIMULATION_SEED, START_CELL

from .features import FEATURE_NAMES

ProgressCallback = Callable[[float], None]
MAX_TURNS_PER_PLAYER = 1000


@dataclass
class TrainingData:
    """Raw simulation output (compact integer form)."""
    cells: np.ndarray        # uint8, visited cell (1..100)
    won: np.ndarray          # uint8, 1 if the visiting player won that game
    game_id: np.ndarray      # uint16
    player: np.ndarray       # uint8, 0 = first mover, 1 = second mover
    n_games: int
    avg_game_length: float   # average turns (both players) per finished game

    @property
    def n_rows(self) -> int:
        return int(self.cells.size)


def simulate_games(board: Board, n_games: int = SIMULATED_GAMES,
                   seed: int = SIMULATION_SEED, shield_prob: float = 0.5,
                   progress: ProgressCallback | None = None) -> TrainingData:
    """Simulate ``n_games`` random games and collect visited cells."""
    rng = random.Random(seed)
    rand, randint = rng.random, rng.randint
    table = board.move_table
    cells = bytearray()
    won_flags = bytearray()
    game_ids = array("H")
    players = bytearray()
    total_turns = 0
    finished = 0

    for game in range(n_games):
        pos = [START_CELL, START_CELL]
        shields = [SHIELDS_PER_PLAYER, SHIELDS_PER_PLAYER]
        visits: list[list[int]] = [[], []]
        winner = -1
        p = 0
        for turn in range(MAX_TURNS_PER_PLAYER * 2):
            row = table[pos[p]]
            first, second = row[randint(1, 6)], row[randint(1, 6)]
            if first and second:
                move = first if rand() < 0.5 else second
            else:
                move = first or second
            if move:
                landing, dest, is_snake = move
                if is_snake and shields[p] and rand() < shield_prob:
                    shields[p] -= 1
                    dest = landing
                visits[p].append(landing)
                if dest != landing:
                    visits[p].append(dest)
                pos[p] = dest
                if dest == GOAL_CELL:
                    winner = p
                    total_turns += turn + 1
                    break
            p ^= 1
        if winner < 0:
            continue                       # extremely unlikely; drop unfinished games
        finished += 1
        for pl in (0, 1):
            n = len(visits[pl])
            cells.extend(visits[pl])
            won_flags.extend(b"\x01" * n if pl == winner else b"\x00" * n)
            game_ids.extend(array("H", [game]) * n)
            players.extend(bytes([pl]) * n)
        if progress and game % 250 == 0:
            progress(game / n_games)
    if progress:
        progress(1.0)

    return TrainingData(
        cells=np.frombuffer(bytes(cells), dtype=np.uint8).copy(),
        won=np.frombuffer(bytes(won_flags), dtype=np.uint8).copy(),
        game_id=np.frombuffer(game_ids.tobytes(), dtype=np.uint16).copy(),
        player=np.frombuffer(bytes(players), dtype=np.uint8).copy(),
        n_games=finished,
        avg_game_length=total_turns / max(1, finished),
    )


def build_feature_dataset(data: TrainingData, feature_matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Expand visited cells into the (X, y) training matrix.

    ``feature_matrix`` has shape (100, 5) with row ``cell - 1``.
    Columns of X follow :data:`ai.features.FEATURE_NAMES`.
    """
    X = feature_matrix[data.cells.astype(np.int64) - 1].astype(np.float32)
    y = data.won.astype(np.int8)
    return X, y


def dataset_sample_csv(path: str, X: np.ndarray, y: np.ndarray, rows: int = 2000) -> None:
    """Write a human-readable sample of the training set."""
    header = ",".join(FEATURE_NAMES) + ",won"
    sample = np.column_stack([X[:rows], y[:rows]])
    np.savetxt(path, sample, delimiter=",", header=header, comments="",
               fmt=["%.0f", "%.0f", "%.0f", "%.0f", "%.1f", "%d"])
