import random

import pytest

from game.board import Board, SpecialKind
from game.game_engine import GameEngine
from game.player import PlayerId
from game.rules import is_valid_move, plan_move


def engine(seed=0) -> GameEngine:
    return GameEngine(Board(), random.Random(seed))


def force_dice(eng: GameEngine, a: int, b: int) -> None:
    from game.dice import DiceRoll
    eng.dice = DiceRoll((a, b))


def test_normal_movement():
    plan = plan_move(Board(), 10, 0, 3, 2)
    assert plan.landing == 13 and plan.destination == 13 and plan.special is SpecialKind.NONE
    assert plan.walk_path == (11, 12, 13)


def test_snake_movement_and_ladder_movement():
    eng = engine()
    eng.active.position = 13
    force_dice(eng, 3, 1)
    outcome = eng.execute_move(eng.select_die(0), use_shield=False)      # 13 + 3 = 16 (snake)
    assert outcome.final_cell == 6 and eng.players[PlayerId.HUMAN].snakes_hit == 1

    eng2 = engine()
    eng2.active.position = 6
    force_dice(eng2, 3, 6)
    outcome = eng2.execute_move(eng2.select_die(0), use_shield=False)    # 6 + 3 = 9 (ladder -> 31)
    assert outcome.final_cell == 31 and eng2.players[PlayerId.HUMAN].ladders_hit == 1


def test_overshoot_handling():
    assert not is_valid_move(98, 3) and is_valid_move(98, 2)
    assert plan_move(Board(), 98, 0, 3, 2) is None
    eng = engine()
    eng.active.position = 98
    force_dice(eng, 3, 5)
    assert eng.valid_die_indices() == []
    with pytest.raises(ValueError):
        eng.select_die(0)


def test_reaching_100_wins_including_via_ladder():
    eng = engine()
    eng.active.position = 96
    force_dice(eng, 4, 1)
    outcome = eng.execute_move(eng.select_die(0))
    assert outcome.won and eng.winner is PlayerId.HUMAN and eng.game_over

    eng2 = engine()
    eng2.active.position = 77
    force_dice(eng2, 3, 1)                 # 77 + 3 = 80 -> ladder to 100
    outcome = eng2.execute_move(eng2.select_die(0))
    assert outcome.won and outcome.final_cell == 100


def test_players_start_with_two_shields_and_shield_decrements():
    eng = engine()
    assert all(p.shields == 2 for p in eng.players.values())
    eng.active.position = 13
    force_dice(eng, 3, 1)
    plan = eng.select_die(0)
    assert plan.needs_shield_decision
    outcome = eng.execute_move(plan, use_shield=True)
    assert outcome.shield_used and outcome.final_cell == 16       # stays on the snake head
    assert eng.players[PlayerId.HUMAN].shields == 1
    assert eng.players[PlayerId.HUMAN].shields_used == 1


def test_shield_is_not_consumed_without_a_snake():
    eng = engine()
    force_dice(eng, 3, 4)
    outcome = eng.execute_move(eng.select_die(0), use_shield=True)
    assert not outcome.shield_used and eng.active.shields == 2


def test_no_shield_left_means_snake_applies():
    eng = engine()
    eng.active.position = 13
    eng.active.shields = 0
    force_dice(eng, 3, 1)
    plan = eng.select_die(0)
    assert not plan.needs_shield_decision
    assert eng.execute_move(plan, use_shield=True).final_cell == 6


def test_player_turns_alternate_and_rounds_count():
    eng = engine()
    assert eng.current is PlayerId.HUMAN and eng.turn_number == 1
    eng.end_turn()
    assert eng.current is PlayerId.AI and eng.turn_number == 1
    eng.end_turn()
    assert eng.current is PlayerId.HUMAN and eng.turn_number == 2
    assert len(eng.history) == 2


def test_dice_generation_in_range():
    eng = engine(5)
    for _ in range(200):
        roll = eng.roll_dice()
        assert all(1 <= v <= 6 for v in roll.values)


def test_full_random_game_terminates():
    eng = engine(11)
    rng = random.Random(2)
    for _ in range(5000):
        eng.roll_dice()
        valid = eng.valid_die_indices()
        if not valid:
            eng.skip_turn()
        else:
            plan = eng.select_die(rng.choice(valid))
            eng.execute_move(plan, use_shield=plan.needs_shield_decision and rng.random() < 0.5)
        if eng.game_over:
            break
        eng.end_turn()
    assert eng.game_over and eng.winner is not None
    assert eng.players[eng.winner].position == 100
