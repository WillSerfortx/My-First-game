"""
Data Generator module for AI-Powered Snake & Ladder.
Simulates 10,000 dual-dice games to create a high-quality machine learning training dataset.
Extracts the 5 required features for every visited position with binary outcome target (won=1, lost=0).
"""

import os
import random
from typing import Tuple, Optional, Callable
import numpy as np
from game.board import Board
from game.rules import GameRules
from .features import FeatureExtractor


class DatasetSimulator:
    """
    Simulates thousands of games and produces a structured (X, y) dataset
    for Logistic Regression training and K-Means analysis.
    """

    CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "training_data.npz")

    def __init__(self, board: Optional[Board] = None, feature_extractor: Optional[FeatureExtractor] = None):
        self.board: Board = board if board is not None else Board()
        self.feature_extractor: FeatureExtractor = (
            feature_extractor if feature_extractor is not None else FeatureExtractor(self.board)
        )

    def simulate_game(self) -> Tuple[list[int], list[int], int]:
        """
        Simulates a single dual-dice Snake & Ladder game between two players.
        Returns:
            p1_history: Cells visited by Player 1
            p2_history: Cells visited by Player 2
            winner: 1 if Player 1 won, 2 if Player 2 won
        """
        p1_pos = 1
        p2_pos = 1
        p1_shields = 2
        p2_shields = 2

        p1_history: list[int] = [1]
        p2_history: list[int] = [1]

        for _ in range(300):  # Safety limit against endless games
            # --- Player 1 turn ---
            d1, d2 = random.randint(1, 6), random.randint(1, 6)
            # Pick strategically or randomly
            chosen_d = max(d1, d2) if random.random() < 0.6 else random.choice((d1, d2))

            # Move calculation
            landing = p1_pos + chosen_d
            if landing > 100:
                landing = 100 - (landing - 100)

            hit_snake = landing in self.board.snakes
            shield_used = False
            if hit_snake and p1_shields > 0:
                # Strategic shield: use if losing >= 15 cells or close to 100
                if (landing - self.board.snakes[landing]) >= 15 or landing >= 70:
                    p1_shields -= 1
                    shield_used = True

            res = GameRules.resolve_move(p1_pos, chosen_d, self.board, use_shield=shield_used)
            p1_pos = res["final_cell"]
            p1_history.append(p1_pos)

            if p1_pos >= 100:
                return p1_history, p2_history, 1

            # --- Player 2 turn ---
            d1, d2 = random.randint(1, 6), random.randint(1, 6)
            chosen_d = max(d1, d2) if random.random() < 0.6 else random.choice((d1, d2))

            landing = p2_pos + chosen_d
            if landing > 100:
                landing = 100 - (landing - 100)

            hit_snake = landing in self.board.snakes
            shield_used = False
            if hit_snake and p2_shields > 0:
                if (landing - self.board.snakes[landing]) >= 15 or landing >= 70:
                    p2_shields -= 1
                    shield_used = True

            res = GameRules.resolve_move(p2_pos, chosen_d, self.board, use_shield=shield_used)
            p2_pos = res["final_cell"]
            p2_history.append(p2_pos)

            if p2_pos >= 100:
                return p1_history, p2_history, 2

        # In rare draw, whichever is ahead wins
        winner = 1 if p1_pos >= p2_pos else 2
        return p1_history, p2_history, winner

    def generate_dataset(
        self,
        num_games: int = 10000,
        progress_callback: Optional[Callable[[float], None]] = None,
        force_regenerate: bool = False,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generates or loads the cached dataset from simulating num_games.
        Returns:
            X: Matrix of shape (N, 5) with the 5 features
            y: Vector of shape (N,) with binary win outcomes (1=won, 0=lost)
        """
        # Ensure output cache directory exists
        os.makedirs(os.path.dirname(self.CACHE_FILE), exist_ok=True)

        if not force_regenerate and os.path.exists(self.CACHE_FILE):
            try:
                data = np.load(self.CACHE_FILE)
                return data["X"], data["y"]
            except Exception:
                pass  # Regenerate if corrupted

        all_features: list[np.ndarray] = []
        all_labels: list[int] = []

        # Vectorized cell feature table lookup
        cell_features_lookup = self.feature_extractor.extract_all_cells()

        for g in range(num_games):
            p1_hist, p2_hist, winner = self.simulate_game()

            # Record Player 1 visited cells
            p1_won = 1 if winner == 1 else 0
            for cell in p1_hist:
                idx = max(0, min(99, cell - 1))
                all_features.append(cell_features_lookup[idx])
                all_labels.append(p1_won)

            # Record Player 2 visited cells
            p2_won = 1 if winner == 2 else 0
            for cell in p2_hist:
                idx = max(0, min(99, cell - 1))
                all_features.append(cell_features_lookup[idx])
                all_labels.append(p2_won)

            if progress_callback and g % 1000 == 0:
                progress_callback(g / float(num_games))

        X = np.array(all_features, dtype=np.float64)
        y = np.array(all_labels, dtype=np.int32)

        # Cache dataset to disk
        try:
            np.savez_compressed(self.CACHE_FILE, X=X, y=y)
        except Exception as e:
            print(f"Warning: Could not save training data cache: {e}")

        if progress_callback:
            progress_callback(1.0)

        return X, y
