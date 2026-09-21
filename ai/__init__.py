"""
AI package for AI-Powered Snake & Ladder.
Integrates four core AI/search/ML techniques:
1. BFS (Shortest Path Analysis)
2. A* (Strategic Candidate Evaluation)
3. Logistic Regression (Win Probability Prediction)
4. K-Means (K=3 Risk Zone Clustering)
"""

from .bfs import BFSAnalyzer
from .astar import AStarScorer
from .features import FeatureExtractor
from .data_generator import DatasetSimulator
from .logistic_model import LogisticWinModel
from .kmeans_model import KMeansRiskModel
from .decision_engine import AIDecisionEngine

__all__ = [
    "BFSAnalyzer",
    "AStarScorer",
    "FeatureExtractor",
    "DatasetSimulator",
    "LogisticWinModel",
    "KMeansRiskModel",
    "AIDecisionEngine",
]
