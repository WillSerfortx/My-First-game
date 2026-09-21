"""The in-game screen: board, dice, AI decision panel, statistics and event log."""
from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

import pygame

from ai.decision_engine import DecisionResult, ShieldDecision
from game.board import SpecialKind
from game.constants import GOAL_CELL, SHIELDS_PER_PLAYER
from game.game_engine import EventKind, GameEngine, MoveOutcome
from game.player import PlayerId
from game.rules import MovePlan

from . import draw, theme
from .animations import (Tween, clamp01, ease_in_out_cubic, ease_out_back, ease_out_cubic,
                         polyline_point, pulse)
from .board_renderer import BoardRenderer
from .particles import ParticleSystem
from .theme import S, fonts
from .widgets import (Button, Card, DecisionScoreBar, DiceWidget, EventLog, MiniChart, Modal, Panel,
                      ProgressBar, StatCard, StatusBadge, Tooltip, mouse_pos)

if TYPE_CHECKING:  # pragma: no cover
    from .app import App

# --- timing (seconds) ---------------------------------------------------------
STEP_TIME = 0.21
ROLL_TIME = 0.95
AI_ROLL_DELAY = 0.9
THINK_TIME = 2.6
VERDICT_AT = 2.0
TURN_END_DELAY = 0.55
SHIELD_FX_TIME = 1.15
VICTORY_DELAY = 0.9

PLAYER_COLOR = {PlayerId.HUMAN: theme.HUMAN_COLOR, PlayerId.AI: theme.AI_COLOR}


class Phase(Enum):
    WAIT_ROLL = "wait_roll"
    ROLLING = "rolling"
    CHOOSE = "choose"
    AI_THINK = "ai_think"
    MOVING = "moving"
    SHIELD_PROMPT = "shield_prompt"
    SHIELD_FX = "shield_fx"
    SPECIAL = "special"
    TURN_END = "turn_end"
    VICTORY = "victory"


@dataclass
class TokenState:
    cell: int
    frac: tuple[float, float]
    lift: float = 0.0          # in cell heights
    scale: float = 1.0


@dataclass
class WalkAnim:
    pid: PlayerId
    cells: list[int]
    start: int
    idx: int = 0
    prog: float = 0.0


@dataclass
class SpecialAnim:
    pid: PlayerId
    path: list[tuple[float, float]]
    kind: SpecialKind
    duration: float
    elapsed: float = 0.0
    spark_timer: float = 0.0


@dataclass
class ShieldFx:
    pid: PlayerId
    elapsed: float = 0.0


@dataclass
class Layout:
    header: pygame.Rect
    board: pygame.Rect
    status: pygame.Rect
    dice: pygame.Rect
    stats: pygame.Rect
    ai: pygame.Rect
    log: pygame.Rect
    bar: pygame.Rect


def compute_layout(vp: pygame.Rect) -> Layout:
    m = S(18)
    header_h, bar_h = S(64), S(34)
    content = pygame.Rect(vp.x + m, vp.y + header_h, vp.w - 2 * m, vp.h - header_h - bar_h - m // 2)
    side_len = min(content.h, int(content.w * 0.53))
    board = pygame.Rect(content.x, content.y + (content.h - side_len) // 2, side_len, side_len)
    side = pygame.Rect(board.right + S(16), content.y, content.right - board.right - S(16), content.h)
    gap = S(12)
    col_w = (side.w - gap) // 2
    col1 = pygame.Rect(side.x, side.y, col_w, side.h)
    col2 = pygame.Rect(side.x + col_w + gap, side.y, side.w - col_w - gap, side.h)
    status_h, dice_h = int(col1.h * 0.245), int(col1.h * 0.27)
    ai_h = int(col2.h * 0.57)
    return Layout(
        header=pygame.Rect(vp.x + m, vp.y + S(6), vp.w - 2 * m, header_h - S(10)),
        board=board,
        status=pygame.Rect(col1.x, col1.y, col1.w, status_h),
        dice=pygame.Rect(col1.x, col1.y + status_h + gap, col1.w, dice_h),
        stats=pygame.Rect(col1.x, col1.y + status_h + dice_h + 2 * gap, col1.w,
                          col1.h - status_h - dice_h - 2 * gap),
        ai=pygame.Rect(col2.x, col2.y, col2.w, ai_h),
        log=pygame.Rect(col2.x, col2.y + ai_h + gap, col2.w, col2.h - ai_h - gap),
        bar=pygame.Rect(vp.x + m, vp.bottom - bar_h, vp.w - 2 * m, bar_h - S(8)),
    )


class GameScreen:
    """Owns a GameEngine and drives the turn flow with animations."""

    def __init__(self, app: "App") -> None:
        self.app = app
        self.engine = GameEngine(app.board, random.Random())
        self.de = app.decision_engine
        self.renderer = BoardRenderer(app.board, app.bundle.clusterer)
        self.particles = ParticleSystem()
        self.time = 0.0

        self.panels = {
            "status": Panel("GAME STATUS", theme.CYAN, 0.0),
            "dice": Panel("DICE OPTIONS", theme.BLUE, 0.08),
            "stats": Panel("STATISTICS", theme.GREEN, 0.16),
            "ai": Panel("AI ANALYSIS", theme.MAGENTA, 0.10),
            "log": Panel("GAME LOG", theme.GOLD, 0.20),
        }
        self.dice = [DiceWidget(0, theme.CYAN), DiceWidget(1, theme.CYAN)]
        self.roll_button = Button("ROLL DICE", self._on_roll_clicked, "primary", 16)
        self.btn_heat = Button("RISK MAP", None, "secondary", 12, toggle=True)
        self.btn_route = Button("BFS PATH", None, "secondary", 12, toggle=True)
        self.btn_sound = Button("SOUND ON", self._toggle_sound, "secondary", 12)
        self.btn_menu = Button("MENU", self._open_pause, "secondary", 12)
        self.header_buttons = [self.btn_heat, self.btn_route, self.btn_sound, self.btn_menu]

        self.win_bars = {pid: ProgressBar(PLAYER_COLOR[pid], 4.0) for pid in PlayerId}
        self.chart = MiniChart()
        self.log_widget = EventLog()
        self.cand_bars = [[DecisionScoreBar("A* Score", theme.CYAN),
                           DecisionScoreBar("Win Probability", theme.GREEN),
                           DecisionScoreBar("Weighted Score", theme.GOLD, 3, strong=True)]
                          for _ in range(2)]

        self.shield_modal = Modal("SNAKE AHEAD", [], [
            Button("USE SHIELD  (Y)", lambda: self._resolve_shield(True), "gold", 15),
            Button("TAKE THE SLIDE  (N)", lambda: self._resolve_shield(False), "secondary", 14),
        ], theme.GOLD)
        self.pause_modal = Modal("PAUSED", ["Return to the main menu? The current game will be lost."], [
            Button("RESUME", self._close_pause, "primary", 15),
            Button("MAIN MENU", self._to_menu, "danger", 15),
        ], theme.CYAN)
        self.victory_buttons = [Button("PLAY AGAIN", self.new_game, "primary", 17),
                                Button("MAIN MENU", self._to_menu, "secondary", 17)]
        self.victory_anim = Tween(0.0, 1.0, 0.9, ease_out_back)

        self.new_game()

    # ================================================================ lifecycle
    def new_game(self) -> None:
        self.engine.reset()
        self.engine.log(EventKind.SYSTEM, "AI engine online: BFS, A*, Logistic Regression, K-Means")
        self.engine.log(EventKind.SYSTEM, "Each turn: roll two dice, pick one. 2 shields each.")
        self.phase = Phase.WAIT_ROLL
        self.phase_time = 0.0
        self.auto_timer = 0.0
        self.decision: DecisionResult | None = None
        self.shield_note: ShieldDecision | None = None
        self.think_t = 0.0
        self.verdict_shown = False
        self.plan: MovePlan | None = None
        self.outcome: MoveOutcome | None = None
        self.walk: WalkAnim | None = None
        self.special: SpecialAnim | None = None
        self.shield_fx: ShieldFx | None = None
        self.hover_die: int | None = None
        self.tokens = {pid: TokenState(1, BoardRenderer.cell_center_frac(1)) for pid in PlayerId}
        self.particles.clear()
        for d in self.dice:
            d.show(1)
            d.chosen = False
            d.valid = True
            d.selectable = False
        for row in self.cand_bars:
            for bar in row:
                bar.set_now(0.0)
        self.log_widget.follow = True
        self.log_widget._key = None
        self.chart.reveal.set(0.0, snap=True)
        self.shield_modal.close()
        self.pause_modal.close()
        for p in self.panels.values():
            p.replay(p.appear.delay)
        for pid in PlayerId:
            self.win_bars[pid].set(self.de.analyze(1).win_probability, snap=True)
        self._begin_turn()

    def _begin_turn(self) -> None:
        self.phase = Phase.WAIT_ROLL
        self.phase_time = 0.0
        cur = self.engine.current
        for d in self.dice:
            d.set_accent(PLAYER_COLOR[cur])
            d.selectable = False
            d.chosen = False
            d.valid = True
        self.auto_timer = AI_ROLL_DELAY if cur is PlayerId.AI else 0.0

    # ================================================================== input
    def _on_roll_clicked(self) -> None:
        if self.phase is Phase.WAIT_ROLL and self.engine.current is PlayerId.HUMAN:
            self._start_roll()

    def _toggle_sound(self) -> None:
        on = self.app.audio.toggle()
        self.btn_sound.label = "SOUND ON" if on else "SOUND OFF"
        self.app.audio.play("click")

    def _open_pause(self) -> None:
        self.app.audio.play("click")
        self.pause_modal.open()

    def _close_pause(self) -> None:
        self.pause_modal.close()

    def _to_menu(self) -> None:
        self.app.audio.play("click")
        self.pause_modal.close()
        self.app.goto("home")

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.phase is Phase.VICTORY and self.victory_anim.progress > 0.5:
            for b in self.victory_buttons:
                b.handle_event(event)
            return
        if self.pause_modal.visible:
            self.pause_modal.handle_event(event)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._close_pause()
            return
        if self.shield_modal.visible:
            self.shield_modal.handle_event(event)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_y:
                    self._resolve_shield(True)
                elif event.key == pygame.K_n:
                    self._resolve_shield(False)
            return

        for b in self.header_buttons + [self.roll_button]:
            b.handle_event(event)
        self.log_widget.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.phase is Phase.CHOOSE:
            for i, d in enumerate(self.dice):
                if d.contains(event.pos) and d.valid:
                    self._human_choose(i)
                    break
        if event.type == pygame.KEYDOWN:
            key = event.key
            if key == pygame.K_ESCAPE:
                self._open_pause()
            elif key in (pygame.K_SPACE, pygame.K_RETURN):
                self._on_roll_clicked()
            elif key in (pygame.K_1, pygame.K_KP1) and self.phase is Phase.CHOOSE and self.dice[0].valid:
                self._human_choose(0)
            elif key in (pygame.K_2, pygame.K_KP2) and self.phase is Phase.CHOOSE and self.dice[1].valid:
                self._human_choose(1)
            elif key == pygame.K_h:
                self.btn_heat.active = not self.btn_heat.active
            elif key == pygame.K_p:
                self.btn_route.active = not self.btn_route.active
            elif key == pygame.K_m:
                self._toggle_sound()

    # ============================================================== turn flow
    def _start_roll(self) -> None:
        roll = self.engine.roll_dice()
        for i, d in enumerate(self.dice):
            d.roll(roll[i], ROLL_TIME, delay=i * 0.12)
        self.app.audio.play("dice")
        self.phase = Phase.ROLLING
        self.phase_time = 0.0
        if self.engine.current is PlayerId.AI:
            self.decision = None
            self.shield_note = None
            self.verdict_shown = False

    def _after_roll(self) -> None:
        valid = self.engine.valid_die_indices()
        for i, d in enumerate(self.dice):
            d.valid = i in valid
        cur = self.engine.current
        if not valid:
            self.engine.skip_turn()
            self.app.toasts.push(f"{self.engine.active.name}: no legal move this turn", theme.ORANGE)
            self.phase, self.phase_time = Phase.TURN_END, 0.0
            return
        if cur is PlayerId.HUMAN:
            for d in self.dice:
                d.selectable = True
            self.phase = Phase.CHOOSE
            if len(valid) == 1:
                self.app.toasts.push("Only one die is playable (the other overshoots cell 100)", theme.GOLD)
        else:
            self._ai_decide()

    def _ai_decide(self) -> None:
        p = self.engine.active
        assert self.engine.dice is not None
        result = self.de.decide(p.position, self.engine.dice.values, p.shields)
        self.decision = result
        self.think_t = 0.0
        self.verdict_shown = False
        eng = self.engine
        eng.log(EventKind.AI, "AI evaluated both candidates")
        valid = [c for c in result.candidates if c.valid]
        if len(valid) == 2:
            best_a = max(valid, key=lambda c: c.astar_score)
            eng.log(EventKind.AI, f"A* preferred cell {best_a.result_cell}")
        if result.chosen_candidate is not None:
            c = result.chosen_candidate
            eng.log(EventKind.AI, f"Logistic Regression: {c.win_probability:.0%} win probability")
            eng.log(EventKind.AI, f"Weighted scores A {result.candidates[0].final_score:.3f} "
                                  f"/ B {result.candidates[1].final_score:.3f}")
        else:
            eng.log(EventKind.AI, result.reason)
        for i, cand in enumerate(result.candidates):
            bars = self.cand_bars[i]
            if cand.valid:
                base = 0.35 + i * 0.45
                bars[0].reveal(cand.astar_score, base)
                bars[1].reveal(cand.win_probability, base + 0.18)
                bars[2].reveal(cand.final_score, base + 0.36)
            else:
                for b in bars:
                    b.set_now(0.0)
        self.phase = Phase.AI_THINK
        self.phase_time = 0.0

    def _human_choose(self, idx: int) -> None:
        if self.phase is not Phase.CHOOSE:
            return
        self.app.audio.play("click")
        for d in self.dice:
            d.selectable = False
        self.dice[idx].chosen = True
        self.hover_die = None
        self._begin_move(self.engine.select_die(idx))

    def _begin_move(self, plan: MovePlan) -> None:
        self.plan = plan
        self.walk = WalkAnim(self.engine.current, list(plan.walk_path), plan.start)
        self.phase, self.phase_time = Phase.MOVING, 0.0

    def _on_landed(self) -> None:
        plan = self.plan
        assert plan is not None
        if plan.needs_shield_decision:
            player = self.engine.active
            if self.engine.current is PlayerId.HUMAN:
                advisor = self.de.decide_shield(plan.landing, plan.destination, player.shields)
                self.shield_modal.set_content("SNAKE AHEAD!", [
                    f"Cell {plan.landing} is a snake head. Without a shield you slide down to cell "
                    f"{plan.destination} (-{plan.landing - plan.destination} cells).",
                    f"Shields left: {player.shields}.",
                    f"AI advisor: benefit {advisor.benefit:+.3f} vs reserve {advisor.threshold:.3f} - "
                    f"{'use the shield' if advisor.use else 'keep the shield'}.",
                ])
                self.shield_modal.open()
                self.phase, self.phase_time = Phase.SHIELD_PROMPT, 0.0
                return
            decision = self.de.decide_shield(plan.landing, plan.destination, player.shields)
            self.shield_note = decision
            prefix = "AI used a shield:" if decision.use else "AI kept its shield:"
            self.engine.log(EventKind.AI, prefix)
            for line in decision.lines:
                self.engine.log(EventKind.AI, "  " + line)
            self._finish_move(decision.use)
        else:
            self._finish_move(False)

    def _resolve_shield(self, use: bool) -> None:
        if self.phase is not Phase.SHIELD_PROMPT:
            return
        self.app.audio.play("click")
        self.shield_modal.close()
        self._finish_move(use)

    def _finish_move(self, use_shield: bool) -> None:
        plan = self.plan
        assert plan is not None
        outcome = self.engine.execute_move(plan, use_shield)
        self.outcome = outcome
        pid = outcome.player
        if outcome.shield_used:
            self.shield_fx = ShieldFx(pid)
            self.app.audio.play("shield")
            x, y = self.renderer.cell_center(plan.landing)
            self.particles.burst(x, y, theme.GOLD, 26)
            self.phase, self.phase_time = Phase.SHIELD_FX, 0.0
        elif outcome.special_applied is not SpecialKind.NONE:
            if outcome.special_applied is SpecialKind.LADDER:
                path = self.renderer.ladder_paths[plan.landing]
                self.special = SpecialAnim(pid, path, SpecialKind.LADDER, 1.15)
                self.app.audio.play("ladder")
            else:
                path = self.renderer.snake_paths[plan.landing]
                self.special = SpecialAnim(pid, path, SpecialKind.SNAKE, 1.55)
                self.app.audio.play("snake")
            self.phase, self.phase_time = Phase.SPECIAL, 0.0
        else:
            self._after_special()

    def _after_special(self) -> None:
        pid = self.engine.current
        pos = self.engine.players[pid].position
        tok = self.tokens[pid]
        tok.cell, tok.frac, tok.lift, tok.scale = pos, BoardRenderer.cell_center_frac(pos), 0.0, 1.0
        self.phase, self.phase_time = Phase.TURN_END, 0.0

    def _finish_turn(self) -> None:
        self.engine.end_turn()
        self._begin_turn()

    def _show_victory(self) -> None:
        self.phase, self.phase_time = Phase.VICTORY, 0.0
        self.victory_anim.restart()
        self.app.audio.play("victory")
        w = self.engine.winner
        color = PLAYER_COLOR[w] if w else theme.GOLD
        x, y = self.renderer.cell_center(GOAL_CELL)
        for _ in range(3):
            self.particles.burst(x, y, color, 40)
        self._confetti_t = 0.0

    # ================================================================== update
    def update(self, dt: float) -> None:
        self.time += dt
        self.phase_time += dt
        for p in self.panels.values():
            p.update(dt)
        for d in self.dice:
            d.update(dt)
        for b in self.header_buttons + [self.roll_button] + self.victory_buttons:
            b.update(dt)
        self.shield_modal.update(dt)
        self.pause_modal.update(dt)
        for row in self.cand_bars:
            for bar in row:
                bar.update(dt)
        for bar in self.win_bars.values():
            bar.update(dt)
        self.chart.update(dt)
        self.particles.update(dt)
        self.victory_anim.update(dt)
        self.btn_heat.label = "RISK MAP"
        self.roll_button.visible = self.phase is Phase.WAIT_ROLL and self.engine.current is PlayerId.HUMAN
        self.roll_button.enabled = self.roll_button.visible

        # keep win-probability bars current
        for pid, player in self.engine.players.items():
            self.win_bars[pid].set(self.de.analyze(player.position).win_probability)

        ph = self.phase
        if ph is Phase.WAIT_ROLL:
            if self.engine.current is PlayerId.AI:
                self.auto_timer -= dt
                if self.auto_timer <= 0:
                    self._start_roll()
        elif ph is Phase.ROLLING:
            if not any(d.rolling for d in self.dice):
                for d in self.dice:
                    d.consume_finished()
                self._after_roll()
        elif ph is Phase.CHOOSE:
            self.hover_die = next((i for i, d in enumerate(self.dice)
                                   if d.selectable and d.valid and d.rect.collidepoint(mouse_pos())), None)
        elif ph is Phase.AI_THINK:
            self._update_ai_think(dt)
        elif ph is Phase.MOVING:
            self._update_walk(dt)
        elif ph is Phase.SPECIAL:
            self._update_special(dt)
        elif ph is Phase.SHIELD_FX:
            self._update_shield_fx(dt)
        elif ph is Phase.TURN_END:
            limit = VICTORY_DELAY if self.engine.game_over else TURN_END_DELAY
            if self.phase_time >= limit:
                if self.engine.game_over:
                    self._show_victory()
                else:
                    self._finish_turn()
        elif ph is Phase.VICTORY:
            self._confetti_t += dt
            if self._confetti_t > 0.35:
                self._confetti_t = 0.0
                w = self.engine.winner
                col = PLAYER_COLOR[w] if w else theme.GOLD
                vp = self.app.viewport
                self.particles.fountain(random.uniform(vp.x + vp.w * 0.2, vp.right - vp.w * 0.2),
                                        vp.bottom - S(20), random.choice([col, theme.GOLD, theme.CYAN, theme.MAGENTA]), 18)

    def _update_ai_think(self, dt: float) -> None:
        assert self.decision is not None
        self.think_t += dt
        chosen = self.decision.chosen
        if not self.verdict_shown and self.think_t >= VERDICT_AT and chosen is not None:
            self.verdict_shown = True
            self.dice[chosen].chosen = True
            self.app.audio.play("ai")
            c = self.dice[chosen].rect.center
            self.particles.burst(c[0], c[1], theme.MAGENTA, 18)
        if self.think_t >= THINK_TIME:
            if chosen is None:
                self.engine.skip_turn()
                self.app.toasts.push("AI cannot move this turn", theme.ORANGE)
                self.phase, self.phase_time = Phase.TURN_END, 0.0
            else:
                self._begin_move(self.engine.select_die(chosen))

    def _update_walk(self, dt: float) -> None:
        w = self.walk
        assert w is not None
        tok = self.tokens[w.pid]
        w.prog += dt / STEP_TIME
        while w.prog >= 1.0 and w.idx < len(w.cells):
            cell = w.cells[w.idx]
            tok.cell, tok.frac = cell, BoardRenderer.cell_center_frac(cell)
            self.app.audio.play("move", 0.35)
            x, y = self.renderer.cell_center(cell)
            self.particles.emit(x, y + self.renderer.cell_px * 0.2, PLAYER_COLOR[w.pid], 5, speed=60,
                                life=0.5, size=S(3))
            w.idx += 1
            w.prog -= 1.0
        if w.idx >= len(w.cells):
            tok.lift = 0.0
            self.walk = None
            self._on_landed()
            return
        prev = w.start if w.idx == 0 else w.cells[w.idx - 1]
        a, b = BoardRenderer.cell_center_frac(prev), BoardRenderer.cell_center_frac(w.cells[w.idx])
        e = ease_in_out_cubic(clamp01(w.prog))
        tok.frac = (a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e)
        tok.lift = math.sin(math.pi * clamp01(w.prog)) * 0.42

    def _update_special(self, dt: float) -> None:
        sp = self.special
        assert sp is not None
        sp.elapsed += dt
        p = clamp01(sp.elapsed / sp.duration)
        tok = self.tokens[sp.pid]
        tok.frac = polyline_point(sp.path, ease_in_out_cubic(p))
        tok.lift = 0.10 if sp.kind is SpecialKind.LADDER else 0.0
        tok.scale = 1.0 + 0.12 * math.sin(p * math.pi) if sp.kind is SpecialKind.LADDER \
            else 1.0 - 0.18 * math.sin(p * math.pi)
        sp.spark_timer -= dt
        if sp.spark_timer <= 0:
            sp.spark_timer = 0.03
            x, y = self.renderer.frac_to_screen(tok.frac)
            if sp.kind is SpecialKind.LADDER:
                self.particles.sparkle_trail(x, y, theme.GOLD)
            else:
                self.particles.sparkle_trail(x, y, theme.RED)
        if p >= 1.0:
            tok.scale = 1.0
            self.special = None
            x, y = self.renderer.frac_to_screen(tok.frac)
            self.particles.burst(x, y, theme.GREEN if sp.kind is SpecialKind.LADDER else theme.RED, 16)
            self._after_special()

    def _update_shield_fx(self, dt: float) -> None:
        fx = self.shield_fx
        assert fx is not None
        fx.elapsed += dt
        if fx.elapsed >= SHIELD_FX_TIME:
            self.shield_fx = None
            self._after_special()

    # =================================================================== draw
    def draw(self, surface: pygame.Surface, vp: pygame.Rect) -> None:
        lay = compute_layout(vp)
        self.renderer.set_rect(lay.board)
        self._sync_idle_tokens()
        self._draw_header(surface, lay.header)
        self._draw_board(surface)
        self._draw_status(surface, lay.status)
        self._draw_dice(surface, lay.dice)
        self._draw_stats(surface, lay.stats)
        self._draw_ai(surface, lay.ai)
        self._draw_log(surface, lay.log)
        self._draw_status_bar(surface, lay.bar)
        self._draw_hover_tooltips(surface)
        self.particles.draw(surface)
        self.shield_modal.draw(surface)
        self.pause_modal.draw(surface)
        if self.phase is Phase.VICTORY:
            self._draw_victory(surface, vp)

    def _sync_idle_tokens(self) -> None:
        """Snap tokens to their logical cell whenever they are not being animated."""
        for pid, tok in self.tokens.items():
            animating = (self.walk is not None and self.walk.pid is pid) or \
                        (self.special is not None and self.special.pid is pid)
            if not animating:
                pos = self.engine.players[pid].position
                # while a snake/ladder outcome is pending the engine already holds the final cell
                if self.phase in (Phase.MOVING, Phase.SHIELD_PROMPT):
                    pos = tok.cell
                tok.cell = pos
                tok.frac = BoardRenderer.cell_center_frac(pos)
                tok.lift, tok.scale = 0.0, 1.0

    # ---------------------------------------------------------------- header
    def _draw_header(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        tf = fonts.get(28, True)
        draw.draw_text(surface, "AI SNAKE & LADDER", tf, theme.CYAN, (rect.x + S(2), rect.y + S(2)))
        draw.draw_text(surface, "AI SNAKE & LADDER", tf, (245, 250, 255), (rect.x, rect.y), shadow=True)
        draw.draw_text(surface, "STRATEGIC GAMEPLAY DASHBOARD", fonts.get(11.5, True), theme.TEXT_DIM,
                       (rect.x + S(3), rect.y + S(36)))
        bw, bh, gap = S(104), S(34), S(10)
        x = rect.right
        for b in reversed(self.header_buttons):
            x -= bw
            b.rect = pygame.Rect(x, rect.y + S(8), bw, bh)
            x -= gap
            b.draw(surface)

    # ----------------------------------------------------------------- board
    def _draw_board(self, surface: pygame.Surface) -> None:
        r, t = self.renderer, self.time
        r.draw(surface, t, heat=self.btn_heat.active)
        if self.btn_route.active:
            cur = self.engine.current
            cell = self.engine.players[cur].position
            r.draw_route(surface, self.app.bundle.bfs.path(cell), PLAYER_COLOR[cur], t)
        if self.phase in (Phase.WAIT_ROLL, Phase.CHOOSE, Phase.ROLLING):
            cur = self.engine.current
            r.draw_cell_ring(surface, self.engine.players[cur].position, PLAYER_COLOR[cur], t, 0.55)
        if self.phase is Phase.CHOOSE and self.hover_die is not None:
            plan = self.engine.plan_for(self.hover_die)
            if plan is not None:
                r.draw_cell_ring(surface, plan.landing, theme.TEXT, t, 0.6)
                if plan.special is SpecialKind.NONE:
                    label = str(plan.landing)
                else:
                    kind = "ladder" if plan.special is SpecialKind.LADDER else "snake"
                    label = f"{plan.landing}  {kind} > {plan.destination}"
                    dest_color = theme.GREEN if plan.special is SpecialKind.LADDER else theme.RED
                    r.draw_destination_marker(surface, plan.destination, dest_color, t, "")
                r.draw_destination_marker(surface, plan.landing, PLAYER_COLOR[self.engine.current], t, label)
        if self.phase is Phase.AI_THINK and self.decision and self.verdict_shown and self.decision.chosen_candidate:
            c = self.decision.chosen_candidate
            r.draw_destination_marker(surface, c.result_cell, theme.MAGENTA, t, f"AI > {c.result_cell}")

        # tokens: back-to-front so the lower token overlaps the upper one
        order = sorted(PlayerId, key=lambda p: self.tokens[p].frac[1])
        h, a = self.tokens[PlayerId.HUMAN], self.tokens[PlayerId.AI]
        together = math.dist(h.frac, a.frac) < 0.02
        for pid in order:
            tok = self.tokens[pid]
            off = 0.0
            if together:
                off = -r.cell_px * 0.2 if pid is PlayerId.HUMAN else r.cell_px * 0.2
            r.draw_token(surface, tok.frac, PLAYER_COLOR[pid], t, lift=tok.lift * r.cell_px,
                         x_offset=off, phase=0.0 if pid is PlayerId.HUMAN else 1.7, scale=tok.scale)
        self._draw_shield_fx(surface)

    def _draw_shield_fx(self, surface: pygame.Surface) -> None:
        fx = self.shield_fx
        if not fx:
            return
        tok = self.tokens[fx.pid]
        x, y = self.renderer.frac_to_screen(tok.frac)
        cs = self.renderer.cell_px
        p = clamp01(fx.elapsed / SHIELD_FX_TIME)
        for i in range(3):
            q = clamp01((p - i * 0.12) / 0.7)
            if 0 < q < 1:
                rad = cs * (0.4 + 1.2 * ease_out_cubic(q))
                pygame.draw.circle(surface, draw.with_alpha(theme.GOLD, 255)[:3], (int(x), int(y)), int(rad), max(2, S(3)))
        draw.draw_glow(surface, (x, y), cs * 1.3, theme.GOLD, int(150 * (1 - p)))
        rise = ease_out_cubic(p) * cs * 0.4
        draw.draw_shield(surface, x, y - cs * 0.75 - rise, cs * 0.30, theme.GOLD, True, 1.0 - p)

    # ---------------------------------------------------------------- status
    def _status_badge(self) -> tuple[str, theme.Color]:
        ph, cur = self.phase, self.engine.current
        if ph is Phase.VICTORY or self.engine.game_over:
            return "GAME OVER", theme.GOLD
        if cur is PlayerId.HUMAN:
            if ph in (Phase.WAIT_ROLL,):
                return "YOUR TURN", theme.CYAN
            if ph is Phase.ROLLING:
                return "ROLLING", theme.CYAN
            if ph is Phase.CHOOSE:
                return "CHOOSE A DIE", theme.GOLD
            if ph is Phase.SHIELD_PROMPT:
                return "SHIELD?", theme.GOLD
            return "MOVING", theme.CYAN
        if ph in (Phase.AI_THINK,):
            return "AI ANALYZING", theme.MAGENTA
        return "AI TURN", theme.MAGENTA

    def _draw_status(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        panel = self.panels["status"]
        c = panel.draw_background(surface, rect)
        text, col = self._status_badge()
        top_h = S(30)
        draw.draw_text(surface, f"TURN {self.engine.turn_number}", fonts.get(22, True), theme.TEXT,
                       (c.x, c.y + top_h // 2), "midleft")
        StatusBadge.draw(surface, text, col, (c.right, c.y + top_h // 2), "midright", self.time, dot=True)
        area = pygame.Rect(c.x, c.y + top_h + S(4), c.w, c.h - top_h - S(4))
        gap = S(6)
        rh = (area.h - gap) // 2
        for i, pid in enumerate((PlayerId.HUMAN, PlayerId.AI)):
            row = pygame.Rect(area.x, area.y + i * (rh + gap), area.w, rh)
            self._draw_player_row(surface, row, pid)
        panel.draw_veil(surface, rect)

    def _draw_player_row(self, surface: pygame.Surface, row: pygame.Rect, pid: PlayerId) -> None:
        player = self.engine.players[pid]
        color = PLAYER_COLOR[pid]
        active = self.engine.current is pid and not self.engine.game_over
        Card.draw(surface, row, color, glow=0.55 + 0.35 * pulse(self.time, 1.0) if active else 0.0)
        pad = S(9)
        line1_y = row.y + int(row.h * 0.32)
        pawn_r = max(4, row.h * 0.11)
        draw.draw_pawn(surface, row.x + pad + pawn_r * 1.3, row.y + int(row.h * 0.55), pawn_r, color, 90)
        nx = row.x + pad + int(pawn_r * 3.2)
        draw.draw_text(surface, pid.value.upper(), fonts.get(14, True), color, (nx, line1_y), "midleft")
        nw = fonts.get(14, True).size(pid.value.upper())[0]
        draw.draw_text(surface, f"Cell {player.position}", fonts.get(13), theme.TEXT,
                       (nx + nw + S(10), line1_y), "midleft")
        # shields (graphical icons)
        ssz = max(5, row.h * 0.13)
        for k in range(SHIELDS_PER_PLAYER):
            sx = row.right - pad - ssz - k * (ssz * 2.4)
            draw.draw_shield(surface, sx, line1_y, ssz, theme.GOLD, filled=(k < player.shields),
                             glow=0.4 if k < player.shields else 0.0)
        # win probability bar
        bar_y = row.y + int(row.h * 0.72)
        label = fonts.get(10.5, True)
        draw.draw_text(surface, "LR WIN", label, theme.TEXT_DIM, (nx, bar_y), "midleft")
        lw = label.size("LR WIN")[0] + S(8)
        prob = self.de.analyze(player.position).win_probability
        pct_w = S(36)
        bar = pygame.Rect(nx + lw, bar_y - S(4), row.right - pad - pct_w - nx - lw, S(8))
        self.win_bars[pid].draw(surface, bar, color)
        draw.draw_text(surface, f"{prob:.0%}", fonts.get(12, True), theme.TEXT, (row.right - pad, bar_y), "midright")

    # ------------------------------------------------------------------ dice
    def _draw_dice(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        panel = self.panels["dice"]
        c = panel.draw_background(surface, rect)
        btn_h, label_h, gap = S(38), S(20), S(8)
        d = max(S(48), min(S(96), c.h - btn_h - label_h - gap * 2 - S(2)))
        d = min(d, (c.w - S(40)) // 2)
        space = S(30)
        total = 2 * d + space
        x0 = c.centerx - total // 2
        y = c.y + S(2)
        cur_color = PLAYER_COLOR[self.engine.current]
        for i, die in enumerate(self.dice):
            die.rect = pygame.Rect(x0 + i * (d + space), y, d, d)
            die.set_accent(cur_color)
            die.draw(surface, self.time)
            val = "-" if self.engine.dice is None else str(self.engine.dice[i])
            active = die.selectable and die.valid
            col = theme.GOLD if die.chosen else (theme.TEXT if active else theme.TEXT_DIM)
            draw.draw_text(surface, f"DICE {i + 1}: {val}", fonts.get(12.5, True), col,
                           (die.rect.centerx, die.rect.bottom + S(10) + S(6)), "midtop")
        area = pygame.Rect(c.x, c.bottom - btn_h, c.w, btn_h)
        self.roll_button.rect = area
        if self.roll_button.visible:
            self.roll_button.draw(surface)
        else:
            hint = {
                Phase.ROLLING: "Rolling the dice...",
                Phase.CHOOSE: "Click a die (or press 1 / 2) - hover to preview",
                Phase.AI_THINK: "AI is evaluating both moves",
                Phase.MOVING: "Moving...",
                Phase.SHIELD_PROMPT: "Use a shield against the snake?",
                Phase.SHIELD_FX: "Shield activated!",
                Phase.SPECIAL: "Snake / ladder in action",
                Phase.TURN_END: "Turn complete",
                Phase.VICTORY: "Game over",
            }.get(self.phase, "AI is about to roll..." if self.engine.current is PlayerId.AI else "")
            hf = fonts.get(12.5)
            draw.draw_text(surface, draw.ellipsize(hf, hint, area.w), hf, theme.TEXT_DIM, area.center, "center")
        panel.draw_veil(surface, rect)

    # ----------------------------------------------------------------- stats
    def _draw_stats(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        panel = self.panels["stats"]
        c = panel.draw_background(surface, rect)
        eng, de = self.engine, self.de
        h, a = eng.players[PlayerId.HUMAN], eng.players[PlayerId.AI]
        gap = S(6)
        chart_h = int(c.h * 0.38)
        grid_h = c.h - chart_h - gap
        cw = (c.w - gap) // 2
        ch = (grid_h - 2 * gap) // 3
        active = eng.active
        an_active = de.analyze(active.position)
        zone_col = theme.ZONE_COLORS.get(an_active.zone, theme.TEXT)
        h_an, a_an = de.analyze(h.position), de.analyze(a.position)
        cards = [
            ("Round", str(eng.turn_number), f"{active.name}", theme.TEXT, None),
            ("Current risk zone", an_active.zone, "K-Means", zone_col, zone_col),
            ("Min rolls to goal", f"{h_an.bfs_rolls} / {a_an.bfs_rolls}", "H / AI", theme.CYAN, None),
            ("Snakes encountered", f"{h.snakes_hit} / {a.snakes_hit}", "H / AI", theme.RED, None),
            ("Ladders encountered", f"{h.ladders_hit} / {a.ladders_hit}", "H / AI", theme.GREEN, None),
            ("Shields used", f"{h.shields_used} / {a.shields_used}", "H / AI", theme.GOLD, None),
        ]
        for i, (label, value, sub, col, accent) in enumerate(cards):
            r, cidx = divmod(i, 2)
            rect_i = pygame.Rect(c.x + cidx * (cw + gap), c.y + r * (ch + gap), cw, ch)
            StatCard.draw(surface, rect_i, label, value, sub, col, accent)
        hist = eng.history
        hs = [x[1] for x in hist] + [h.position]
        as_ = [x[2] for x in hist] + [a.position]
        chart_rect = pygame.Rect(c.x, c.bottom - chart_h, c.w, chart_h)
        self.chart.draw(surface, chart_rect, [(theme.HUMAN_COLOR, hs), (theme.AI_COLOR, as_)], 100,
                        "Board progress by round")
        panel.draw_veil(surface, rect)

    # -------------------------------------------------------------- AI panel
    def _draw_ai(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        panel = self.panels["ai"]
        c = panel.draw_background(surface, rect)
        if self.decision is None:
            badge, bcol = "WAITING", theme.TEXT_DIM
        elif self.phase is Phase.AI_THINK and not self.verdict_shown:
            badge, bcol = "ANALYZING", theme.MAGENTA
        else:
            badge, bcol = "DECIDED", theme.GREEN
        StatusBadge.draw(surface, badge, bcol, (rect.right - S(14), rect.y + S(11)), "topright", self.time,
                         dot=self.phase is Phase.AI_THINK)
        footer_h, verdict_h, gap = S(54), S(46), S(8)
        cards_h = c.h - footer_h - verdict_h - gap * 2
        card_h = (cards_h - gap) // 2
        for i in range(2):
            self._draw_candidate(surface, pygame.Rect(c.x, c.y + i * (card_h + gap), c.w, card_h), i)
        verdict = pygame.Rect(c.x, c.y + cards_h + gap, c.w, verdict_h)
        self._draw_verdict(surface, verdict)
        footer = pygame.Rect(c.x, verdict.bottom + gap // 2, c.w, footer_h)
        self._draw_ai_footer(surface, footer)
        panel.draw_veil(surface, rect)

    def _draw_candidate(self, surface: pygame.Surface, rect: pygame.Rect, i: int) -> None:
        dec = self.decision
        cand = dec.candidates[i] if dec else None
        chosen = bool(dec and self.verdict_shown and dec.chosen == i)
        dimmed = bool(dec and self.verdict_shown and dec.chosen is not None and dec.chosen != i)
        accent = theme.GOLD if chosen else theme.MAGENTA
        Card.draw(surface, rect, accent, glow=(0.6 + 0.3 * pulse(self.time, 1.3)) if chosen else 0.0)
        pad = S(9)
        inner = rect.inflate(-2 * pad, -S(8))
        hh = int(inner.h * 0.22)
        bh = int(inner.h * 0.19)
        f_head = fonts.get(13, True)
        label = "AB"[i]
        if cand is None:
            draw.draw_text(surface, f"DICE OPTION {label}", f_head, theme.TEXT_FAINT, (inner.x, inner.y + hh // 2), "midleft")
            draw.draw_text(surface, "-", fonts.get(13), theme.TEXT_FAINT, (inner.right, inner.y + hh // 2), "midright")
            for k, bar in enumerate(self.cand_bars[i]):
                row = pygame.Rect(inner.x, inner.y + hh + k * bh, inner.w, bh)
                bar.draw(surface, row, dim=True)
            return
        head_col = theme.GOLD if chosen else (theme.TEXT_FAINT if dimmed else theme.TEXT)
        draw.draw_text(surface, f"DICE OPTION {label}: {cand.die_value}", f_head, head_col,
                       (inner.x, inner.y + hh // 2), "midleft")
        dest = f"Destination: {cand.result_cell}" if cand.valid else "Illegal move"
        df = fonts.get(12.5, True)
        draw.draw_text(surface, dest, df, theme.RED if not cand.valid else (theme.CYAN if not dimmed else theme.TEXT_FAINT),
                       (inner.right, inner.y + hh // 2), "midright")
        for k, bar in enumerate(self.cand_bars[i]):
            row = pygame.Rect(inner.x, inner.y + hh + k * bh, inner.w, bh)
            bar.draw(surface, row, dim=dimmed or not cand.valid)
        bottom = pygame.Rect(inner.x, inner.y + hh + 3 * bh, inner.w, inner.bottom - (inner.y + hh + 3 * bh))
        if cand.valid and cand.analysis:
            zc = theme.ZONE_COLORS.get(cand.zone, theme.TEXT)
            badge = StatusBadge.draw(surface, cand.zone, zc if not dimmed else theme.TEXT_FAINT,
                                     (bottom.x, bottom.centery), "midleft", self.time, size=10.5)
            nf = fonts.get(11)
            note = f"BFS {cand.analysis.bfs_rolls} rolls | {cand.note}"
            draw.draw_text(surface, draw.ellipsize(nf, note, bottom.right - badge.right - S(8)), nf,
                           theme.TEXT_DIM if not dimmed else theme.TEXT_FAINT,
                           (badge.right + S(8), bottom.centery), "midleft")
        else:
            nf = fonts.get(11)
            draw.draw_text(surface, draw.ellipsize(nf, cand.note, bottom.w), nf, theme.TEXT_DIM,
                           (bottom.x, bottom.centery), "midleft")

    def _draw_verdict(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        dec = self.decision
        if dec is None:
            Card.draw(surface, rect)
            f = fonts.get(13)
            draw.draw_text(surface, "Waiting for the AI's turn...", f, theme.TEXT_DIM, rect.center, "center")
            return
        if not self.verdict_shown and self.phase is Phase.AI_THINK:
            Card.draw(surface, rect, theme.MAGENTA)
            dots = "." * (1 + int(self.time * 3) % 3)
            draw.draw_text(surface, "Analyzing candidates" + dots, fonts.get(14, True), theme.MAGENTA, rect.center, "center")
            return
        chosen = dec.chosen_candidate
        Card.draw(surface, rect, theme.GOLD if chosen else theme.ORANGE, glow=0.5 + 0.3 * pulse(self.time, 1.1) if chosen else 0.1)
        head = f"AI CHOOSES DICE {chosen.die_value}" if chosen else "AI CANNOT MOVE"
        tf = fonts.get(16, True)
        tw = tf.size(head)[0]
        cx = rect.centerx
        y = rect.y + int(rect.h * 0.34)
        if chosen:
            draw.draw_check(surface, cx - tw // 2 - S(16), y, S(8), theme.GREEN, max(2, S(3)))
        draw.draw_text(surface, head, tf, theme.GOLD if chosen else theme.ORANGE, (cx + S(2), y), "center", shadow=True)
        rf = fonts.get(11)
        reason = dec.reason
        if self.shield_note is not None:
            sn = self.shield_note
            reason = (f"Shield {'used' if sn.use else 'kept'}: est. loss {sn.loss_cells} cells, "
                      f"benefit {sn.benefit:+.2f} vs {sn.threshold:.2f}")
        draw.draw_text(surface, draw.ellipsize(rf, reason, rect.w - S(16)), rf, theme.TEXT_DIM,
                       (cx, rect.bottom - int(rect.h * 0.22)), "center")

    def _draw_ai_footer(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        pos = self.engine.players[PlayerId.AI].position
        an = self.de.analyze(pos)
        rows = [
            ("BFS PATH ANALYSIS", theme.CYAN, f"Current Cell: {pos}  |  Minimum Rolls to Goal: {an.bfs_rolls}"),
            ("LOGISTIC REGRESSION", theme.GREEN, f"Estimated Win Probability: {an.win_probability:.0%}"),
            ("K-MEANS", theme.ZONE_COLORS.get(an.zone, theme.TEXT), f"Risk zone: {an.zone}  (hazard {an.hazard:+.2f})"),
        ]
        rh = rect.h // 3
        lf, vf = fonts.get(10.5, True), fonts.get(11.5)
        for i, (name, col, value) in enumerate(rows):
            y = rect.y + i * rh + rh // 2
            draw.draw_text(surface, name, lf, col, (rect.x + S(2), y), "midleft")
            x = rect.x + S(2) + max(lf.size(n)[0] for n, _, _ in rows) + S(10)
            draw.draw_text(surface, draw.ellipsize(vf, value, rect.right - x), vf, theme.TEXT_DIM, (x, y), "midleft")

    # ------------------------------------------------------------------- log
    def _draw_log(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        panel = self.panels["log"]
        c = panel.draw_background(surface, rect)
        self.log_widget.draw(surface, c, self.engine.events, time.time(), 1 / 60)
        panel.draw_veil(surface, rect)

    # ------------------------------------------------------------ status bar
    def _draw_status_bar(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        draw.fill_rrect(surface, rect, (12, 16, 36, 200), rect.h // 2)
        draw.stroke_rrect(surface, rect, (100, 120, 190, 70), rect.h // 2, 1)
        f = fonts.get(11.5)
        hint = "SPACE roll   1 / 2 choose die   Y / N shield   H risk map   P BFS path   M sound   ESC menu"
        right = f"BFS  A*  Logistic Regression  K-Means   |   {self.app.fps:.0f} FPS"
        rw = f.size(right)[0]
        draw.draw_text(surface, draw.ellipsize(f, hint, rect.w - rw - S(40)), f, theme.TEXT_DIM,
                       (rect.x + S(16), rect.centery), "midleft")
        draw.draw_text(surface, right, f, theme.TEXT_FAINT, (rect.right - S(16), rect.centery), "midright")

    # --------------------------------------------------------------- tooltip
    def _draw_hover_tooltips(self, surface: pygame.Surface) -> None:
        if self.shield_modal.visible or self.pause_modal.visible or self.phase is Phase.VICTORY:
            return
        pos = mouse_pos()
        if self.phase is Phase.CHOOSE and self.hover_die is not None:
            plan = self.engine.plan_for(self.hover_die)
            if plan:
                lines: list = [f"Move {plan.die_value}: cell {plan.start} > {plan.landing}"]
                if plan.special is SpecialKind.LADDER:
                    lines.append((f"Ladder! climbs to cell {plan.destination}", theme.GREEN))
                elif plan.special is SpecialKind.SNAKE:
                    lines.append((f"Snake! slides to cell {plan.destination}", theme.RED))
                    if plan.shield_available:
                        lines.append(("A shield can block it", theme.GOLD))
                an = self.de.analyze(plan.destination)
                lines.append(f"LR win {an.win_probability:.0%}  |  BFS {an.bfs_rolls} rolls")
                Tooltip.draw(surface, lines, pos, f"DICE {self.hover_die + 1}", theme.CYAN)
            return
        cell = self.renderer.cell_at(pos)
        if cell is not None and not any(d.rect.collidepoint(pos) for d in self.dice):
            an = self.de.analyze(cell)
            kind = self.app.board.kind_at(cell)
            lines = [f"Zone: {an.zone}   BFS {an.bfs_rolls} rolls",
                     f"A* {an.astar_score:.2f}   LR win {an.win_probability:.0%}"]
            if kind is SpecialKind.SNAKE:
                lines.insert(0, (f"Snake head > cell {self.app.board.snakes[cell]}", theme.RED))
            elif kind is SpecialKind.LADDER:
                lines.insert(0, (f"Ladder bottom > cell {self.app.board.ladders[cell]}", theme.GREEN))
            Tooltip.draw(surface, lines, pos, f"CELL {cell}", theme.ZONE_COLORS.get(an.zone, theme.CYAN))

    # --------------------------------------------------------------- victory
    def _draw_victory(self, surface: pygame.Surface, vp: pygame.Rect) -> None:
        p = clamp01(self.victory_anim.progress)
        sw, sh = surface.get_size()
        veil = pygame.Surface((sw, sh), pygame.SRCALPHA)
        veil.fill((4, 6, 16, int(200 * p)))
        surface.blit(veil, (0, 0))
        winner = self.engine.winner or PlayerId.HUMAN
        color = PLAYER_COLOR[winner]
        w, h = min(S(600), vp.w - S(40)), min(S(470), vp.h - S(40))
        scale = 0.85 + 0.15 * self.victory_anim.value
        rect = pygame.Rect(0, 0, int(w * scale), int(h * scale))
        rect.center = vp.center
        draw.draw_glow_rect(surface, rect, color, S(24), S(30), int(120 * p))
        surface.blit(draw.glass_panel_surface(rect.w, rect.h, S(24), color, 245), rect.topleft)
        if p < 0.4:
            return
        cx = rect.centerx
        draw.draw_star(surface, cx, rect.y + S(62), S(34) + math.sin(self.time * 3) * S(3), theme.GOLD, self.time * 0.6)
        tf = fonts.get(50, True)
        draw.draw_text(surface, "VICTORY", tf, draw.darken(theme.GOLD, 0.4), (cx + S(3), rect.y + S(108) + S(3)), "midtop")
        draw.draw_text(surface, "VICTORY", tf, theme.GOLD, (cx, rect.y + S(108)), "midtop")
        draw.draw_text(surface, f"{winner.value.upper()} WINS", fonts.get(26, True), color, (cx, rect.y + S(176)), "midtop", shadow=True)
        tagline = ("Your strategy conquered the board" if winner is PlayerId.HUMAN
                   else "Strategic intelligence conquered the board")
        draw.draw_text(surface, tagline, fonts.get(15), theme.TEXT_DIM, (cx, rect.y + S(216)), "midtop")
        pl = self.engine.players[winner]
        stats = [f"Turns: {pl.turns}", f"Final Position: {pl.position}",
                 f"Snakes {pl.snakes_hit}  |  Ladders {pl.ladders_hit}  |  Shields used {pl.shields_used}"]
        y = rect.y + S(254)
        for s in stats:
            draw.draw_text(surface, s, fonts.get(15, True), theme.TEXT, (cx, y), "midtop")
            y += S(24)
        bw, bh = S(200), S(50)
        for i, b in enumerate(self.victory_buttons):
            b.rect = pygame.Rect(cx - bw - S(8) + i * (bw + S(16)), rect.bottom - S(28) - bh, bw, bh)
            b.draw(surface)
