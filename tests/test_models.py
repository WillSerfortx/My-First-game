import numpy as np

from ai.data_generator import build_feature_dataset, simulate_games
from ai.decision_engine import DecisionEngine
from ai.features import FeatureExtractor
from game.board import Board
from tests.helpers import get_board, get_small_bundle


def test_simulation_generates_labelled_rows():
    board = get_board()
    data = simulate_games(board, n_games=200, seed=1)
    assert data.n_games == 200 and data.n_rows > 200
    assert set(np.unique(data.won)) == {0, 1}
    assert data.cells.min() >= 1 and data.cells.max() <= 100
    X, y = build_feature_dataset(data, FeatureExtractor(board).matrix())
    assert X.shape == (data.n_rows, 5) and y.shape == (data.n_rows,)


def test_simulation_is_reproducible():
    a = simulate_games(get_board(), n_games=100, seed=3)
    b = simulate_games(get_board(), n_games=100, seed=3)
    assert np.array_equal(a.cells, b.cells) and np.array_equal(a.won, b.won)


def test_logistic_regression_trains_and_predicts_probabilities():
    bundle = get_small_bundle()
    m = bundle.model.metrics
    assert m is not None and 0.0 <= m.accuracy <= 1.0
    assert sum(sum(row) for row in m.confusion) == m.n_test
    proba = bundle.model.predict_proba(bundle.features.matrix())
    assert proba.shape == (100,)
    assert ((proba >= 0.0) & (proba <= 1.0)).all()
    # progress should raise the estimated chance of winning
    assert proba[98] > proba[0]


def test_kmeans_creates_three_clusters_with_measured_zones():
    bundle = get_small_bundle()
    clusterer = bundle.clusterer
    assert len(set(clusterer.labels.tolist())) == 3
    assert sorted(p.zone for p in clusterer.profiles) == ["ADVANTAGE", "DANGER", "SAFE"]
    hazards = {p.zone: p.hazard for p in clusterer.profiles}
    assert hazards["DANGER"] > hazards["SAFE"] > hazards["ADVANTAGE"]
    assert sum(p.size for p in clusterer.profiles) == 100


def test_decision_engine_picks_higher_weighted_score():
    engine = DecisionEngine(get_small_bundle())
    result = engine.decide(42, (3, 5), 2)
    a, b = result.candidates
    best = max((a, b), key=lambda c: c.final_score)
    assert result.chosen == best.die_index
    for c in (a, b):
        expected = 0.6 * c.astar_score + 0.4 * c.win_probability
        assert abs(c.final_score - expected) < 1e-9


def test_decision_handles_overshoot_and_winning_moves():
    engine = DecisionEngine(get_small_bundle())
    forced = engine.decide(97, (6, 3), 2)         # 6 overshoots, 3 wins
    assert forced.chosen == 1 and forced.candidates[1].wins_game
    none = engine.decide(99, (5, 6), 2)
    assert none.chosen is None
