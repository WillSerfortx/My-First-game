"""Logistic Regression: probability that a player standing on a cell wins."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .features import FEATURE_NAMES

EXAMPLE_CELLS = (1, 10, 25, 50, 75, 90, 99)


@dataclass
class ModelMetrics:
    """Everything here is computed on a held-out set of *games*."""
    accuracy: float
    baseline_accuracy: float            # always predicting the majority class
    confusion: list[list[int]]          # [[TN, FP], [FN, TP]]
    precision: float
    recall: float
    f1: float
    roc_auc: float
    n_train: int
    n_test: int
    coefficients: dict[str, float] = field(default_factory=dict)  # on standardised features
    intercept: float = 0.0
    examples: list[tuple[int, float]] = field(default_factory=list)


class WinProbabilityModel:
    """StandardScaler + LogisticRegression pipeline."""

    def __init__(self) -> None:
        self.pipeline = Pipeline([
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(max_iter=300)),
        ])
        self.metrics: ModelMetrics | None = None
        self._fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray, game_ids: np.ndarray,
            test_fraction: float = 0.2) -> ModelMetrics:
        """Train, evaluating on games the model has never seen."""
        cutoff = int(game_ids.max() * (1.0 - test_fraction))
        train_mask = game_ids <= cutoff
        X_tr, y_tr = X[train_mask], y[train_mask]
        X_te, y_te = X[~train_mask], y[~train_mask]
        self.pipeline.fit(X_tr, y_tr)
        self._fitted = True

        proba = self.pipeline.predict_proba(X_te)[:, 1]
        pred = (proba >= 0.5).astype(int)
        cm = confusion_matrix(y_te, pred, labels=[0, 1])
        tn, fp, fn, tp = (int(v) for v in cm.ravel())
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        majority = max(float(y_te.mean()), 1.0 - float(y_te.mean()))
        clf: LogisticRegression = self.pipeline.named_steps["clf"]
        self.metrics = ModelMetrics(
            accuracy=float(accuracy_score(y_te, pred)),
            baseline_accuracy=majority,
            confusion=[[tn, fp], [fn, tp]],
            precision=precision, recall=recall, f1=f1,
            roc_auc=float(roc_auc_score(y_te, proba)),
            n_train=int(X_tr.shape[0]), n_test=int(X_te.shape[0]),
            coefficients={n: float(c) for n, c in zip(FEATURE_NAMES, clf.coef_[0])},
            intercept=float(clf.intercept_[0]),
        )
        return self.metrics

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Win probability (0..1) for each feature row."""
        if not self._fitted:
            raise RuntimeError("Model is not trained")
        return self.pipeline.predict_proba(np.atleast_2d(X))[:, 1]
