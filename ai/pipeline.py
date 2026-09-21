"""Training pipeline: simulate -> features -> Logistic Regression -> K-Means -> cache.

    data generation -> feature extraction -> training dataset
        -> Logistic Regression -> K-Means -> cached results -> game AI

Everything expensive is computed once and cached under ``data/`` so starting the
game again (and every single move) is instant.
"""
from __future__ import annotations

import hashlib
import json
import pickle
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np

from game.board import Board
from game.constants import KMEANS_CLUSTERS, SIMULATED_GAMES, SIMULATION_SEED

from .astar import AStarScorer
from .bfs import BFSAnalyzer
from .data_generator import TrainingData, build_feature_dataset, dataset_sample_csv, simulate_games
from .features import FEATURE_NAMES, FeatureExtractor
from .kmeans_model import CellClusterer
from .logistic_model import EXAMPLE_CELLS, WinProbabilityModel

PIPELINE_VERSION = 3
ProgressFn = Callable[[float, str], None]


@dataclass
class DatasetSummary:
    """Facts about the generated training data (all measured)."""
    n_games: int
    n_rows: int
    won_rows: int
    avg_game_length: float
    sample_rows: list[list[float]] = field(default_factory=list)   # 5 features + won

    @property
    def win_fraction(self) -> float:
        return self.won_rows / max(1, self.n_rows)


@dataclass
class AIBundle:
    """Everything the game AI and the AI Lab screen need."""
    board: Board
    features: FeatureExtractor
    bfs: BFSAnalyzer
    astar: AStarScorer
    model: WinProbabilityModel
    clusterer: CellClusterer
    cell_probability: np.ndarray            # LR win probability of cells 1..100
    summary: DatasetSummary
    source: str                             # "trained" | "cache"
    seconds: dict[str, float] = field(default_factory=dict)

    def win_probability(self, cell: int) -> float:
        return float(self.cell_probability[cell - 1])


def _signature(board: Board, n_games: int, seed: int) -> str:
    payload = json.dumps({"v": PIPELINE_VERSION, "board": board.signature(), "games": n_games,
                          "seed": seed, "features": FEATURE_NAMES, "k": KMEANS_CLUSTERS})
    return hashlib.sha1(payload.encode()).hexdigest()[:16]


def _default_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "data"


def _noop(_f: float, _m: str) -> None:
    return None


def build_ai(board: Board, data_dir: Path | None = None, n_games: int = SIMULATED_GAMES,
             seed: int = SIMULATION_SEED, progress: ProgressFn | None = None,
             force: bool = False) -> AIBundle:
    """Load the cached AI, or run the full training pipeline."""
    progress = progress or _noop
    data_dir = Path(data_dir) if data_dir else _default_data_dir()
    signature = _signature(board, n_games, seed)
    seconds: dict[str, float] = {}

    progress(0.02, "Building board graph, BFS and features")
    t0 = time.perf_counter()
    features = FeatureExtractor(board)
    bfs = BFSAnalyzer(board)
    astar = AStarScorer(board, bfs, features)
    seconds["search"] = time.perf_counter() - t0
    matrix = features.matrix()

    # ---- 1. cached models -------------------------------------------------
    models_path = data_dir / "models.pkl"
    if not force and models_path.exists():
        try:
            with open(models_path, "rb") as fh:
                cached = pickle.load(fh)
            if cached.get("signature") == signature:
                progress(0.95, "Loaded cached models")
                model, clusterer, summary = cached["model"], cached["clusterer"], cached["summary"]
                probs = model.predict_proba(matrix)
                progress(1.0, "AI ready")
                return AIBundle(board, features, bfs, astar, model, clusterer, probs,
                                summary, "cache", cached.get("seconds", {}))
        except Exception:  # corrupt / incompatible cache -> retrain
            pass

    # ---- 2. training data (cached separately) ------------------------------
    data_path = data_dir / "training_data.npz"
    data: TrainingData | None = None
    if not force and data_path.exists():
        try:
            with np.load(data_path) as z:
                if str(z["signature"]) == signature:
                    data = TrainingData(z["cells"], z["won"], z["game_id"], z["player"],
                                        int(z["n_games"]), float(z["avg_len"]))
                    progress(0.5, "Loaded cached simulation data")
        except Exception:
            data = None
    if data is None:
        t0 = time.perf_counter()
        data = simulate_games(board, n_games, seed,
                              progress=lambda f: progress(0.05 + 0.45 * f,
                                                          f"Simulating {n_games:,} random games"))
        seconds["simulation"] = time.perf_counter() - t0
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(data_path, cells=data.cells, won=data.won, game_id=data.game_id,
                                player=data.player, n_games=data.n_games,
                                avg_len=data.avg_game_length, signature=signature)
        except OSError:
            pass

    # ---- 3. features -> dataset ---------------------------------------------
    progress(0.55, "Extracting the five cell features")
    X, y = build_feature_dataset(data, matrix)
    try:
        dataset_sample_csv(str(data_dir / "training_sample.csv"), X, y)
    except OSError:
        pass

    # ---- 4. logistic regression -----------------------------------------------
    progress(0.65, "Training Logistic Regression")
    t0 = time.perf_counter()
    model = WinProbabilityModel()
    metrics = model.fit(X, y, data.game_id)
    probs = model.predict_proba(matrix)
    metrics.examples = [(c, float(probs[c - 1])) for c in EXAMPLE_CELLS]
    seconds["logistic_regression"] = time.perf_counter() - t0

    # ---- 5. k-means ---------------------------------------------------------------
    progress(0.85, "Clustering cells with K-Means (K=3)")
    t0 = time.perf_counter()
    clusterer = CellClusterer(KMEANS_CLUSTERS).fit(matrix)
    seconds["kmeans"] = time.perf_counter() - t0

    summary = DatasetSummary(
        n_games=data.n_games, n_rows=data.n_rows, won_rows=int(data.won.sum()),
        avg_game_length=data.avg_game_length,
        sample_rows=[[float(v) for v in X[i]] + [float(y[i])] for i in range(12)],
    )
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        with open(models_path, "wb") as fh:
            pickle.dump({"signature": signature, "model": model, "clusterer": clusterer,
                         "summary": summary, "seconds": seconds}, fh)
    except OSError:
        pass
    progress(1.0, "AI ready")
    return AIBundle(board, features, bfs, astar, model, clusterer, probs, summary,
                    "trained", seconds)
