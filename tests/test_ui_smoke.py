"""Headless end-to-end smoke test of the Pygame UI (skipped when pygame is missing)."""
import os
import time

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
pygame = pytest.importorskip("pygame")


def _frames(app, n):
    for _ in range(n):
        app._frame(1 / 60)


def test_screens_and_a_scripted_game_run_without_errors():
    from game.player import PlayerId
    from ui.app import App
    from ui.game_screen import Phase

    app = App()
    deadline = time.time() + 120
    while not app.loader.ready and time.time() < deadline:
        _frames(app, 1)
        time.sleep(0.01)
    assert app.loader.ready, app.loader.error

    for name in ("home", "how", "lab"):
        app.goto(name)
        _frames(app, 20)

    app.start_game()
    game = app.game
    assert game is not None
    for frame in range(1500):
        if game.phase is Phase.WAIT_ROLL and game.engine.current is PlayerId.HUMAN:
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        elif game.phase is Phase.CHOOSE:
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1 if game.dice[0].valid else pygame.K_2))
        elif game.phase is Phase.SHIELD_PROMPT:
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_y))
        _frames(app, 1)
        if game.phase is Phase.VICTORY:
            break
    assert game.engine.turn_number >= 2
    pygame.quit()
