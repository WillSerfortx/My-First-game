"""
Tests for Machine Learning models: Logistic Regression and K-Means (K=3).
"""

import pytest
import numpy as np
from ai.features import FeatureExtractor
from ai.data_generator import DatasetSimulator
from ai.logistic_model import LogisticWinModel
from ai.kmeans_model import KMeansRiskModel


def test_simulation_data_generation():
    fe = FeatureExtractor()
    sim = DatasetSimulator(feature_extractor=fe)

    # Fast small simulation for test verification
    X, y = sim.generate_dataset(num_games=100, force_regenerate=True)
    assert X.ndim == 2
    assert X.shape[1] == 5
    assert y.ndim == 1
    assert set(np.unique(y)).issubset({0, 1})


def test_logistic_regression_training_and_inference():
    fe = FeatureExtractor()
    sim = DatasetSimulator(feature_extractor=fe)
    X, y = sim.generate_dataset(num_games=200, force_regenerate=True)

    model = LogisticWinModel(fe)
    metrics = model.train(X, y)

    assert model.is_trained
    assert 0.0 <= model.accuracy <= 1.0
    assert model.confusion_matrix.shape == (2, 2)
    assert len(model.feature_coefficients) == 5

    # Check inference across all cells
    for c in (1, 25, 50, 75, 100):
        prob = model.predict_win_probability(c)
        assert 0.0 <= prob <= 1.0, f"Win prob {prob} for cell {c} out of range"

    # Higher position generally yields higher win probability
    p_early = model.predict_win_probability(10)
    p_late = model.predict_win_probability(90)
    assert p_late >= p_early


def test_kmeans_clustering():
    fe = FeatureExtractor()
    kmeans = KMeansRiskModel(fe)
    kmeans.fit_board()

    assert kmeans.is_trained
    assert len(kmeans.cell_zones) == 100

    # Ensure exactly 3 semantic zones are assigned
    assigned_zones = set(kmeans.cell_zones.values())
    assert assigned_zones == {"Danger", "Safe", "Advantage"}

    # Heatmap structure verification
    heatmap = kmeans.get_heatmap()
    assert len(heatmap) == 100
    for c in range(1, 101):
        assert c in heatmap
        assert "zone" in heatmap[c]
        assert "color" in heatmap[c]
        assert "features" in heatmap[c]
