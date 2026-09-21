"""
Tests for Board structure, 10 snakes, 9 ladders, graph construction, and coordinate mappings.
"""

import pytest
from game.board import Board


def test_board_cell_counts():
    board = Board()
    assert board.TOTAL_CELLS == 100
    assert board.GRID_SIZE == 10


def test_board_snakes_and_ladders_counts():
    board = Board()
    assert len(board.snakes) == 10, f"Expected 10 snakes, got {len(board.snakes)}"
    assert len(board.ladders) == 9, f"Expected 9 ladders, got {len(board.ladders)}"

    # Check snake heads are greater than tails
    for head, tail in board.snakes.items():
        assert head > tail, f"Snake head {head} must be greater than tail {tail}"
        assert 1 <= head <= 100
        assert 1 <= tail <= 100

    # Check ladder bottoms are lower than tops
    for bottom, top in board.ladders.items():
        assert bottom < top, f"Ladder bottom {bottom} must be less than top {top}"
        assert 1 <= bottom <= 100
        assert 1 <= top <= 100

    # Ensure no cell is both a snake head and a ladder bottom
    overlap = set(board.snakes.keys()).intersection(set(board.ladders.keys()))
    assert len(overlap) == 0, f"Overlapping snake head and ladder bottom: {overlap}"


def test_board_coordinates():
    board = Board()
    # Cell 1 at bottom-left: col=0, row=9
    assert board.get_cell_coordinates(1) == (0, 9)
    # Cell 10 at bottom-right: col=9, row=9
    assert board.get_cell_coordinates(10) == (9, 9)
    # Cell 11 at row above, reversed: col=9, row=8
    assert board.get_cell_coordinates(11) == (9, 8)
    # Cell 20 at col=0, row=8
    assert board.get_cell_coordinates(20) == (0, 8)
    # Cell 100 at top-left: col=0, row=0
    assert board.get_cell_coordinates(100) == (0, 0)


def test_graph_adjacency_structure():
    board = Board()
    assert len(board.graph) == 100

    for cell in range(1, 101):
        assert cell in board.graph
        for roll in range(1, 7):
            dest = board.graph[cell][roll]
            assert 1 <= dest <= 100
