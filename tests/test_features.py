"""
Tests for Feature Extraction module and the 5 required features.
"""

import pytest
import numpy as np
from game.board import Board
from ai.features import FeatureExtractor


def test_feature_dimensions():
    board = Board()
    fe = FeatureExtractor(board)

    # 5 features
    assert len(fe.FEATURE_NAMES) == 5
    assert fe.FEATURE_NAMES == [
        "dist_to_snake",
        "dist_to_ladder",
        "snakes_within_6",
        "ladders_within_6",
        "position_pct",
    ]

    all_feats = fe.extract_all_cells()
    assert all_feats.shape == (100, 5)


def test_feature_ranges():
    board = Board()
    fe = FeatureExtractor(board)

    for cell in range(1, 101):
        f = fe.extract_dict(cell)

        assert f["dist_to_snake"] >= 0.0
        assert f["dist_to_ladder"] >= 0.0
        assert 0.0 <= f["snakes_within_6"] <= 6.0
        assert 0.0 <= f["ladders_within_6"] <= 6.0
        assert 0.009 <= f["position_pct"] <= 1.001


def test_feature_exact_values():
    board = Board()
    fe = FeatureExtractor(board)

    # Cell 1: ladders at 4 and 9 -> ladders within 6 is 1 (cell 4)
    f1 = fe.extract_dict(1)
    assert f1["position_pct"] == pytest.approx(0.01)
    assert f1["dist_to_ladder"] == 3.0  # 4 - 1 = 3
    assert f1["ladders_within_6"] == 1.0
