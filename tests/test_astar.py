from ai.astar import AStarScorer, astar_search
from ai.bfs import BFSAnalyzer
from ai.features import FeatureExtractor
from game.board import Board, SpecialKind
from game.constants import GOAL_CELL


def build():
    board = Board()
    features = FeatureExtractor(board)
    bfs = BFSAnalyzer(board)
    return board, bfs, AStarScorer(board, bfs, features)


def test_scores_are_normalised_and_goal_is_best():
    board, _bfs, scorer = build()
    scores = [scorer.score(c) for c in range(1, 101)]
    assert all(0.0 <= s <= 1.0 for s in scores)
    assert scorer.score(GOAL_CELL) == 1.0
    assert scorer.score(99) > scorer.score(50) > scorer.score(1)


def test_path_is_valid_and_snake_free():
    board, _bfs, scorer = build()
    for cell in (1, 10, 33, 57, 88):
        res = scorer.result(cell)
        assert res.found and res.path[0] == cell and res.path[-1] == GOAL_CELL
        for a, b in zip(res.path, res.path[1:]):
            edges = [e for e in board.edges[a] if e.destination == b]
            assert edges and any(e.kind is not SpecialKind.SNAKE for e in edges)


def test_astar_cost_is_at_least_bfs_minimum():
    board, bfs, scorer = build()
    for cell in range(1, 100):
        res = scorer.result(cell)
        assert res.rolls >= bfs.min_rolls(cell)
        assert res.cost >= bfs.min_rolls(cell) - 1e-9     # heuristic admissibility


def test_astar_matches_bfs_with_unit_costs_when_snakes_allowed():
    board, bfs, _scorer = build()
    for cell in (1, 20, 45, 70, 95):
        res = astar_search(board, cell, GOAL_CELL, bfs.min_rolls, lambda _c: 1.0, allow_snakes=True)
        assert res.found and res.rolls == bfs.min_rolls(cell)


def test_candidate_scoring_prefers_ladder_result():
    _board, _bfs, scorer = build()
    # 4 -> ladder to 14 is far better than staying on plain cell 5
    assert scorer.score(14) > scorer.score(5)
