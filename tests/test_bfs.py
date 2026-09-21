"""
Tests for BFS Shortest Path analysis and minimum rolls calculation.
"""

import pytest
from game.board import Board
from ai.bfs import BFSAnalyzer


def test_bfs_goal_and_start():
    board = Board()
    bfs = BFSAnalyzer(board)

    # Goal requires 0 rolls
    assert bfs.get_min_rolls(100) == 0

    # Cell 1 requires approximately 7 rolls (specification benchmark)
    c1_rolls = bfs.get_min_rolls(1)
    assert 5 <= c1_rolls <= 9, f"Expected cell 1 min rolls around 7, got {c1_rolls}"


def test_bfs_all_cells_reachable():
    board = Board()
    bfs = BFSAnalyzer(board)

    for cell in range(1, 101):
        rolls = bfs.get_min_rolls(cell)
        assert rolls >= 0
        if cell < 100:
            assert rolls > 0
            best_moves = bfs.get_optimal_rolls(cell)
            assert len(best_moves) > 0
            for r in best_moves:
                assert 1 <= r <= 6


def test_bfs_monotonic_proximity():
    board = Board()
    bfs = BFSAnalyzer(board)

    # From 99, 1 roll of 1 reaches 100
    assert bfs.get_min_rolls(99) == 1
    # From 94, roll of 6 reaches 100
    assert bfs.get_min_rolls(94) == 1
