"""AI decision engine: chooses one of two dice and decides on shield usage.

final_score = 0.60 * A*_score + 0.40 * LogisticRegression_win_probability

K-Means is *not* part of the score; it supplies the risk-zone information that
is shown next to every candidate.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from game.board import SpecialKind
from game.constants import GOAL_CELL
from game.rules import MovePlan, plan_move

from .pipeline import AIBundle

WEIGHT_ASTAR = 0.60
WEIGHT_LOGISTIC = 0.40

# A shield is only spent when the *benefit* of keeping the snake-head cell
# (same 60/40 blend of A* and win probability) exceeds a reserve threshold.
# Fewer shields left -> each one is more precious -> higher threshold.
SHIELD_THRESHOLD = {2: 0.10, 1: 0.16}
ENDGAME_CELL = 75               # near the goal shields are worth spending
ENDGAME_FACTOR = 0.5


@dataclass(frozen=True)
class CellAnalysis:
    """All analytical values for one cell."""
    cell: int
    astar_score: float
    win_probability: float
    zone: str
    bfs_rolls: int
    astar_rolls: int
    astar_cost: float
    astar_expanded: int
    hazard: float

    @property
    def blended(self) -> float:
        return WEIGHT_ASTAR * self.astar_score + WEIGHT_LOGISTIC * self.win_probability


@dataclass(frozen=True)
class ShieldDecision:
    use: bool
    head: int
    tail: int
    loss_cells: int
    benefit: float
    threshold: float
    lines: tuple[str, ...]


@dataclass(frozen=True)
class CandidateEvaluation:
    label: str                       # "A" or "B"
    die_index: int
    die_value: int
    valid: bool
    landing: int                     # cell reached by walking (0 if invalid)
    result_cell: int                 # final cell after snake/ladder/shield
    special: SpecialKind
    shield_used: bool
    wins_game: bool
    analysis: CellAnalysis | None
    final_score: float
    note: str                        # short human-readable consequence

    @property
    def astar_score(self) -> float:
        return self.analysis.astar_score if self.analysis else 0.0

    @property
    def win_probability(self) -> float:
        return self.analysis.win_probability if self.analysis else 0.0

    @property
    def zone(self) -> str:
        return self.analysis.zone if self.analysis else "-"


@dataclass(frozen=True)
class DecisionResult:
    candidates: tuple[CandidateEvaluation, CandidateEvaluation]
    chosen: int | None               # index 0/1 of the chosen die, None if no legal move
    reason: str
    detail_lines: tuple[str, ...]
    compute_ms: float
    shield_decision: ShieldDecision | None = None

    @property
    def chosen_candidate(self) -> CandidateEvaluation | None:
        return None if self.chosen is None else self.candidates[self.chosen]


class DecisionEngine:
    """Stateless (apart from caches) decision logic on top of an :class:`AIBundle`."""

    def __init__(self, bundle: AIBundle) -> None:
        self.bundle = bundle
        self._analysis: dict[int, CellAnalysis] = {}

    # ------------------------------------------------------------- analysis
    def analyze(self, cell: int) -> CellAnalysis:
        cached = self._analysis.get(cell)
        if cached is None:
            b = self.bundle
            res = b.astar.result(cell)
            cached = CellAnalysis(
                cell=cell,
                astar_score=b.astar.score(cell),
                win_probability=b.win_probability(cell),
                zone=b.clusterer.zone_of(cell),
                bfs_rolls=b.bfs.min_rolls(cell),
                astar_rolls=res.rolls,
                astar_cost=res.cost,
                astar_expanded=res.expanded,
                hazard=b.clusterer.hazard_of(cell),
            )
            self._analysis[cell] = cached
        return cached

    # --------------------------------------------------------------- shields
    def decide_shield(self, head: int, tail: int, shields_left: int) -> ShieldDecision:
        """Should a shield be spent on this snake bite?"""
        keep, drop = self.analyze(head), self.analyze(tail)
        loss = head - tail
        benefit = (WEIGHT_ASTAR * (keep.astar_score - drop.astar_score)
                   + WEIGHT_LOGISTIC * (keep.win_probability - drop.win_probability))
        threshold = SHIELD_THRESHOLD.get(shields_left, SHIELD_THRESHOLD[1])
        if head >= ENDGAME_CELL:
            threshold *= ENDGAME_FACTOR
        use = shields_left > 0 and benefit >= threshold
        lines = [
            "Snake threat detected." if use else "Snake threat evaluated.",
            f"Estimated position loss: {loss} cells.",
            f"Shield benefit {benefit:+.3f} vs reserve threshold {threshold:.3f}.",
            "Shield preserved the current position." if use
            else "Shield kept in reserve for a more dangerous snake.",
        ]
        return ShieldDecision(use, head, tail, loss, benefit, threshold, tuple(lines))

    # ------------------------------------------------------------ candidates
    def evaluate_candidate(self, pos: int, die_index: int, die_value: int,
                           shields: int) -> CandidateEvaluation:
        label = "AB"[die_index]
        plan: MovePlan | None = plan_move(self.bundle.board, pos, die_index, die_value, shields)
        if plan is None:
            return CandidateEvaluation(label, die_index, die_value, False, 0, pos,
                                       SpecialKind.NONE, False, False, None, -1.0,
                                       f"Overshoots cell {GOAL_CELL} - illegal")
        result, special, shield_used = plan.destination, plan.special, False
        note = "Plain move"
        if plan.special is SpecialKind.SNAKE and plan.shield_available:
            sd = self.decide_shield(plan.landing, plan.destination, shields)
            if sd.use:
                result, special, shield_used = plan.landing, SpecialKind.NONE, True
                note = f"Snake at {plan.landing} - shield would block it"
            else:
                note = f"Snake at {plan.landing} -> slides to {plan.destination}"
        elif plan.special is SpecialKind.SNAKE:
            note = f"Snake at {plan.landing} -> slides to {plan.destination}"
        elif plan.special is SpecialKind.LADDER:
            note = f"Ladder at {plan.landing} -> climbs to {plan.destination}"
        analysis = self.analyze(result)
        wins = result == GOAL_CELL
        if wins:
            note = "Reaches cell 100 - winning move"
        final = WEIGHT_ASTAR * analysis.astar_score + WEIGHT_LOGISTIC * analysis.win_probability
        return CandidateEvaluation(label, die_index, die_value, True, plan.landing, result,
                                   special, shield_used, wins, analysis, final, note)

    def decide(self, pos: int, dice: tuple[int, int], shields: int) -> DecisionResult:
        """Pick the die with the higher weighted score."""
        start = time.perf_counter()
        cands = (self.evaluate_candidate(pos, 0, dice[0], shields),
                 self.evaluate_candidate(pos, 1, dice[1], shields))
        valid = [c for c in cands if c.valid]
        lines: list[str] = []
        shield_decision: ShieldDecision | None = None

        if not valid:
            reason = "No legal move: both dice overshoot the goal"
            chosen = None
        elif len(valid) == 1:
            chosen = valid[0].die_index
            other = cands[1 - chosen]
            reason = (f"Dice {valid[0].die_value} is the only legal move "
                      f"(dice {other.die_value} overshoots)")
        else:
            best = max(valid, key=lambda c: (c.wins_game, c.final_score, c.result_cell, c.die_value))
            other = cands[1 - best.die_index]
            chosen = best.die_index
            if best.wins_game:
                reason = f"Dice {best.die_value} reaches cell {GOAL_CELL} - winning move"
            else:
                reason = (f"Dice {best.die_value} scores {best.final_score:.3f} "
                          f"vs {other.final_score:.3f}")
                a_diff = best.astar_score - other.astar_score
                p_diff = best.win_probability - other.win_probability
                lines.append(f"A* difference {a_diff:+.3f} (x{WEIGHT_ASTAR:.2f})")
                lines.append(f"Win-probability difference {p_diff:+.3f} (x{WEIGHT_LOGISTIC:.2f})")

        if chosen is not None:
            c = cands[chosen]
            plan = plan_move(self.bundle.board, pos, chosen, c.die_value, shields)
            if plan is not None and plan.needs_shield_decision:
                shield_decision = self.decide_shield(plan.landing, plan.destination, shields)
        ms = (time.perf_counter() - start) * 1000.0
        return DecisionResult(cands, chosen, reason, tuple(lines), ms, shield_decision)
