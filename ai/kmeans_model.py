"""
K-Means Clustering module for AI-Powered Snake & Ladder.
Applies K-Means with K=3 clusters to the 5 cell features.
Categorizes board zones mathematically into:
- DANGER: High immediate snake density and proximity
- SAFE: Low threat, stable transit zone
- ADVANTAGE: High ladder density and advanced board progress
Provides the full 100-cell risk heatmap for analytical visualization.
"""

import os
import pickle
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from .features import FeatureExtractor


class KMeansRiskModel:
    """
    K-Means clustering (K=3) model for strategic risk zone analysis.
    """

    ZONE_DANGER = "Danger"
    ZONE_SAFE = "Safe"
    ZONE_ADVANTAGE = "Advantage"

    # Color codes for visual heatmap rendering
    ZONE_COLORS = {
        ZONE_DANGER: (239, 68, 68),     # Crimson Red
        ZONE_SAFE: (59, 130, 246),      # Slate Blue
        ZONE_ADVANTAGE: (16, 185, 129),  # Emerald Green
    }

    CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "kmeans_cache.pkl")

    def __init__(self, feature_extractor: Optional[FeatureExtractor] = None):
        self.feature_extractor: FeatureExtractor = (
            feature_extractor if feature_extractor is not None else FeatureExtractor()
        )
        self.scaler: StandardScaler = StandardScaler()
        self.model: KMeans = KMeans(n_clusters=3, random_state=42, n_init=10)

        self.is_trained: bool = False
        self.cluster_to_zone: Dict[int, str] = {}
        self.cell_zones: Dict[int, str] = {}
        self.cluster_centroids: np.ndarray = np.zeros((3, 5))
        self.cluster_metrics: Dict[str, Dict[str, float]] = {}

        # Attempt to load cached model
        self.load_cache()

    def fit_board(self, X: Optional[np.ndarray] = None) -> None:
        """
        Fits K-Means (K=3) on the 100 cell features (or dataset X) and assigns
        semantic labels (Danger, Safe, Advantage) based on measurable centroid properties.
        """
        cell_features = np.asarray(self.feature_extractor.extract_all_cells(), dtype=np.float64)
        fit_data = np.asarray(X if X is not None else cell_features, dtype=np.float64)

        scaled_fit = np.asarray(self.scaler.fit_transform(fit_data), dtype=np.float64)
        self.model.fit(scaled_fit)

        # Predict cluster IDs for all 100 cells
        scaled_cells = np.asarray(self.scaler.transform(cell_features), dtype=np.float64)
        cell_cluster_ids = self.model.predict(scaled_cells)

        # Analyze centroids to map raw cluster IDs 0, 1, 2 to Danger, Safe, Advantage
        # Centroids in original feature space
        original_centroids = self.scaler.inverse_transform(self.model.cluster_centers_)
        self.cluster_centroids = original_centroids

        # Feature indices:
        # 0: dist_to_snake, 1: dist_to_ladder, 2: snakes_within_6, 3: ladders_within_6, 4: position_pct
        danger_scores = []
        advantage_scores = []

        for k in range(3):
            c = original_centroids[k]
            # Danger score: higher snakes_within_6 and lower dist_to_snake increases danger
            d_score = float(c[2] * 3.0 - (c[0] / 30.0))
            # Advantage score: higher ladders_within_6 and higher position_pct increases advantage
            a_score = float(c[3] * 3.0 + c[4] * 2.0)

            danger_scores.append((d_score, k))
            advantage_scores.append((a_score, k))

        # Identify Danger cluster (highest danger score)
        danger_cluster = max(danger_scores, key=lambda x: x[0])[1]

        # Identify Advantage cluster from remaining (highest advantage score)
        remaining = [k for k in range(3) if k != danger_cluster]
        advantage_cluster = max(
            [item for item in advantage_scores if item[1] in remaining],
            key=lambda x: x[0],
        )[1]

        # Remaining cluster is Safe
        safe_cluster = [k for k in range(3) if k not in (danger_cluster, advantage_cluster)][0]

        self.cluster_to_zone = {
            danger_cluster: self.ZONE_DANGER,
            safe_cluster: self.ZONE_SAFE,
            advantage_cluster: self.ZONE_ADVANTAGE,
        }

        # Assign each cell (1..100) its semantic zone
        self.cell_zones = {}
        for c in range(1, 101):
            cluster_id = int(cell_cluster_ids[c - 1])
            self.cell_zones[c] = self.cluster_to_zone[cluster_id]

        # Compute summary metrics for each zone
        self._compute_zone_metrics()

        self.is_trained = True
        self.save_cache()

    def _compute_zone_metrics(self) -> None:
        """Computes summary statistics for each semantic zone."""
        for zone in (self.ZONE_DANGER, self.ZONE_SAFE, self.ZONE_ADVANTAGE):
            cells = [c for c, z in self.cell_zones.items() if z == zone]
            if cells:
                feats = np.array([self.feature_extractor.extract_cell(c) for c in cells])
                means = feats.mean(axis=0)
                self.cluster_metrics[zone] = {
                    "count": len(cells),
                    "avg_dist_to_snake": round(float(means[0]), 1),
                    "avg_dist_to_ladder": round(float(means[1]), 1),
                    "avg_snakes_w6": round(float(means[2]), 2),
                    "avg_ladders_w6": round(float(means[3]), 2),
                    "avg_position_pct": round(float(means[4]), 2),
                }

    def get_zone_for_cell(self, cell: int) -> str:
        """Returns the risk zone name ('Danger', 'Safe', 'Advantage') for a cell."""
        if not self.is_trained:
            self.fit_board()
        return self.cell_zones.get(cell, self.ZONE_SAFE)

    def get_zone_color(self, cell: int) -> Tuple[int, int, int]:
        """Returns RGB color for the cell's risk zone."""
        zone = self.get_zone_for_cell(cell)
        return self.ZONE_COLORS.get(zone, (100, 116, 139))

    def get_heatmap(self) -> Dict[int, Dict[str, Any]]:
        """
        Returns full board risk heatmap data for all 100 cells,
        including zone classification and color codes.
        """
        if not self.is_trained:
            self.fit_board()

        heatmap = {}
        for c in range(1, 101):
            zone = self.cell_zones.get(c, self.ZONE_SAFE)
            heatmap[c] = {
                "cell": c,
                "zone": zone,
                "color": self.ZONE_COLORS[zone],
                "features": self.feature_extractor.extract_dict(c),
            }
        return heatmap

    def save_cache(self) -> None:
        """Saves model and clusters to cache."""
        os.makedirs(os.path.dirname(self.CACHE_FILE), exist_ok=True)
        try:
            with open(self.CACHE_FILE, "wb") as f:
                pickle.dump(
                    {
                        "model": self.model,
                        "scaler": self.scaler,
                        "cluster_to_zone": self.cluster_to_zone,
                        "cell_zones": self.cell_zones,
                        "cluster_centroids": self.cluster_centroids,
                        "cluster_metrics": self.cluster_metrics,
                        "is_trained": self.is_trained,
                    },
                    f,
                )
        except Exception as e:
            print(f"Warning: Could not save K-Means cache: {e}")

    def load_cache(self) -> bool:
        """Loads model and clusters from cache."""
        if not os.path.exists(self.CACHE_FILE):
            return False
        try:
            with open(self.CACHE_FILE, "rb") as f:
                data = pickle.load(f)
                self.model = data["model"]
                self.scaler = data["scaler"]
                self.cluster_to_zone = data["cluster_to_zone"]
                self.cell_zones = data["cell_zones"]
                self.cluster_centroids = data["cluster_centroids"]
                self.cluster_metrics = data["cluster_metrics"]
                self.is_trained = data["is_trained"]
                return True
        except Exception:
            return False
