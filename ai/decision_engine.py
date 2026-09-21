"""
AI Decision Engine module for AI-Powered Snake & Ladder.
Evaluates both dual-dice candidates using the 4 AI techniques:
- BFS: Shortest path rolls
- A*: Strategic pathfinding score (0.0 - 1.0)
- Logistic Regression: Win probability (0.0 - 1.0)
- K-Means: Visual/analytical risk zone (Danger / Safe / Advantage)

Final decision formula:
final_score = 0.60 * astar_score + 0.40 * logistic_probability

Also executes strategic shield decision when snake threat is detected.
"""

from typing import Dict, Any, Tuple, Optional
from game.board import Board
from game.rules import GameRules
from .bfs import BFSAnalyzer
from .astar import AStarScorer
from .logistic_model import LogisticWinModel
from .kmeans_model import KMeansRiskModel


class AIDecisionEngine:
    """
    Evaluates dual-dice options transparently and selects optimal action.
    """

    def __init__(
        self,
        board: Optional[Board] = None,
        bfs: Optional[BFSAnalyzer] = None,
        astar: Optional[AStarScorer] = None,
        logistic: Optional[LogisticWinModel] = None,
        kmeans: Optional[KMeansRiskModel] = None,
    ):
        self.board: Board = board if board is not None else Board()
        self.bfs: BFSAnalyzer = bfs if bfs is not None else BFSAnalyzer(self.board)
        self.astar: AStarScorer = astar if astar is not None else AStarScorer(self.board, self.bfs)
        self.logistic: LogisticWinModel = logistic if logistic is not None else LogisticWinModel()
        self.kmeans: KMeansRiskModel = kmeans if kmeans is not None else KMeansRiskModel()

    def evaluate_candidates(
        self,
        current_cell: int,
        dice_values: Tuple[int, int],
        ai_shields: int = 2,
    ) -> Dict[str, Any]:
        """
        Evaluates both dice candidates comprehensively and returns the chosen move
        along with full evaluation transparency metrics.
        """
        d1, d2 = dice_values

        cand_a = self._evaluate_single_dice(current_cell, d1, dice_label="Dice 1", ai_shields=ai_shields)
        cand_b = self._evaluate_single_dice(current_cell, d2, dice_label="Dice 2", ai_shields=ai_shields)

        # Compare final scores
        if cand_a["final_score"] >= cand_b["final_score"]:
            chosen_index = 0
            chosen_cand = cand_a
            rejected_cand = cand_b
        else:
            chosen_index = 1
            chosen_cand = cand_b
            rejected_cand = cand_a

        # Strategic shield decision on chosen candidate
        use_shield = False
        shield_explanation = ""

        if chosen_cand["hit_snake"] and ai_shields > 0:
            loss = chosen_cand["snake_loss"]
            # Deploy shield if loss is large (>= 15 cells) or late in game (cell >= 65)
            if loss >= 15 or chosen_cand["landing_cell"] >= 65:
                use_shield = True
                shield_explanation = (
                    f"AI deployed shield: Snake threat at cell {chosen_cand['landing_cell']} "
                    f"(loss of {loss} cells). Position preserved!"
                )
            else:
                shield_explanation = f"AI saved shield: snake loss of {loss} cells deemed acceptable."

        # Rationale summary
        score_diff = abs(cand_a["final_score"] - cand_b["final_score"])
        rationale = (
            f"AI chooses {chosen_cand['label']} ({chosen_cand['roll']}) over {rejected_cand['label']} ({rejected_cand['roll']}) "
            f"by +{score_diff:.3f} weighted score. "
            f"Destination {chosen_cand['final_cell']} offers {chosen_cand['win_probability']*100:.1f}% win prob "
            f"and {chosen_cand['risk_zone']} risk zone."
        )

        return {
            "current_cell": current_cell,
            "dice_values": dice_values,
            "chosen_index": chosen_index,
            "chosen_dice": chosen_cand["roll"],
            "use_shield": use_shield,
            "shield_explanation": shield_explanation,
            "rationale": rationale,
            "candidate_a": cand_a,
            "candidate_b": cand_b,
        }

    def _evaluate_single_dice(
        self,
        current_cell: int,
        roll: int,
        dice_label: str,
        ai_shields: int,
    ) -> Dict[str, Any]:
        """Evaluates one candidate move."""
        # Preliminary resolution without shield
        move_info = GameRules.resolve_move(current_cell, roll, self.board, use_shield=False)
        dest = move_info["final_cell"]
        landing = move_info["landing_cell"]

        # 1. BFS Shortest Path
        bfs_rolls = self.bfs.get_min_rolls(dest)

        # 2. A* Score (0.0 - 1.0)
        astar_info = self.astar.evaluate_candidate(
            current_cell=current_cell,
            roll=roll,
            destination_cell=dest,
            hit_ladder=move_info["hit_ladder"],
            hit_snake=move_info["hit_snake"],
        )
        astar_score = astar_info["astar_score"]

        # 3. Logistic Regression Win Probability (0.0 - 1.0)
        win_prob = self.logistic.predict_win_probability(dest)

        # 4. K-Means Risk Zone (Danger / Safe / Advantage)
        risk_zone = self.kmeans.get_zone_for_cell(dest)

        # Final Weighted Decision Formula: 60% A* + 40% Logistic Regression
        final_score = round(0.60 * astar_score + 0.40 * win_prob, 4)

        return {
            "label": dice_label,
            "roll": roll,
            "landing_cell": landing,
            "final_cell": dest,
            "hit_snake": move_info["hit_snake"],
            "hit_ladder": move_info["hit_ladder"],
            "snake_loss": move_info["snake_loss"],
            "ladder_gain": move_info["ladder_gain"],
            "bfs_rolls": bfs_rolls,
            "astar_score": astar_score,
            "win_probability": win_prob,
            "risk_zone": risk_zone,
            "final_score": final_score,
        }
