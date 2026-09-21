"""
Tests for A* candidate evaluation, scoring ranges, and strategic heuristics.
"""

import pytest
from game.board import Board
from ai.bfs import BFSAnalyzer
from ai.astar import AStarScorer


def test_astar_score_range():
    board = Board()
    bfs = BFSAnalyzer(board)
    astar = AStarScorer(board, bfs)

    # Test arbitrary candidate moves
    for cell in (1, 20, 50, 80, 95):
        for roll in (1, 3, 5, 6):
            dest = board.calculate_destination(cell, roll)
            hit_ladder = board.is_ladder_bottom(cell + roll)
            hit_snake = board.is_snake_head(cell + roll)
            eval_res = astar.evaluate_candidate(cell, roll, dest, hit_ladder=hit_ladder, hit_snake=hit_snake)

            score = eval_res["astar_score"]
            assert 0.0 <= score <= 1.0, f"A* score {score} out of range [0, 1]"
            assert "g_cost" in eval_res
            assert "h_cost" in eval_res
            assert "f_cost" in eval_res


def test_astar_prefers_ladder_over_snake():
    board = Board()
    bfs = BFSAnalyzer(board)
    astar = AStarScorer(board, bfs)

    # Cell 28 has a ladder to 84
    ladder_dest = 84
    eval_ladder = astar.evaluate_candidate(28, 0, ladder_dest, hit_ladder=True, hit_snake=False)

    # Cell 87 has a snake to 24
    snake_dest = 24
    eval_snake = astar.evaluate_candidate(87, 0, snake_dest, hit_ladder=False, hit_snake=True)

    assert eval_ladder["astar_score"] > eval_snake["astar_score"]


def test_astar_winning_cell():
    board = Board()
    bfs = BFSAnalyzer(board)
    astar = AStarScorer(board, bfs)

    eval_win = astar.evaluate_candidate(95, 5, 100, hit_ladder=False, hit_snake=False)
    assert eval_win["astar_score"] >= 0.95
    assert eval_win["h_cost"] == 0.0
