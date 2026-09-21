"""
Tests for Game Rules, movement mechanics, overshoot bounce, shields, and win detection.
"""

import pytest
from game.board import Board
from game.rules import GameRules
from game.game_engine import GameEngine, TurnPhase


def test_normal_forward_movement():
    board = Board()
    # From 1 with roll of 2 -> landing 3
    res = GameRules.resolve_move(1, 2, board, use_shield=False)
    assert res["final_cell"] == 3
    assert not res["hit_snake"]
    assert not res["hit_ladder"]
    assert not res["bounced"]


def test_ladder_ascension():
    board = Board()
    # Ladder bottom at 4 -> climbs to 14
    res = GameRules.resolve_move(1, 3, board, use_shield=False)
    assert res["landing_cell"] == 4
    assert res["final_cell"] == 14
    assert res["hit_ladder"]
    assert res["ladder_gain"] == 10


def test_snake_slide_and_shield_protection():
    board = Board()
    # Snake at 17 -> slides to 7
    # Case 1: Without shield
    res_no_shield = GameRules.resolve_move(14, 3, board, use_shield=False)
    assert res_no_shield["landing_cell"] == 17
    assert res_no_shield["final_cell"] == 7
    assert res_no_shield["hit_snake"]
    assert not res_no_shield["shield_used"]

    # Case 2: With shield
    res_shielded = GameRules.resolve_move(14, 3, board, use_shield=True)
    assert res_shielded["landing_cell"] == 17
    assert res_shielded["final_cell"] == 17  # Retained position!
    assert res_shielded["hit_snake"]
    assert res_shielded["shield_used"]


def test_overshoot_bounce_back():
    board = Board()
    # From 97, roll of 5 -> 97 + 5 = 102 -> bounce back 100 - (102 - 100) = 98
    # Snake at 98 slides to 78
    res = GameRules.resolve_move(97, 5, board, use_shield=False)
    assert res["landing_cell"] == 98
    assert res["bounced"]
    assert res["final_cell"] == 78  # Snake at 98 activates!


def test_exact_win_condition():
    board = Board()
    res = GameRules.resolve_move(95, 5, board, use_shield=False)
    assert res["final_cell"] == 100
    assert GameRules.is_game_over(res["final_cell"])


def test_turn_alternation_and_shield_decrement():
    engine = GameEngine()
    assert engine.current_player_idx == 0
    assert engine.human.shields == 2
    assert engine.ai.shields == 2

    # Human uses a shield
    assert engine.human.use_shield()
    assert engine.human.shields == 1
    assert engine.human.shields_used == 1
