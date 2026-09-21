"""K-Means (K=3) clustering of the 100 cells into strategic risk zones.

Cluster names are *derived*, not assigned: every cell gets a measurable
``hazard`` value from its own features, clusters are ranked by their mean
hazard and named DANGER (highest), SAFE (middle) and ADVANTAGE (lowest).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from game.constants import KMEANS_CLUSTERS, NUM_CELLS

from .features import FEATURE_NAMES

ZONE_DANGER = "DANGER"
ZONE_SAFE = "SAFE"
ZONE_ADVANTAGE = "ADVANTAGE"
ZONE_ORDER = (ZONE_DANGER, ZONE_SAFE, ZONE_ADVANTAGE)


def cell_hazard(features: np.ndarray) -> np.ndarray:
    """Net threat of each cell (rows of the 5-feature matrix).

    hazard = (snakes_within_6 - ladders_within_6)
           + (1 / dist_to_snake - 1 / dist_to_ladder)
    Positive = snake-dominated surroundings, negative = ladder-dominated.
    """
    d_snake, d_ladder = features[:, 0], features[:, 1]
    snakes6, ladders6 = features[:, 2], features[:, 3]
    return (snakes6 - ladders6) + (1.0 / d_snake - 1.0 / d_ladder)


@dataclass
class ClusterProfile:
    cluster_id: int
    zone: str
    size: int
    hazard: float
    means: dict[str, float]
    cells: list[int]


class CellClusterer:
    """Fits K-Means on standardised cell features and interprets the clusters."""

    def __init__(self, k: int = KMEANS_CLUSTERS, seed: int = 42) -> None:
        self.k = k
        self.seed = seed
        self.scaler = StandardScaler()
        self.model = KMeans(n_clusters=k, n_init=10, random_state=seed)
        self.labels: np.ndarray = np.zeros(NUM_CELLS, dtype=int)
        self.hazards: np.ndarray = np.zeros(NUM_CELLS)
        self.zone_by_cluster: dict[int, str] = {}
        self.profiles: list[ClusterProfile] = []
        self.silhouette: float = 0.0
        self.inertia: float = 0.0

    def fit(self, feature_matrix: np.ndarray) -> "CellClusterer":
        scaled = self.scaler.fit_transform(feature_matrix)
        self.labels = self.model.fit_predict(scaled)
        self.inertia = float(self.model.inertia_)
        self.silhouette = float(silhouette_score(scaled, self.labels)) \
            if len(set(self.labels)) > 1 else 0.0
        self.hazards = cell_hazard(feature_matrix)

        mean_hazard = {c: float(self.hazards[self.labels == c].mean()) for c in range(self.k)}
        ranked = sorted(mean_hazard, key=mean_hazard.get, reverse=True)  # highest hazard first
        names = ZONE_ORDER if self.k == 3 else tuple(f"ZONE {i + 1}" for i in range(self.k))
        self.zone_by_cluster = {cluster: names[i] for i, cluster in enumerate(ranked)}

        self.profiles = []
        for cluster in ranked:
            mask = self.labels == cluster
            self.profiles.append(ClusterProfile(
                cluster_id=cluster,
                zone=self.zone_by_cluster[cluster],
                size=int(mask.sum()),
                hazard=mean_hazard[cluster],
                means={n: float(feature_matrix[mask, i].mean()) for i, n in enumerate(FEATURE_NAMES)},
                cells=[int(i) + 1 for i in np.flatnonzero(mask)],
            ))
        return self

    def cluster_of(self, cell: int) -> int:
        return int(self.labels[cell - 1])

    def zone_of(self, cell: int) -> str:
        return self.zone_by_cluster[self.cluster_of(cell)]

    def hazard_of(self, cell: int) -> float:
        return float(self.hazards[cell - 1])
