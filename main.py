"""
Main application entry point for AI-Powered Snake & Ladder.
Initializes Pygame window (1440x900 resizable), manages model caching/bootstrap loading,
and runs the high-performance 60 FPS delta-time loop.
"""

import sys
import os
import pygame

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from ui.theme import Theme
from ui.screens import ScreenManager, ScreenType


def main() -> None:
    """Main execution loop."""
    pygame.init()
    pygame.font.init()

    # Initial window resolution
    width, height = 1440, 900
    screen = pygame.display.set_mode((width, height), pygame.RESIZABLE | pygame.DOUBLEBUF)
    pygame.display.set_caption("AI-Powered Snake & Ladder — Strategic Decision-Making")

    clock = pygame.time.Clock()

    # Create ScreenManager
    manager = ScreenManager(screen_size=(width, height))

    # Bootstrap check: ensure 10,000 simulation models are trained & cached
    if not manager.logistic.is_trained or not manager.kmeans.is_trained:
        # Show elegant initialization splash
        screen.fill(Theme.BG_DARK)
        font_title = Theme.get_font(28, bold=True)
        font_sub = Theme.get_font(16, bold=False)

        t_surf = font_title.render("INITIALIZING AI ENGINE", True, Theme.TEXT_WHITE)
        s_surf = font_sub.render("Simulating 10,000 games & extracting 5 strategic features...", True, Theme.CYAN_HUMAN)

        screen.blit(t_surf, (width // 2 - t_surf.get_width() // 2, height // 2 - 40))
        screen.blit(s_surf, (width // 2 - s_surf.get_width() // 2, height // 2 + 10))
        pygame.display.flip()

        # Run simulation & model training
        X, y = manager.simulator.generate_dataset(num_games=10000)
        manager.logistic.train(X, y)
        manager.kmeans.fit_board(X)

    running = True
    while running:
        # Delta-time in seconds
        dt = clock.tick(60) / 1000.0
        dt = min(dt, 0.1)  # Cap delta-time to avoid spiral of death on window drag

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                width, height = max(1200, event.w), max(750, event.h)
                screen = pygame.display.set_mode((width, height), pygame.RESIZABLE | pygame.DOUBLEBUF)
                manager.resize(width, height)
            else:
                manager.handle_event(event)

        # Update animations and game state
        manager.update(dt)

        # Render active screen
        manager.draw(screen)
        pygame.display.flip()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
