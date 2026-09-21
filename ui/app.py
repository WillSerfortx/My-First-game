"""Application shell: window, screen manager, background AI loading and main loop."""
from __future__ import annotations

import sys
import threading
import traceback

import pygame

from ai.decision_engine import DecisionEngine
from ai.pipeline import AIBundle, build_ai
from game.board import Board

from . import theme
from .audio import AudioManager
from .game_screen import GameScreen
from .particles import AmbientField
from .screens import AILabScreen, HomeScreen, HowItWorksScreen
from .widgets import ToastManager

INITIAL_SIZE = (1440, 900)
MIN_SIZE = (960, 600)
MIN_ASPECT, MAX_ASPECT = 1.35, 2.0     # layout viewport is letter-boxed to this range
TARGET_FPS = 60


class AILoader:
    """Trains / loads the AI in a background thread so the menu stays responsive."""

    def __init__(self, board: Board) -> None:
        self.board = board
        self.progress = 0.0
        self.message = "Starting"
        self.bundle: AIBundle | None = None
        self.error: str | None = None
        self._thread = threading.Thread(target=self._run, name="ai-loader", daemon=True)

    @property
    def ready(self) -> bool:
        return self.bundle is not None

    def start(self) -> None:
        self._thread.start()

    def _on_progress(self, fraction: float, message: str) -> None:
        self.progress, self.message = fraction, message

    def _run(self) -> None:
        try:
            self.bundle = build_ai(self.board, progress=self._on_progress)
        except Exception as first:                       # corrupt cache etc. -> retrain from scratch
            try:
                self.bundle = build_ai(self.board, progress=self._on_progress, force=True)
            except Exception as second:
                self.error = f"{type(second).__name__}: {second}" if second else str(first)


class App:
    """Owns the pygame window, shared services and the active screen."""

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("AI-Powered Snake & Ladder")
        size = INITIAL_SIZE
        try:
            info = pygame.display.Info()
            if info.current_w > 0 and info.current_h > 0:
                size = (min(size[0], int(info.current_w * 0.96)), min(size[1], int(info.current_h * 0.92)))
        except Exception:
            pass
        self.surface = pygame.display.set_mode((max(size[0], MIN_SIZE[0]), max(size[1], MIN_SIZE[1])),
                                               pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.fps = 0.0
        self.running = True
        self.viewport = pygame.Rect(0, 0, *INITIAL_SIZE)

        self.board = Board()
        self.audio = AudioManager()
        self.toasts = ToastManager()
        self.ambient = AmbientField()
        self.loader = AILoader(self.board)
        self.loader.start()
        self.decision_engine: DecisionEngine | None = None

        self.screens: dict[str, object] = {
            "home": HomeScreen(self),
            "how": HowItWorksScreen(self),
            "lab": AILabScreen(self),
        }
        self.game: GameScreen | None = None
        self.current_name = "home"
        self._error_streak = 0

    # ------------------------------------------------------------------ AI
    @property
    def bundle(self) -> AIBundle | None:
        return self.loader.bundle

    def _ensure_engine(self) -> None:
        if self.decision_engine is None and self.loader.bundle is not None:
            self.decision_engine = DecisionEngine(self.loader.bundle)

    # ------------------------------------------------------------ navigation
    def goto(self, name: str) -> None:
        if name == "game":
            if self.game is None:
                self.start_game()
                return
            self.current_name = "game"
            return
        self.current_name = name
        screen = self.screens.get(name)
        if screen is not None and hasattr(screen, "on_enter"):
            screen.on_enter()

    def start_game(self) -> None:
        self._ensure_engine()
        if self.decision_engine is None:
            self.toasts.push("The AI is not ready yet", theme.GOLD)
            return
        self.game = GameScreen(self)
        self.current_name = "game"

    def quit(self) -> None:
        self.running = False

    @property
    def screen(self):
        return self.game if self.current_name == "game" and self.game else self.screens[
            self.current_name if self.current_name in self.screens else "home"]

    # -------------------------------------------------------------- viewport
    def _compute_viewport(self, size: tuple[int, int]) -> pygame.Rect:
        w, h = size
        aspect = w / max(1, h)
        vw, vh = w, h
        if aspect > MAX_ASPECT:
            vw = int(h * MAX_ASPECT)
        elif aspect < MIN_ASPECT:
            vh = int(w / MIN_ASPECT)
        vp = pygame.Rect(0, 0, vw, vh)
        vp.center = (w // 2, h // 2)
        theme.set_scale(min(vw / theme.DESIGN_W, vh / theme.DESIGN_H))
        return vp

    # ------------------------------------------------------------------ loop
    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.VIDEORESIZE:
            w, h = event.w, event.h
            if w < MIN_SIZE[0] or h < MIN_SIZE[1]:
                self.surface = pygame.display.set_mode((max(w, MIN_SIZE[0]), max(h, MIN_SIZE[1])),
                                                       pygame.RESIZABLE)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
            try:
                pygame.display.toggle_fullscreen()
            except Exception:
                pass
        else:
            self.screen.handle_event(event)

    def _frame(self, dt: float) -> None:
        self.surface = pygame.display.get_surface() or self.surface
        self.viewport = self._compute_viewport(self.surface.get_size())
        self._ensure_engine()
        for event in pygame.event.get():
            self._handle_event(event)
        if not self.running:
            return
        self.ambient.update(dt)
        self.toasts.update(dt)
        screen = self.screen
        screen.update(dt)
        self.ambient.draw(self.surface)
        screen.draw(self.surface, self.viewport)
        self.toasts.draw(self.surface, self.viewport.y + int(theme.S(14)))
        pygame.display.flip()

    def run(self) -> None:
        while self.running:
            dt = min(0.05, self.clock.tick(TARGET_FPS) / 1000.0)
            self.fps = self.clock.get_fps()
            try:
                self._frame(dt)
                self._error_streak = 0
            except Exception:                    # never crash the demo on an unexpected error
                traceback.print_exc(file=sys.stderr)
                self._error_streak += 1
                if self._error_streak >= 20:
                    self._error_streak = 0
                    self.toasts.push("Recovered from an error - returning to the menu", theme.RED)
                    self.game = None
                    self.current_name = "home"
        pygame.quit()
