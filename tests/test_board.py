import pytest

from game.board import Board, SpecialKind
from game.constants import LADDERS, NUM_CELLS, SNAKES


def test_board_has_100_cells_and_graph_nodes():
    board = Board()
    assert NUM_CELLS == 100
    assert sorted(board.graph) == list(range(1, 101))


def test_snake_and_ladder_counts_and_positions():
    board = Board()
    assert len(board.snakes) == 10
    assert len(board.ladders) == 9
    assert board.snakes == SNAKES and board.ladders == LADDERS
    assert all(head > tail for head, tail in board.snakes.items())
    assert all(bottom < top for bottom, top in board.ladders.items())


def test_graph_construction_applies_redirections():
    board = Board()
    # from 10 rolling a 6 lands on snake head 16 -> tail 6
    assert board.graph[10][5] == 6
    # from 1 rolling a 1 lands on ladder bottom 2 -> top 38
    assert board.graph[1][0] == 38
    edge = board.edge(10, 6)
    assert edge.landing == 16 and edge.destination == 6 and edge.kind is SpecialKind.SNAKE


def test_graph_has_no_overshoot_edges():
    board = Board()
    assert board.graph[100] == []
    assert len(board.graph[99]) == 1 and board.graph[99] == [100]
    assert len(board.graph[96]) == 4          # rolls 1..4 only


def test_grid_layout_is_boustrophedon_and_bijective():
    seen = set()
    for cell in range(1, 101):
        row, col = Board.cell_to_grid(cell)
        assert 0 <= row < 10 and 0 <= col < 10
        assert Board.grid_to_cell(row, col) == cell
        seen.add((row, col))
    assert len(seen) == 100
    assert Board.cell_to_grid(1) == (0, 0)
    assert Board.cell_to_grid(10) == (0, 9)
    assert Board.cell_to_grid(11) == (1, 9)      # second row runs right -> left
    assert Board.cell_to_grid(100) == (9, 0)


def test_invalid_layouts_are_rejected():
    with pytest.raises(ValueError):
        Board(snakes={10: 20}, ladders={})            # snake going up
    with pytest.raises(ValueError):
        Board(snakes={30: 10}, ladders={30: 50})      # shared cell
    with pytest.raises(ValueError):
        Board(snakes={30: 10}, ladders={10: 40})      # chained jumps
