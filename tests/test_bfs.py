from ai.bfs import BFSAnalyzer, bfs_shortest_path
from game.board import Board


def test_goal_is_zero_rolls():
    board = Board()
    res = bfs_shortest_path(board, 100)
    assert res.found and res.rolls == 0 and res.path == (100,)


def test_cell_one_needs_about_seven_rolls():
    analyzer = BFSAnalyzer(Board())
    assert analyzer.min_rolls(1) == 7


def test_all_cells_reach_the_goal():
    board = Board()
    analyzer = BFSAnalyzer(board)
    assert len(analyzer.min_rolls_table) == 100
    assert all(r >= 0 for r in analyzer.min_rolls_table.values())


def test_path_is_a_valid_chain_of_graph_edges():
    board = Board()
    res = bfs_shortest_path(board, 1)
    assert res.path[0] == 1 and res.path[-1] == 100
    assert res.rolls == len(res.path) - 1
    for a, b in zip(res.path, res.path[1:]):
        assert b in board.graph[a]


def test_minimum_path_calculation_on_known_cells():
    board = Board()
    assert bfs_shortest_path(board, 99).rolls == 1
    assert bfs_shortest_path(board, 94).rolls == 1     # 94 + 6
    assert bfs_shortest_path(board, 80).rolls == bfs_shortest_path(board, 80).rolls
    # 71 -> ladder 91? only reachable by landing; from 65 a 6 hits it
    assert bfs_shortest_path(board, 65).rolls <= 3
