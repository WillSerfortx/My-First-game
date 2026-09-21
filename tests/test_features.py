import numpy as np

from ai.features import FEATURE_NAMES, FeatureExtractor
from game.board import Board


def test_feature_dimensions():
    fx = FeatureExtractor(Board())
    assert FEATURE_NAMES == ("dist_to_snake", "dist_to_ladder", "snakes_within_6",
                             "ladders_within_6", "position_pct")
    assert fx.matrix().shape == (100, 5)
    assert fx.features_for(45).shape == (5,)


def test_feature_ranges_are_valid():
    m = FeatureExtractor(Board()).matrix()
    assert np.isfinite(m).all()
    assert m[:, 0].min() >= 1 and m[:, 0].max() <= 12
    assert m[:, 1].min() >= 1 and m[:, 1].max() <= 12
    assert m[:, 2].min() >= 0 and m[:, 2].max() <= 6
    assert m[:, 3].min() >= 0 and m[:, 3].max() <= 6
    assert m[:, 4].min() > 0 and m[:, 4].max() == 100.0


def test_known_values():
    fx = FeatureExtractor(Board())
    f = fx.features_for(10)      # snake head 16 is 6 ahead, ladder bottom 21 is 11 ahead
    assert f[0] == 6 and f[1] == 11
    assert f[2] == 1 and f[3] == 0
    assert f[4] == 10.0
    assert fx.features_for(100)[4] == 100.0
