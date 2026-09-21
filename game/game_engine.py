"""
Game Engine module for AI-Powered Snake & Ladder.
Coordinates turns, players, dice, state transitions, shields, and event history.
"""

from enum import Enum, auto
from typing import List, Dict, Any, Optional
import time

from .board import Board
from .player import Player
from .dice import DualDice
from .rules import GameRules


class TurnPhase(Enum):
    IDLE = auto()
    ROLLING_DICE = auto()
    WAITING_HUMAN_SELECTION = auto()
    AI_THINKING = auto()
    WAITING_HUMAN_SHIELD = auto()
    MOVING_PLAYER = auto()
    ROUND_END = auto()
    GAME_OVER = auto()


class GameEngine:
    """
    State machine and coordinator for the Snake & Ladder game.
    """

    def __init__(self, board: Optional[Board] = None):
        self.board: Board = board if board is not None else Board()

        # Players: Human (Cyan theme), AI (Magenta/Purple theme)
        self.human = Player(
            name="Human Player",
            is_ai=False,
            primary_color=(6, 182, 212),     # Neon Cyan
            secondary_color=(14, 116, 144),  # Darker Cyan
            initial_shields=2,
        )
        self.ai = Player(
            name="AI Agent",
            is_ai=True,
            primary_color=(168, 85, 247),    # Cyber Purple
            secondary_color=(126, 34, 206),  # Darker Purple
            initial_shields=2,
        )
        self.players: List[Player] = [self.human, self.ai]
        self.current_player_idx: int = 0  # 0: Human, 1: AI

        self.dice: DualDice = DualDice(roll_duration=0.25)
        self.phase: TurnPhase = TurnPhase.IDLE

        self.turn_number: int = 1
        self.winner: Optional[Player] = None

        # Pending move resolution data during animation / shield interaction
        self.pending_move: Optional[Dict[str, Any]] = None
        self.pending_roll: Optional[int] = None
        self.ai_decision_data: Optional[Dict[str, Any]] = None

        # Event log
        self.event_log: List[Dict[str, Any]] = []
        self.add_log("System", "Game initialized. Ready for Round 1!", category="system")

    @property
    def current_player(self) -> Player:
        return self.players[self.current_player_idx]

    @property
    def waiting_player(self) -> Player:
        return self.players[1 - self.current_player_idx]

    def add_log(self, source: str, message: str, category: str = "info") -> None:
        """Adds a timestamped event entry to the log."""
        timestamp = time.strftime("%H:%M:%S")
        self.event_log.append({
            "time": timestamp,
            "turn": self.turn_number,
            "source": source,
            "message": message,
            "category": category,
        })
        # Keep log within 150 items
        if len(self.event_log) > 150:
            self.event_log.pop(0)

    def start_new_game(self) -> None:
        """Resets the entire game state."""
        self.human.reset()
        self.ai.reset()
        self.dice.reset()
        self.current_player_idx = 0
        self.turn_number = 1
        self.winner = None
        self.phase = TurnPhase.IDLE
        self.pending_move = None
        self.pending_roll = None
        self.ai_decision_data = None
        self.event_log.clear()
        self.add_log("System", "New game started. Human's turn to roll.", category="system")

    def trigger_roll(self) -> None:
        """Starts the dice roll for the current player."""
        if self.phase != TurnPhase.IDLE:
            return

        values = self.dice.roll()
        self.phase = TurnPhase.ROLLING_DICE
        player_type = "AI" if self.current_player.is_ai else "Human"
        self.add_log(player_type, f"Rolled [{values[0]}] and [{values[1]}].", category="dice")

    def update_dice_roll(self, dt: float) -> bool:
        """Updates the rolling dice physics."""
        finished = self.dice.update(dt)
        if finished and self.phase == TurnPhase.ROLLING_DICE:
            if self.current_player.is_ai:
                self.phase = TurnPhase.AI_THINKING
            else:
                self.phase = TurnPhase.WAITING_HUMAN_SELECTION
            return True
        return False

    def human_select_dice(self, dice_index: int) -> Optional[Dict[str, Any]]:
        """Handles human player clicking dice 0 or 1."""
        if self.phase != TurnPhase.WAITING_HUMAN_SELECTION:
            return None

        chosen_val = self.dice.select(dice_index)
        self.pending_roll = chosen_val
        self.add_log("Human", f"Selected dice [{chosen_val}].", category="choice")

        # Preliminary move calculation to check if landing on snake
        move_info = GameRules.resolve_move(
            self.human.position,
            chosen_val,
            self.board,
            use_shield=False,
        )

        if move_info["hit_snake"] and self.human.has_shields():
            # Prompt human to use shield
            self.pending_move = move_info
            self.phase = TurnPhase.WAITING_HUMAN_SHIELD
            self.add_log("Human", f"Snake threat detected at cell {move_info['landing_cell']}!", category="warning")
            return move_info
        else:
            # Execute move directly
            self._execute_move(move_info)
            return move_info

    def human_resolve_shield(self, use_shield: bool) -> None:
        """Resolves human decision to activate shield or take the snake slide."""
        if self.phase != TurnPhase.WAITING_HUMAN_SHIELD or self.pending_roll is None:
            return

        if use_shield and self.human.use_shield():
            self.add_log(
                "Human",
                f"Activated Shield! Blocked snake at cell {self.pending_move['landing_cell']}.",
                category="shield",
            )
            move_info = GameRules.resolve_move(
                self.human.position,
                self.pending_roll,
                self.board,
                use_shield=True,
            )
        else:
            self.add_log("Human", "Chose not to use shield. Slid down snake.", category="snake")
            move_info = self.pending_move

        self._execute_move(move_info)

    def execute_ai_turn(self, chosen_dice_index: int, use_shield: bool, decision_meta: Dict[str, Any]) -> None:
        """Executes the AI's chosen move after the AI decision engine finishes."""
        if self.phase != TurnPhase.AI_THINKING:
            return

        chosen_val = self.dice.select(chosen_dice_index)
        self.pending_roll = chosen_val
        self.ai_decision_data = decision_meta

        self.add_log("AI", f"Engine chose dice [{chosen_val}].", category="ai")

        if use_shield:
            self.ai.use_shield()
            self.add_log("AI", "Strategically deployed Shield to block snake.", category="shield")

        move_info = GameRules.resolve_move(
            self.ai.position,
            chosen_val,
            self.board,
            use_shield=use_shield,
        )
        self._execute_move(move_info)

    def _execute_move(self, move_info: Dict[str, Any]) -> None:
        """Starts player token movement animation toward destination."""
        player = self.current_player
        player.queue_movement_path(move_info["path"])
        self.pending_move = move_info
        self.phase = TurnPhase.MOVING_PLAYER

    def update_movement(self, dt: float) -> bool:
        """Updates moving player token visual animation."""
        if self.phase != TurnPhase.MOVING_PLAYER:
            return False

        done = self.current_player.update_animation(dt)
        if done:
            self._finalize_turn()
            return True
        return False

    def _finalize_turn(self) -> None:
        """Updates statistics, checks win conditions, and advances turn."""
        player = self.current_player
        move_info = self.pending_move or {}

        hit_snake = move_info.get("hit_snake", False)
        hit_ladder = move_info.get("hit_ladder", False)
        shield_used = move_info.get("shield_used", False)
        landing = move_info.get("landing_cell", player.position)
        final_pos = move_info.get("final_cell", player.position)

        player.record_turn(final_pos, hit_snake and not shield_used, hit_ladder, shield_used)

        p_name = "AI" if player.is_ai else "Human"
        if hit_ladder:
            self.add_log(p_name, f"Climbed ladder from {landing} to {final_pos} (+{move_info.get('ladder_gain', 0)})!", category="ladder")
        elif hit_snake and not shield_used:
            self.add_log(p_name, f"Bitten by snake at {landing}! Slid down to {final_pos} (-{move_info.get('snake_loss', 0)}).", category="snake")
        else:
            self.add_log(p_name, f"Arrived at cell {final_pos}.", category="move")

        # Win condition check
        if GameRules.is_game_over(player.position):
            self.winner = player
            self.phase = TurnPhase.GAME_OVER
            self.add_log("System", f"Game Over! {player.name} reaches cell 100 and WINS!", category="victory")
            return

        # Advance turn
        self.current_player_idx = 1 - self.current_player_idx
        if self.current_player_idx == 0:
            self.turn_number += 1

        self.phase = TurnPhase.IDLE
        self.pending_move = None
        self.pending_roll = None
