"""
Screen Management module for AI-Powered Snake & Ladder.
Implements:
- ScreenManager (Screen switcher and persistent event routing)
- HomeScreen (Landing menu with animated particles)
- GameScreen (Main dashboard with board, dual dice, AI transparency panel, shields, event log)
- AnalyticsScreen (AI Lab with 100-cell K-Means heatmap, feature inspector, and real ML metrics)
- HowItWorksModal (Rules and 4 AI algorithms explanation)
"""

import pygame
from enum import Enum, auto
from typing import Optional, Dict, Any, Tuple, List

from game.board import Board
from game.player import Player
from game.game_engine import GameEngine, TurnPhase
from ai.bfs import BFSAnalyzer
from ai.astar import AStarScorer
from ai.features import FeatureExtractor
from ai.data_generator import DatasetSimulator
from ai.logistic_model import LogisticWinModel
from ai.kmeans_model import KMeansRiskModel
from ai.decision_engine import AIDecisionEngine

from .theme import Theme
from .widgets import Button, Card, DiceWidget, ShieldWidget, DecisionScoreBar, EventLogWidget, StatCard, Modal
from .board_renderer import BoardRenderer
from .particles import ParticleManager
from .audio import AudioManager


class ScreenType(Enum):
    HOME = auto()
    GAME = auto()
    ANALYTICS = auto()


class ScreenManager:
    """
    Coordinates active screen state, transitions, and persistent UI buttons/widgets.
    """

    def __init__(self, screen_size: Tuple[int, int] = (1440, 900)):
        self.screen_size: Tuple[int, int] = screen_size

        # Shared game components
        self.board: Board = Board()
        self.engine: GameEngine = GameEngine(self.board)

        # Shared AI components
        self.feature_extractor: FeatureExtractor = FeatureExtractor(self.board)
        self.bfs: BFSAnalyzer = BFSAnalyzer(self.board)
        self.astar: AStarScorer = AStarScorer(self.board, self.bfs)
        self.simulator: DatasetSimulator = DatasetSimulator(self.board, self.feature_extractor)
        self.logistic: LogisticWinModel = LogisticWinModel(self.feature_extractor)
        self.kmeans: KMeansRiskModel = KMeansRiskModel(self.feature_extractor)
        self.decision_engine: AIDecisionEngine = AIDecisionEngine(
            self.board, self.bfs, self.astar, self.logistic, self.kmeans
        )

        # UI & Media
        self.board_renderer: BoardRenderer = BoardRenderer(self.board)
        self.particles: ParticleManager = ParticleManager()
        self.audio: AudioManager = AudioManager()

        # Screens & modals
        self.current_screen_type: ScreenType = ScreenType.HOME
        self.active_modal: Optional[Modal] = None

        # AI thinking timer for realistic turn pacing
        self.ai_timer: float = 0.0
        self.ai_roll_delay: float = 0.0
        self.ai_calculated_decision: Optional[Dict[str, Any]] = None

        # Analytics inspection selection
        self.inspected_cell: int = 45

        # Initialize interactive buttons and layouts
        self._init_buttons()
        self.resize(screen_size[0], screen_size[1])

    def _init_buttons(self) -> None:
        """Initializes persistent Button instances with callbacks."""
        # 1. Home Screen Buttons
        self.btn_home_start = Button(
            pygame.Rect(0, 0, 280, 50),
            "START GAME",
            callback=self._action_start_game,
            bg_color=(16, 185, 129),
            hover_color=(52, 211, 153),
            border_color=(16, 185, 129),
            font_size=16,
        )
        self.btn_home_lab = Button(
            pygame.Rect(0, 0, 280, 50),
            "AI LAB / ANALYTICS",
            callback=lambda: self.switch_screen(ScreenType.ANALYTICS),
            bg_color=Theme.BG_CARD,
            hover_color=Theme.BG_CARD_HOVER,
            border_color=Theme.BORDER_ACCENT,
            font_size=15,
        )
        self.btn_home_rules = Button(
            pygame.Rect(0, 0, 280, 50),
            "HOW IT WORKS",
            callback=self._show_rules_modal,
            bg_color=Theme.BG_CARD,
            hover_color=Theme.BG_CARD_HOVER,
            border_color=Theme.BORDER_DEFAULT,
            font_size=15,
        )
        self.btn_home_quit = Button(
            pygame.Rect(0, 0, 280, 50),
            "QUIT",
            callback=lambda: pygame.event.post(pygame.event.Event(pygame.QUIT)),
            bg_color=(35, 20, 25),
            hover_color=(239, 68, 68),
            border_color=Theme.RED_SNAKE,
            font_size=15,
        )
        self.home_buttons = [
            self.btn_home_start,
            self.btn_home_lab,
            self.btn_home_rules,
            self.btn_home_quit,
        ]

        # 2. Game Screen Buttons
        self.btn_roll = Button(
            pygame.Rect(0, 0, 160, 48),
            "ROLL DICE",
            callback=self._action_roll_dice,
            bg_color=Theme.CYAN_HUMAN,
            hover_color=Theme.CYAN_HUMAN_GLOW,
            border_color=Theme.CYAN_HUMAN,
            font_size=15,
        )
        self.btn_game_lab = Button(
            pygame.Rect(0, 0, 150, 40),
            "AI LAB",
            callback=lambda: self.switch_screen(ScreenType.ANALYTICS),
            bg_color=Theme.BG_CARD,
            border_color=Theme.BORDER_ACCENT,
            font_size=13,
        )
        self.btn_game_restart = Button(
            pygame.Rect(0, 0, 150, 40),
            "RESTART",
            callback=self._action_restart_game,
            bg_color=Theme.BG_CARD,
            font_size=13,
        )
        self.btn_game_menu = Button(
            pygame.Rect(0, 0, 150, 40),
            "MAIN MENU",
            callback=lambda: self.switch_screen(ScreenType.HOME),
            bg_color=Theme.BG_CARD,
            font_size=13,
        )
        self.game_toolbar_buttons = [
            self.btn_game_lab,
            self.btn_game_restart,
            self.btn_game_menu,
        ]

        # Rectangles for dual dice interactive selection
        self.dice_1_rect = pygame.Rect(0, 0, 64, 64)
        self.dice_2_rect = pygame.Rect(0, 0, 64, 64)

        # 3. Analytics Screen Buttons
        self.btn_analytics_back = Button(
            pygame.Rect(0, 0, 150, 36),
            "← BACK TO GAME",
            callback=lambda: self.switch_screen(ScreenType.GAME),
            bg_color=Theme.BG_CARD,
            border_color=Theme.CYAN_HUMAN,
            font_size=13,
        )
        self.btn_analytics_retrain = Button(
            pygame.Rect(0, 0, 240, 38),
            "RE-SIMULATE 10,000 GAMES",
            callback=self._re_simulate_models,
            bg_color=Theme.BG_CARD,
            border_color=Theme.BORDER_ACCENT,
            font_size=12,
        )
        self.analytics_buttons = [
            self.btn_analytics_back,
            self.btn_analytics_retrain,
        ]

    def _action_start_game(self) -> None:
        self.engine.start_new_game()
        self.switch_screen(ScreenType.GAME)

    def _action_restart_game(self) -> None:
        self.engine.start_new_game()
        self.audio.play("click")

    def _action_roll_dice(self) -> None:
        if self.engine.phase == TurnPhase.IDLE:
            self.engine.trigger_roll()
            self.audio.play("dice")

    def resize(self, width: int, height: int) -> None:
        """Adapts UI layouts and button rectangles dynamically upon window resize."""
        self.screen_size = (max(1200, width), max(750, height))
        sw, sh = self.screen_size

        # Board layout on left
        board_dim = min(sw * 0.52, sh - 120)
        board_rect = pygame.Rect(40, (sh - board_dim) // 2 + 20, int(board_dim), int(board_dim))
        self.board_renderer.update_layout(board_rect)

        # Home screen buttons layout
        cx = sw // 2
        cy = sh // 2
        btn_w, btn_h = 280, 50
        btn_x = cx - btn_w // 2

        self.btn_home_start.rect = pygame.Rect(btn_x, cy - 40, btn_w, btn_h)
        self.btn_home_lab.rect = pygame.Rect(btn_x, cy + 25, btn_w, btn_h)
        self.btn_home_rules.rect = pygame.Rect(btn_x, cy + 90, btn_w, btn_h)
        self.btn_home_quit.rect = pygame.Rect(btn_x, cy + 155, btn_w, btn_h)

        # Game screen dashboard coordinates on right
        dash_x = self.board_renderer.board_rect.right + 25
        dash_w = sw - dash_x - 30

        # Dice panel positions
        dice_panel_y = 95
        self.dice_1_rect = pygame.Rect(dash_x + 24, dice_panel_y + 45, 64, 64)
        self.dice_2_rect = pygame.Rect(dash_x + 115, dice_panel_y + 45, 64, 64)
        self.btn_roll.rect = pygame.Rect(dash_x + dash_w - 180, dice_panel_y + 50, 160, 48)

        # Game bottom toolbar
        tb_w = (dash_w - 24) // 3
        tb_y = sh - 55
        self.btn_game_lab.rect = pygame.Rect(dash_x, tb_y, tb_w, 40)
        self.btn_game_restart.rect = pygame.Rect(dash_x + tb_w + 12, tb_y, tb_w, 40)
        self.btn_game_menu.rect = pygame.Rect(dash_x + (tb_w + 12) * 2, tb_y, tb_w, 40)

        # Analytics buttons
        self.btn_analytics_back.rect = pygame.Rect(sw - 180, 30, 140, 36)
        right_x = 520
        metrics_rect_bottom = sh - 40
        self.btn_analytics_retrain.rect = pygame.Rect(right_x + 16, metrics_rect_bottom - 50, 240, 38)

    def switch_screen(self, screen_type: ScreenType) -> None:
        """Switches active screen."""
        self.current_screen_type = screen_type
        self.active_modal = None
        self.audio.play("click")

    # =========================================================================
    # EVENT HANDLING & UPDATE
    # =========================================================================

    def handle_event(self, event: pygame.event.Event) -> None:
        """Dispatches events to active modal, buttons, or board."""
        # 1. Check Active Modal First
        if self.active_modal is not None:
            if self.active_modal.handle_event(event):
                return
            # Click outside dismisses informational modal
            if event.type == pygame.MOUSEBUTTONDOWN and not self.active_modal.rect.collidepoint(event.pos):
                if self.engine.phase != TurnPhase.WAITING_HUMAN_SHIELD:
                    self.active_modal = None
            return

        # 2. Route based on Screen Type
        if self.current_screen_type == ScreenType.HOME:
            self._handle_home_event(event)
        elif self.current_screen_type == ScreenType.GAME:
            self._handle_game_event(event)
        elif self.current_screen_type == ScreenType.ANALYTICS:
            self._handle_analytics_event(event)

    def update(self, dt: float) -> None:
        """Updates game state machine, animations, AI delays, and buttons."""
        self.particles.update(dt, self.screen_size)

        if self.active_modal:
            self.active_modal.update(dt)
            return

        # Update button hover states
        if self.current_screen_type == ScreenType.HOME:
            for btn in self.home_buttons:
                btn.update(dt)
        elif self.current_screen_type == ScreenType.GAME:
            self.btn_roll.update(dt)
            for btn in self.game_toolbar_buttons:
                btn.update(dt)
            self._update_game(dt)
        elif self.current_screen_type == ScreenType.ANALYTICS:
            for btn in self.analytics_buttons:
                btn.update(dt)

    # =========================================================================
    # HOME SCREEN
    # =========================================================================

    def _handle_home_event(self, event: pygame.event.Event) -> None:
        for btn in self.home_buttons:
            if btn.handle_event(event):
                return

    def _draw_home(self, surface: pygame.Surface) -> None:
        """Renders cinematic landing menu."""
        sw, sh = self.screen_size
        surface.fill(Theme.BG_DARK)
        self.particles.draw(surface)

        # Title card banner
        font_large = Theme.get_font(42, bold=True)
        font_sub = Theme.get_font(18, bold=False)

        title_surf = font_large.render("AI-POWERED SNAKE & LADDER", True, Theme.TEXT_WHITE)
        sub_surf = font_sub.render(
            "Strategic Gameplay with Intelligent Decision-Making • 4 AI Models", True, Theme.CYAN_HUMAN
        )

        cx = sw // 2
        cy = sh // 2

        surface.blit(title_surf, (cx - title_surf.get_width() // 2, cy - 180))
        surface.blit(sub_surf, (cx - sub_surf.get_width() // 2, cy - 125))

        # Render Persistent Home Buttons
        for btn in self.home_buttons:
            btn.draw(surface)

    def _show_rules_modal(self) -> None:
        """Displays explanation modal of game rules and the 4 AI algorithms."""
        sw, sh = self.screen_size
        modal_w, modal_h = 740, 520
        modal_rect = pygame.Rect((sw - modal_w) // 2, (sh - modal_h) // 2, modal_w, modal_h)

        msg = (
            "GAMEPLAY & DECISION-MAKING:\n"
            "• Each turn rolls TWO dice. You choose one value to execute your move.\n"
            "• Each player has 2 SHIELD power-ups to block snakes and save position.\n"
            "• First player to reach cell 100 wins! Overshoots bounce backward.\n\n"
            "INTEGRATED FOUR AI TECHNIQUES:\n"
            "1. BFS: Computes the shortest path & minimum rolls to cell 100 lookup table.\n"
            "2. A*: Evaluates candidate move trajectories with heuristic scoring [0.0 - 1.0].\n"
            "3. Logistic Regression: Predicts win probability [0.0 - 1.0] trained on 10,000 games.\n"
            "4. K-Means (K=3): Clusters board cells into DANGER, SAFE, and ADVANTAGE risk zones.\n\n"
            "AI Decision Formula:  final_score = 0.60 * A* + 0.40 * Logistic Regression\n"
            "Evaluates both candidates dynamically every round."
        )

        b_close = Button(
            pygame.Rect(modal_rect.centerx - 80, modal_rect.bottom - 60, 160, 42),
            "GOT IT",
            callback=lambda: setattr(self, "active_modal", None),
            bg_color=Theme.BORDER_ACCENT,
            font_size=14,
        )

        self.active_modal = Modal(
            modal_rect,
            title="AI Snake & Ladder — Architecture & Rules",
            message=msg,
            buttons=[b_close],
            accent_color=Theme.CYAN_HUMAN,
        )

    # =========================================================================
    # GAME SCREEN
    # =========================================================================

    def _handle_game_event(self, event: pygame.event.Event) -> None:
        """Handles user dice selection, roll button clicks, and toolbar actions."""
        # 1. Roll button click
        is_human_turn = not self.engine.current_player.is_ai
        if is_human_turn and self.engine.phase == TurnPhase.IDLE:
            if self.btn_roll.handle_event(event):
                return

        # 2. Human Dice Selection during WAITING_HUMAN_SELECTION
        if self.engine.phase == TurnPhase.WAITING_HUMAN_SELECTION:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.dice_1_rect.collidepoint(event.pos):
                    self.audio.play("click")
                    self.particles.emit_dice_burst(self.dice_1_rect.center)
                    self.engine.human_select_dice(0)
                    self._check_shield_prompt()
                    return
                elif self.dice_2_rect.collidepoint(event.pos):
                    self.audio.play("click")
                    self.particles.emit_dice_burst(self.dice_2_rect.center)
                    self.engine.human_select_dice(1)
                    self._check_shield_prompt()
                    return

        # 3. Bottom Toolbar Buttons
        for btn in self.game_toolbar_buttons:
            if btn.handle_event(event):
                return

    def _check_shield_prompt(self) -> None:
        """Displays modal if human player landed on a snake and has shields."""
        if self.engine.phase == TurnPhase.WAITING_HUMAN_SHIELD:
            sw, sh = self.screen_size
            modal_w, modal_h = 520, 280
            modal_rect = pygame.Rect((sw - modal_w) // 2, (sh - modal_h) // 2, modal_w, modal_h)

            pending = self.engine.pending_move
            landing = pending["landing_cell"]
            tail = self.board.get_snake_tail(landing)
            loss = landing - tail if tail else 0

            msg = (
                f"SNAKE THREAT AT CELL {landing}!\n"
                f"Without protection, you will slide down to cell {tail} (-{loss} cells).\n"
                f"You have {self.engine.human.shields} shield(s) available.\n"
                f"Deploy shield to retain your current position?"
            )

            b_use = Button(
                pygame.Rect(modal_rect.x + 40, modal_rect.bottom - 65, 200, 44),
                "DEPLOY SHIELD",
                callback=lambda: (
                    self.audio.play("shield"),
                    self.particles.emit_shield_shockwave(modal_rect.center),
                    self.engine.human_resolve_shield(True),
                    setattr(self, "active_modal", None),
                ),
                bg_color=Theme.AMBER_SHIELD,
                font_size=14,
            )

            b_slide = Button(
                pygame.Rect(modal_rect.right - 240, modal_rect.bottom - 65, 200, 44),
                "TAKE SLIDE",
                callback=lambda: (
                    self.audio.play("snake"),
                    self.particles.emit_snake_sizzle(modal_rect.center),
                    self.engine.human_resolve_shield(False),
                    setattr(self, "active_modal", None),
                ),
                bg_color=(45, 55, 72),
                font_size=14,
            )

            self.active_modal = Modal(
                modal_rect,
                title="SHIELD DEFENSE ACTIVATION",
                message=msg,
                buttons=[b_use, b_slide],
                accent_color=Theme.AMBER_SHIELD,
            )

    def _update_game(self, dt: float) -> None:
        """Drives turns, movement animation, AI thinking delay, and sounds."""
        # 0. Automatic AI Turn Roll Trigger
        if self.engine.phase == TurnPhase.IDLE and self.engine.current_player.is_ai:
            self.ai_roll_delay += dt
            if self.ai_roll_delay >= 0.2:  # Crisp 0.2s pause before AI rolls
                self.ai_roll_delay = 0.0
                self.engine.trigger_roll()
                self.audio.play("dice")
                return
        else:
            self.ai_roll_delay = 0.0

        # 1. Dice rolling physics
        if self.engine.phase == TurnPhase.ROLLING_DICE:
            finished = self.engine.update_dice_roll(dt)
            if finished:
                self.audio.play("dice")

        # 2. AI Turn Decision & Animation Delay
        elif self.engine.phase == TurnPhase.AI_THINKING:
            self.ai_timer += dt
            if self.ai_calculated_decision is None:
                self.ai_calculated_decision = self.decision_engine.evaluate_candidates(
                    current_cell=self.engine.ai.position,
                    dice_values=self.engine.dice.values,
                    ai_shields=self.engine.ai.shields,
                )

            # Fast 0.35s delay so user can observe AI decision without tedious waiting
            if self.ai_timer >= 0.35:
                dec = self.ai_calculated_decision
                use_shield = dec["use_shield"]
                if use_shield:
                    self.audio.play("shield")
                    self.particles.emit_shield_shockwave((self.screen_size[0] // 2, self.screen_size[1] // 2))
                self.engine.execute_ai_turn(dec["chosen_index"], use_shield, dec)
                self.ai_timer = 0.0
                self.ai_calculated_decision = None

        # 3. Player Movement Animation
        elif self.engine.phase == TurnPhase.MOVING_PLAYER:
            done = self.engine.update_movement(dt)
            if done:
                move_info = self.engine.pending_move or {}
                if move_info.get("hit_ladder"):
                    self.audio.play("ladder")
                    self.particles.emit_ladder_sparkle(
                        self.board_renderer.cell_centers.get(self.engine.current_player.position, (0, 0))
                    )
                elif move_info.get("hit_snake") and not move_info.get("shield_used"):
                    self.audio.play("snake")
                    self.particles.emit_snake_sizzle(
                        self.board_renderer.cell_centers.get(self.engine.current_player.position, (0, 0))
                    )
                else:
                    self.audio.play("move")

                # Check game over
                if self.engine.phase == TurnPhase.GAME_OVER and self.active_modal is None:
                    self.audio.play("victory")
                    self.particles.emit_victory_confetti(self.screen_size[0], self.screen_size[1])
                    self._show_victory_modal()

    def _show_victory_modal(self) -> None:
        """Displays victory card."""
        sw, sh = self.screen_size
        modal_w, modal_h = 560, 360
        modal_rect = pygame.Rect((sw - modal_w) // 2, (sh - modal_h) // 2, modal_w, modal_h)

        winner = self.engine.winner
        w_name = winner.name if winner else "Player"
        color = Theme.PURPLE_AI if (winner and winner.is_ai) else Theme.CYAN_HUMAN

        msg = (
            f"CHAMPION: {w_name.upper()}!\n\n"
            f"Total Turns: {self.engine.turn_number}\n"
            f"Ladders Climbed: {winner.ladders_climbed if winner else 0}\n"
            f"Snakes Encountered: {winner.snakes_encountered if winner else 0}\n"
            f"Shields Remaining: {winner.shields if winner else 0}\n\n"
            f"Strategic intelligence dominated the board!"
        )

        b_again = Button(
            pygame.Rect(modal_rect.x + 40, modal_rect.bottom - 65, 220, 44),
            "PLAY AGAIN",
            callback=lambda: (self.engine.start_new_game(), setattr(self, "active_modal", None)),
            bg_color=(16, 185, 129),
            font_size=15,
        )
        b_menu = Button(
            pygame.Rect(modal_rect.right - 260, modal_rect.bottom - 65, 220, 44),
            "MAIN MENU",
            callback=lambda: (setattr(self, "active_modal", None), self.switch_screen(ScreenType.HOME)),
            bg_color=Theme.BG_CARD,
            font_size=15,
        )

        self.active_modal = Modal(
            modal_rect, title="VICTORY ACQUIRED", message=msg, buttons=[b_again, b_menu], accent_color=color
        )

    def _draw_game(self, surface: pygame.Surface) -> None:
        """Renders the comprehensive game dashboard."""
        sw, sh = self.screen_size
        surface.fill(Theme.BG_DARK)
        self.particles.draw(surface)

        # 1. Render Left Side: 10x10 Board
        hovered_cell = self.board_renderer.get_cell_at_pos(pygame.mouse.get_pos())
        self.board_renderer.draw(
            surface,
            human_player=self.engine.human,
            ai_player=self.engine.ai,
            cell_zones=self.kmeans.cell_zones if self.kmeans.is_trained else None,
            hovered_cell=hovered_cell,
        )

        # 2. Render Right Side: Dashboard Panels
        dash_x = self.board_renderer.board_rect.right + 25
        dash_w = sw - dash_x - 30

        # Header: Game Status Card
        self._draw_status_card(surface, pygame.Rect(dash_x, 20, dash_w, 65))

        # Panel 1: Dual-Dice Options Card
        self._draw_dice_panel(surface, pygame.Rect(dash_x, 95, dash_w, 140))

        # Panel 2: AI Decision Transparency Panel
        self._draw_ai_decision_panel(surface, pygame.Rect(dash_x, 245, dash_w, 245))

        # Panel 3: Shields & Quick Stats
        self._draw_stats_panel(surface, pygame.Rect(dash_x, 500, dash_w, 110))

        # Panel 4: Event Log Card
        log_rect = pygame.Rect(dash_x, 620, dash_w, sh - 690)
        self._draw_event_log(surface, log_rect)

        # Bottom Navigation Controls
        self._draw_bottom_toolbar(surface)

    def _draw_status_card(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Renders current turn, active player, and game phase."""
        Theme.draw_glass_panel(surface, rect, radius=10, border_color=Theme.BORDER_DEFAULT)

        curr = self.engine.current_player
        is_human = not curr.is_ai
        accent = Theme.CYAN_HUMAN if is_human else Theme.PURPLE_AI

        # Turn indicator
        font_turn = Theme.get_font(13, bold=True)
        t_surf = font_turn.render(f"ROUND {self.engine.turn_number}", True, Theme.TEXT_MUTED)
        surface.blit(t_surf, (rect.x + 16, rect.y + 12))

        # Active player banner
        font_p = Theme.get_font(18, bold=True)
        p_surf = font_p.render(f"{curr.name.upper()}'S TURN", True, accent)
        surface.blit(p_surf, (rect.x + 16, rect.y + 32))

        # Phase description badge
        phase_desc = "Ready to Roll"
        if self.engine.phase == TurnPhase.ROLLING_DICE:
            phase_desc = "Tumbling Dice..."
        elif self.engine.phase == TurnPhase.WAITING_HUMAN_SELECTION:
            phase_desc = "Choose Dice 1 or 2!"
        elif self.engine.phase == TurnPhase.AI_THINKING:
            phase_desc = "AI Evaluating 4 Models..."
        elif self.engine.phase == TurnPhase.MOVING_PLAYER:
            phase_desc = "Moving Token..."
        elif self.engine.phase == TurnPhase.GAME_OVER:
            phase_desc = "Game Finished!"

        Theme.draw_badge(
            surface,
            phase_desc,
            (rect.right - 180, rect.y + 20),
            bg_color=(24, 32, 48),
            text_color=Theme.TEXT_WHITE,
        )

    def _draw_dice_panel(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Renders dual dice options with roll button and selection highlights."""
        Theme.draw_glass_panel(surface, rect, radius=10, border_color=Theme.BORDER_DEFAULT)

        font_lbl = Theme.get_font(12, bold=True)
        lbl = font_lbl.render("DUAL-DICE DECISION SELECTION", True, Theme.TEXT_MUTED)
        surface.blit(lbl, (rect.x + 16, rect.y + 12))

        # Two dice widgets
        d1_val = self.engine.dice.display_values[0]
        d2_val = self.engine.dice.display_values[1]
        rot1 = self.engine.dice.rotation_angles[0]
        rot2 = self.engine.dice.rotation_angles[1]

        d1_w = DiceWidget(size=64)
        d2_w = DiceWidget(size=64)

        is_human_turn = not self.engine.current_player.is_ai
        d1_w.is_selectable = (self.engine.phase == TurnPhase.WAITING_HUMAN_SELECTION)
        d2_w.is_selectable = (self.engine.phase == TurnPhase.WAITING_HUMAN_SELECTION)

        mpos = pygame.mouse.get_pos()
        d1_w.is_hovered = self.dice_1_rect.collidepoint(mpos) and d1_w.is_selectable
        d2_w.is_hovered = self.dice_2_rect.collidepoint(mpos) and d2_w.is_selectable
        d1_w.is_selected = (self.engine.dice.selected_index == 0)
        d2_w.is_selected = (self.engine.dice.selected_index == 1)

        d1_w.draw(surface, self.dice_1_rect.topleft, d1_val, rotation=rot1)
        d2_w.draw(surface, self.dice_2_rect.topleft, d2_val, rotation=rot2)

        # Draw Roll Button
        if is_human_turn and self.engine.phase == TurnPhase.IDLE:
            self.btn_roll.text = "ROLL DICE"
            self.btn_roll.bg_color = Theme.CYAN_HUMAN
            self.btn_roll.draw(surface)
        elif not is_human_turn and self.engine.phase == TurnPhase.IDLE:
            # Show AI auto-rolling status
            txt_surf = Theme.get_font(14, bold=True).render("AI ROLLING...", True, Theme.PURPLE_AI)
            surface.blit(txt_surf, (self.btn_roll.rect.x + 20, self.btn_roll.rect.centery - 8))
        elif self.engine.phase == TurnPhase.WAITING_HUMAN_SELECTION:
            txt_surf = Theme.get_font(13, bold=True).render("← CLICK A DICE!", True, Theme.AMBER_SHIELD)
            surface.blit(txt_surf, (self.btn_roll.rect.x + 10, self.btn_roll.rect.centery - 8))
        else:
            txt_surf = Theme.get_font(13, bold=False).render("Processing...", True, Theme.TEXT_MUTED)
            surface.blit(txt_surf, (self.btn_roll.rect.x + 20, self.btn_roll.rect.centery - 8))

    def _draw_ai_decision_panel(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Renders the AI decision explanation transparency panel."""
        Theme.draw_glass_panel(surface, rect, radius=10, border_color=Theme.PURPLE_AI, alpha=235)

        font_hdr = Theme.get_font(13, bold=True)
        h_surf = font_hdr.render("AI DECISION ENGINE (TRANSPARENCY)", True, Theme.PURPLE_AI_GLOW)
        surface.blit(h_surf, (rect.x + 16, rect.y + 12))

        # Formula label
        font_form = Theme.get_font(10, bold=False)
        form_surf = font_form.render("Weighting: 0.60 * A* Score + 0.40 * Win Probability", True, Theme.TEXT_SUBTLE)
        surface.blit(form_surf, (rect.right - form_surf.get_width() - 16, rect.y + 14))

        dec = self.ai_calculated_decision or self.engine.ai_decision_data

        if dec is None:
            font_sub = Theme.get_font(13, bold=False)
            sub = font_sub.render("Waiting for AI roll to perform dual-candidate analysis...", True, Theme.TEXT_SUBTLE)
            surface.blit(sub, (rect.x + 16, rect.y + 110))
            return

        cand_a = dec["candidate_a"]
        cand_b = dec["candidate_b"]
        chosen = dec["chosen_index"]

        half_w = (rect.width - 44) // 2
        col1_rect = pygame.Rect(rect.x + 16, rect.y + 38, half_w, 165)
        col2_rect = pygame.Rect(rect.x + 28 + half_w, rect.y + 38, half_w, 165)

        self._draw_candidate_column(surface, col1_rect, cand_a, is_chosen=(chosen == 0))
        self._draw_candidate_column(surface, col2_rect, cand_b, is_chosen=(chosen == 1))

        bot_y = rect.bottom - 32
        font_exp = Theme.get_font(11, bold=True)
        chosen_dice = dec["chosen_dice"]
        shield_txt = " • Shield Deployed!" if dec["use_shield"] else ""
        expl_surf = font_exp.render(f"✓ AI CHOOSES DICE {chosen_dice}{shield_txt}", True, Theme.GREEN_ADVANTAGE)
        surface.blit(expl_surf, (rect.x + 16, bot_y))

    def _draw_candidate_column(
        self, surface: pygame.Surface, rect: pygame.Rect, cand: Dict[str, Any], is_chosen: bool
    ) -> None:
        """Renders Candidate A or Candidate B metrics."""
        border = Theme.GREEN_ADVANTAGE if is_chosen else Theme.BORDER_DEFAULT
        bg = (24, 34, 52) if is_chosen else (18, 24, 38)
        Theme.draw_rounded_rect(surface, rect, bg, radius=6, border_color=border, border_width=2 if is_chosen else 1)

        font = Theme.get_font(12, bold=True)
        hdr = f"{cand['label']}: Value [{cand['roll']}] → Cell {cand['final_cell']}"
        h_s = font.render(hdr, True, Theme.TEXT_WHITE)
        surface.blit(h_s, (rect.x + 8, rect.y + 6))

        zone = cand.get("risk_zone", "Safe")
        z_color = (
            Theme.RED_DANGER if zone == "Danger" else (Theme.GREEN_ADVANTAGE if zone == "Advantage" else Theme.BLUE_SAFE)
        )
        Theme.draw_badge(surface, zone, (rect.right - 65, rect.y + 5), bg_color=z_color, font_size=9)

        bar_w = rect.width - 16
        bar1_rect = pygame.Rect(rect.x + 8, rect.y + 44, bar_w, 8)
        DecisionScoreBar.draw(surface, bar1_rect, "A* Score", cand["astar_score"], Theme.CYAN_HUMAN, font_size=10)

        bar2_rect = pygame.Rect(rect.x + 8, rect.y + 78, bar_w, 8)
        DecisionScoreBar.draw(
            surface, bar2_rect, "Win Prob (LR)", cand["win_probability"], Theme.PURPLE_AI, font_size=10
        )

        bar3_rect = pygame.Rect(rect.x + 8, rect.y + 112, bar_w, 8)
        DecisionScoreBar.draw(
            surface,
            bar3_rect,
            "Weighted Score",
            cand["final_score"],
            Theme.GREEN_ADVANTAGE if is_chosen else Theme.BORDER_DEFAULT,
            font_size=10,
        )

        font_min = Theme.get_font(10, bold=False)
        m_s = font_min.render(f"BFS Min Rolls: {cand['bfs_rolls']}", True, Theme.TEXT_SUBTLE)
        surface.blit(m_s, (rect.x + 8, rect.y + 130))

    def _draw_stats_panel(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Renders player shields and quick stats."""
        card_w = (rect.width - 12) // 2
        r_hum = pygame.Rect(rect.x, rect.y, card_w, rect.height)
        r_ai = pygame.Rect(rect.x + card_w + 12, rect.y, card_w, rect.height)

        h_prob = self.logistic.predict_win_probability(self.engine.human.position)
        StatCard.draw(
            surface,
            r_hum,
            label="Human Player",
            value=f"Cell {self.engine.human.position}",
            subtext=f"Shields: {self.engine.human.shields}/2 • Win Prob: {h_prob*100:.0f}%",
            accent_color=Theme.CYAN_HUMAN,
        )

        ai_prob = self.logistic.predict_win_probability(self.engine.ai.position)
        StatCard.draw(
            surface,
            r_ai,
            label="AI Agent",
            value=f"Cell {self.engine.ai.position}",
            subtext=f"Shields: {self.engine.ai.shields}/2 • Win Prob: {ai_prob*100:.0f}%",
            accent_color=Theme.PURPLE_AI,
        )

    def _draw_event_log(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Renders the scrollable event log card."""
        log_widget = EventLogWidget(rect)
        log_widget.draw(surface, self.engine.event_log)

    def _draw_bottom_toolbar(self, surface: pygame.Surface) -> None:
        """Renders persistent toolbar buttons."""
        for btn in self.game_toolbar_buttons:
            btn.draw(surface)

    # =========================================================================
    # ANALYTICS / AI LAB SCREEN
    # =========================================================================

    def _handle_analytics_event(self, event: pygame.event.Event) -> None:
        """Handles clicks on back button, retrain button, and heatmap cells."""
        for btn in self.analytics_buttons:
            if btn.handle_event(event):
                return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            heatmap_x, heatmap_y = 50, 95
            cell_size = 42
            for c in range(1, 101):
                col, row = self.board.get_cell_coordinates(c)
                r = pygame.Rect(heatmap_x + col * cell_size, heatmap_y + row * cell_size, cell_size, cell_size)
                if r.collidepoint(event.pos):
                    self.inspected_cell = c
                    self.audio.play("click")
                    break

    def _draw_analytics(self, surface: pygame.Surface) -> None:
        """Renders the AI Lab analytics screen."""
        sw, sh = self.screen_size
        surface.fill(Theme.BG_DARK)
        self.particles.draw(surface)

        font_title = Theme.get_font(24, bold=True)
        t_s = font_title.render("AI LAB — MODEL ANALYTICS & BOARD RISK HEATMAP", True, Theme.TEXT_WHITE)
        surface.blit(t_s, (50, 30))

        # Draw Back Button
        self.btn_analytics_back.draw(surface)

        # Left Column: 100-cell Risk Heatmap (K-Means)
        self._draw_heatmap_grid(surface, (50, 95))

        # Right Column: Inspected Cell & Model Performance Cards
        right_x = 520
        right_w = sw - right_x - 50

        self._draw_cell_inspector(surface, pygame.Rect(right_x, 95, right_w, 200))
        self._draw_model_metrics(surface, pygame.Rect(right_x, 310, right_w, sh - 350))

    def _draw_heatmap_grid(self, surface: pygame.Surface, pos: Tuple[int, int]) -> None:
        """Renders the interactive 10x10 K-Means cell heatmap."""
        start_x, start_y = pos
        cell_size = 42
        grid_w = cell_size * 10

        frame_rect = pygame.Rect(start_x - 10, start_y - 10, grid_w + 20, grid_w + 50)
        Theme.draw_glass_panel(surface, frame_rect, radius=12, border_color=Theme.BORDER_ACCENT)

        font_num = Theme.get_font(10, bold=True)
        mpos = pygame.mouse.get_pos()

        for c in range(1, 101):
            col, row = self.board.get_cell_coordinates(c)
            cx = start_x + col * cell_size
            cy = start_y + row * cell_size
            r = pygame.Rect(cx, cy, cell_size, cell_size)

            zone = self.kmeans.get_zone_for_cell(c)
            bg_color = (
                (180, 30, 40)
                if zone == "Danger"
                else ((20, 140, 80) if zone == "Advantage" else (30, 70, 140))
            )

            is_inspected = (c == self.inspected_cell)
            border_c = (
                (255, 255, 255)
                if is_inspected
                else ((200, 200, 200) if r.collidepoint(mpos) else Theme.BORDER_DEFAULT)
            )
            border_w = 2 if (is_inspected or r.collidepoint(mpos)) else 1

            pygame.draw.rect(surface, bg_color, r)
            pygame.draw.rect(surface, border_c, r, border_w)

            ns = font_num.render(str(c), True, (255, 255, 255))
            surface.blit(ns, (cx + 3, cy + 3))

        leg_y = start_y + grid_w + 10
        Theme.draw_badge(surface, "DANGER", (start_x, leg_y), bg_color=Theme.RED_DANGER, font_size=10)
        Theme.draw_badge(surface, "SAFE", (start_x + 90, leg_y), bg_color=Theme.BLUE_SAFE, font_size=10)
        Theme.draw_badge(surface, "ADVANTAGE", (start_x + 160, leg_y), bg_color=Theme.GREEN_ADVANTAGE, font_size=10)

    def _draw_cell_inspector(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Renders features and metrics for the currently inspected cell."""
        Theme.draw_glass_panel(surface, rect, radius=10, border_color=Theme.CYAN_HUMAN)

        c = self.inspected_cell
        feats = self.feature_extractor.extract_dict(c)
        zone = self.kmeans.get_zone_for_cell(c)
        min_rolls = self.bfs.get_min_rolls(c)
        prob = self.logistic.predict_win_probability(c)

        font_hdr = Theme.get_font(16, bold=True)
        h_s = font_hdr.render(f"INSPECTING CELL {c}", True, Theme.TEXT_WHITE)
        surface.blit(h_s, (rect.x + 16, rect.y + 14))

        z_color = (
            Theme.RED_DANGER if zone == "Danger" else (Theme.GREEN_ADVANTAGE if zone == "Advantage" else Theme.BLUE_SAFE)
        )
        Theme.draw_badge(
            surface, f"CLUSTER: {zone.upper()}", (rect.right - 180, rect.y + 14), bg_color=z_color, font_size=11
        )

        font_f = Theme.get_font(13, bold=False)
        y = rect.y + 48
        lines = [
            f"• dist_to_snake: {feats['dist_to_snake']:.1f} cells",
            f"• dist_to_ladder: {feats['dist_to_ladder']:.1f} cells",
            f"• snakes_within_6: {int(feats['snakes_within_6'])}",
            f"• ladders_within_6: {int(feats['ladders_within_6'])}",
            f"• position_pct: {feats['position_pct']*100:.0f}%",
        ]

        col1 = lines[:3]
        col2 = lines[3:] + [f"• BFS Min Rolls: {min_rolls}", f"• LR Win Prob: {prob*100:.1f}%"]

        for l in col1:
            surface.blit(font_f.render(l, True, Theme.TEXT_MUTED), (rect.x + 16, y))
            y += 24

        y2 = rect.y + 48
        for l in col2:
            surface.blit(font_f.render(l, True, Theme.TEXT_MUTED), (rect.centerx + 10, y2))
            y2 += 24

    def _draw_model_metrics(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Renders calculated machine learning validation metrics."""
        Theme.draw_glass_panel(surface, rect, radius=10, border_color=Theme.BORDER_DEFAULT)

        font_hdr = Theme.get_font(15, bold=True)
        surface.blit(
            font_hdr.render("MODEL PERFORMANCE & SIMULATION METRICS", True, Theme.TEXT_WHITE),
            (rect.x + 16, rect.y + 14),
        )

        font_body = Theme.get_font(13, bold=False)
        y = rect.y + 45

        acc_text = f"Logistic Regression Accuracy: {self.logistic.accuracy * 100:.1f}%"
        surface.blit(font_body.render(acc_text, True, Theme.CYAN_HUMAN), (rect.x + 16, y))
        y += 24

        cm = self.logistic.confusion_matrix
        cm_text = f"Confusion Matrix: [[TN={cm[0,0]}, FP={cm[0,1]}], [FN={cm[1,0]}, TP={cm[1,1]}]]"
        surface.blit(font_body.render(cm_text, True, Theme.TEXT_MUTED), (rect.x + 16, y))
        y += 28

        surface.blit(
            font_body.render("Feature Coefficients (Influence on Win):", True, Theme.TEXT_WHITE),
            (rect.x + 16, y),
        )
        y += 22
        for name, val in self.logistic.feature_coefficients.items():
            color = Theme.GREEN_ADVANTAGE if val > 0 else Theme.RED_DANGER
            c_text = f"  {name}: {val:+.4f}"
            surface.blit(font_body.render(c_text, True, color), (rect.x + 16, y))
            y += 20

        y += 10
        surface.blit(font_body.render("K-Means (K=3) Cluster Breakdown:", True, Theme.TEXT_WHITE), (rect.x + 16, y))
        y += 22
        for z_name, m in self.kmeans.cluster_metrics.items():
            z_str = f"  {z_name}: {m['count']} cells | avg_snakes_w6={m['avg_snakes_w6']} | avg_ladders_w6={m['avg_ladders_w6']}"
            surface.blit(font_body.render(z_str, True, Theme.TEXT_MUTED), (rect.x + 16, y))
            y += 20

        # Draw Retrain Button
        self.btn_analytics_retrain.draw(surface)

    def _re_simulate_models(self) -> None:
        """Simulates 10,000 games and retrains Logistic Regression & K-Means."""
        self.audio.play("click")
        X, y = self.simulator.generate_dataset(num_games=10000, force_regenerate=True)
        self.logistic.train(X, y)
        self.kmeans.fit_board(X)
        self.audio.play("ladder")

    # =========================================================================
    # MAIN DRAW ROUTER
    # =========================================================================

    def draw(self, surface: pygame.Surface) -> None:
        """Dispatches draw calls based on active screen."""
        if self.current_screen_type == ScreenType.HOME:
            self._draw_home(surface)
        elif self.current_screen_type == ScreenType.GAME:
            self._draw_game(surface)
        elif self.current_screen_type == ScreenType.ANALYTICS:
            self._draw_analytics(surface)

        if self.active_modal is not None:
            self.active_modal.draw(surface, self.screen_size)
