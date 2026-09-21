"""
Logistic Regression module for AI-Powered Snake & Ladder.
Trains a real binary classification model on the 5 cell features to predict
win probability (0.0 - 1.0). Provides real calculated metrics: accuracy,
confusion matrix, and feature coefficients.
"""

import os
import pickle
from typing import Dict, Any, Optional, Tuple
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix

from .features import FeatureExtractor


class LogisticWinModel:
    """
    Logistic Regression model predicting win probability from board cell features.
    """

    CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "logistic_cache.pkl")

    def __init__(self, feature_extractor: Optional[FeatureExtractor] = None):
        self.feature_extractor: FeatureExtractor = (
            feature_extractor if feature_extractor is not None else FeatureExtractor()
        )
        self.scaler: StandardScaler = StandardScaler()
        self.model: LogisticRegression = LogisticRegression(
            solver="lbfgs",
            max_iter=1000,
            random_state=42,
        )

        self.is_trained: bool = False
        self.accuracy: float = 0.0
        self.confusion_matrix: np.ndarray = np.zeros((2, 2), dtype=int)
        self.feature_coefficients: Dict[str, float] = {}
        self.intercept: float = 0.0

        # Try loading cached model
        self.load_cache()

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        test_size: float = 0.2,
    ) -> Dict[str, Any]:
        """
        Trains Logistic Regression on (X, y) with train/test split.
        Calculates real accuracy, confusion matrix, and feature importances.
        """
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train model
        self.model.fit(X_train_scaled, y_train)

        # Evaluate performance
        y_pred = self.model.predict(X_test_scaled)
        self.accuracy = float(accuracy_score(y_test, y_pred))
        self.confusion_matrix = confusion_matrix(y_test, y_pred)
        self.intercept = float(self.model.intercept_[0])

        for name, coef in zip(self.feature_extractor.FEATURE_NAMES, self.model.coef_[0]):
            self.feature_coefficients[name] = float(coef)

        self.is_trained = True
        self.save_cache()

        return self.get_metrics()

    def predict_win_probability(self, cell: int) -> float:
        """
        Calculates the estimated win probability [0.0, 1.0] for a player at `cell`.
        Uses real model inference.
        """
        if not self.is_trained:
            # Fallback based on linear progress before training
            return min(1.0, max(0.05, cell / 100.0))

        feat_vector = np.asarray(self.feature_extractor.extract_cell(cell), dtype=np.float64).reshape(1, -1)
        feat_scaled = np.asarray(self.scaler.transform(feat_vector), dtype=np.float64)
        prob = self.model.predict_proba(feat_scaled)[0, 1]
        return round(float(prob), 4)

    def get_metrics(self) -> Dict[str, Any]:
        """Returns calculated validation metrics for display in the AI Lab screen."""
        return {
            "accuracy": self.accuracy,
            "confusion_matrix": self.confusion_matrix.tolist(),
            "coefficients": dict(self.feature_coefficients),
            "intercept": self.intercept,
            "is_trained": self.is_trained,
        }

    def save_cache(self) -> None:
        """Saves trained model, scaler, and metrics to disk."""
        os.makedirs(os.path.dirname(self.CACHE_FILE), exist_ok=True)
        try:
            with open(self.CACHE_FILE, "wb") as f:
                pickle.dump(
                    {
                        "model": self.model,
                        "scaler": self.scaler,
                        "accuracy": self.accuracy,
                        "confusion_matrix": self.confusion_matrix,
                        "coefficients": self.feature_coefficients,
                        "intercept": self.intercept,
                        "is_trained": self.is_trained,
                    },
                    f,
                )
        except Exception as e:
            print(f"Warning: Could not save Logistic Regression cache: {e}")

    def load_cache(self) -> bool:
        """Loads trained model, scaler, and metrics from disk if available."""
        if not os.path.exists(self.CACHE_FILE):
            return False
        try:
            with open(self.CACHE_FILE, "rb") as f:
                data = pickle.load(f)
                self.model = data["model"]
                self.scaler = data["scaler"]
                self.accuracy = data["accuracy"]
                self.confusion_matrix = data["confusion_matrix"]
                self.feature_coefficients = data["coefficients"]
                self.intercept = data["intercept"]
                self.is_trained = data["is_trained"]
                return True
        except Exception:
            return False
