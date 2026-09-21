"""Turn-based game engine (pure logic, no rendering).

Typical human/AI turn::

    roll = engine.roll_dice()
    plan = engine.select_die(index)            # logs the selection
    ...                                        # UI walks the token along plan.walk_path
    outcome = engine.execute_move(plan, use_shield)
    if not outcome.won:
        engine.end_turn()
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from enum import Enum

from .board import Board, SpecialKind
from .constants import GOAL_CELL
from .dice import DiceRoll, roll_two_dice
from .player import Player, PlayerId
from .rules import MovePlan, final_cell, plan_move


class EventKind(Enum):
    SYSTEM = "system"
    ROLL = "roll"
    SELECT = "select"
    MOVE = "move"
    LADDER = "ladder"
    SNAKE = "snake"
    SHIELD = "shield"
    AI = "ai"
    WIN = "win"


@dataclass(frozen=True)
class GameEvent:
    timestamp: float
    kind: EventKind
    text: str


@dataclass(frozen=True)
class MoveOutcome:
    """Result of executing a move."""
    player: PlayerId
    plan: MovePlan
    final_cell: int
    special_applied: SpecialKind
    shield_used: bool
    won: bool


@dataclass
class GameEngine:
    board: Board
    rng: random.Random = field(default_factory=random.Random)

    def __post_init__(self) -> None:
        self.reset()

    # ------------------------------------------------------------------ state
    def reset(self) -> None:
        self.players: dict[PlayerId, Player] = {
            PlayerId.HUMAN: Player(PlayerId.HUMAN),
            PlayerId.AI: Player(PlayerId.AI),
        }
        self.current: PlayerId = PlayerId.HUMAN
        self.turn_number: int = 1
        self.dice: DiceRoll | None = None
        self.winner: PlayerId | None = None
        self.events: list[GameEvent] = []
        # (round, human position, ai position) -- used by the progress chart
        self.history: list[tuple[int, int, int]] = [(0, 1, 1)]
        self.log(EventKind.SYSTEM, "Board initialised: 100 cells, 10 snakes, 9 ladders")

    @property
    def active(self) -> Player:
        return self.players[self.current]

    @property
    def opponent(self) -> Player:
        return self.players[self.current.other]

    @property
    def game_over(self) -> bool:
        return self.winner is not None

    def log(self, kind: EventKind, text: str) -> None:
        self.events.append(GameEvent(time.time(), kind, text))

    # ------------------------------------------------------------------ turns
    def roll_dice(self) -> DiceRoll:
        """Roll two dice for the active player."""
        self.dice = roll_two_dice(self.rng)
        a, b = self.dice.values
        self.log(EventKind.ROLL, f"{self.active.name} rolled {a} and {b}")
        return self.dice

    def plan_for(self, die_index: int, player: Player | None = None) -> MovePlan | None:
        """Plan (without side effects) the move for one of the two dice."""
        if self.dice is None:
            raise RuntimeError("Dice have not been rolled")
        player = player or self.active
        return plan_move(self.board, player.position, die_index,
                         self.dice[die_index], player.shields)

    def valid_die_indices(self) -> list[int]:
        return [i for i in (0, 1) if self.plan_for(i) is not None]

    def select_die(self, die_index: int) -> MovePlan:
        """Commit to a die: logs the selection and returns the move plan."""
        plan = self.plan_for(die_index)
        if plan is None:
            raise ValueError("Selected die overshoots the goal")
        self.log(EventKind.SELECT, f"{self.active.name} selected {plan.die_value}")
        return plan

    def skip_turn(self) -> None:
        """Used when neither die is playable (both overshoot cell 100)."""
        self.active.turns += 1
        self.log(EventKind.SYSTEM,
                 f"{self.active.name} cannot move (both dice overshoot cell {GOAL_CELL})")

    def execute_move(self, plan: MovePlan, use_shield: bool = False) -> MoveOutcome:
        """Apply a planned move to the game state."""
        player = self.active
        dest, special = final_cell(plan, use_shield)
        shield_used = plan.special is SpecialKind.SNAKE and dest == plan.landing and use_shield \
            and plan.shield_available
        player.turns += 1
        self.log(EventKind.MOVE, f"{player.name} moved to cell {plan.landing}")

        if shield_used:
            player.shields -= 1
            player.shields_used += 1
            player.snakes_hit += 1     # the snake was encountered, just blocked
            self.log(EventKind.SHIELD,
                     f"{player.name} used a shield - snake blocked at cell {plan.landing} "
                     f"({player.shields} left)")
        elif special is SpecialKind.SNAKE:
            player.snakes_hit += 1
            self.log(EventKind.SNAKE, f"Snake bite! {player.name} slides down to cell {dest}")
        elif special is SpecialKind.LADDER:
            player.ladders_hit += 1
            self.log(EventKind.LADDER, f"Ladder activated -> cell {dest}")

        player.position = dest
        won = dest == GOAL_CELL
        if won:
            self.winner = player.pid
            self.log(EventKind.WIN, f"{player.name} reached cell {GOAL_CELL} and wins!")
        return MoveOutcome(player.pid, plan, dest, special, shield_used, won)

    def end_turn(self) -> None:
        """Hand the turn to the other player (a round ends after the AI moves)."""
        if self.current is PlayerId.AI:
            h, a = self.players[PlayerId.HUMAN].position, self.players[PlayerId.AI].position
            self.history.append((self.turn_number, h, a))
            self.turn_number += 1
        self.current = self.current.other
        self.dice = None
