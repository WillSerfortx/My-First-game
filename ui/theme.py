"""
Theme module for AI-Powered Snake & Ladder.
Provides a cohesive, futuristic dark glassmorphism design system,
color palette tokens, responsive font loaders, and surface drawing helpers.
"""

import pygame
from typing import Tuple, Optional, Dict, List


class Theme:
    """
    Design tokens and graphic utilities for the application.
    """

    # Background Colors
    BG_DARK: Tuple[int, int, int] = (11, 15, 25)          # Deep Obsidian
    BG_PANEL: Tuple[int, int, int] = (17, 24, 39)         # Dark Navy Glass
    BG_CARD: Tuple[int, int, int] = (31, 41, 55)          # Elevated Charcoal
    BG_CARD_HOVER: Tuple[int, int, int] = (45, 55, 72)
    BG_CELL_LIGHT: Tuple[int, int, int] = (20, 27, 45)    # Board alternating cell
    BG_CELL_DARK: Tuple[int, int, int] = (15, 20, 35)

    # Accent & Player Colors
    CYAN_HUMAN: Tuple[int, int, int] = (6, 182, 212)       # Human neon cyan
    CYAN_HUMAN_GLOW: Tuple[int, int, int] = (34, 211, 238)
    PURPLE_AI: Tuple[int, int, int] = (168, 85, 247)       # AI cyber purple
    PURPLE_AI_GLOW: Tuple[int, int, int] = (192, 132, 252)

    # Game Mechanics Colors
    GREEN_LADDER: Tuple[int, int, int] = (16, 185, 129)    # Emerald Green
    GREEN_ADVANTAGE: Tuple[int, int, int] = (52, 211, 153)
    RED_SNAKE: Tuple[int, int, int] = (239, 68, 68)        # Crimson Red
    RED_DANGER: Tuple[int, int, int] = (248, 113, 113)
    AMBER_SHIELD: Tuple[int, int, int] = (245, 158, 11)    # Golden Amber
    BLUE_SAFE: Tuple[int, int, int] = (59, 130, 246)       # Electric Blue

    # UI Borders and Dividers
    BORDER_DEFAULT: Tuple[int, int, int] = (55, 65, 81)
    BORDER_ACCENT: Tuple[int, int, int] = (99, 102, 241)   # Indigo Glow
    BORDER_HIGHLIGHT: Tuple[int, int, int] = (147, 197, 253)

    # Typography Colors
    TEXT_WHITE: Tuple[int, int, int] = (248, 250, 252)
    TEXT_MUTED: Tuple[int, int, int] = (156, 163, 175)
    TEXT_SUBTLE: Tuple[int, int, int] = (107, 114, 128)
    TEXT_DARK: Tuple[int, int, int] = (31, 41, 55)

    # Font Cache
    _font_cache: Dict[Tuple[str, int, bool], pygame.font.Font] = {}

    @classmethod
    def get_font(cls, size: int = 16, bold: bool = False) -> pygame.font.Font:
        """Loads and caches system fonts with fallbacks."""
        key = ("default", size, bold)
        if key not in cls._font_cache:
            if not pygame.font.get_init():
                pygame.font.init()

            try:
                font = pygame.font.SysFont("helvetica,arial,segoeui,roboto,sans-serif", size, bold=bold)
            except Exception:
                font = pygame.font.Font(None, size)

            if font is None:
                font = pygame.font.Font(None, size)

            cls._font_cache[key] = font

        return cls._font_cache[key]

    @classmethod
    def draw_rounded_rect(
        cls,
        surface: pygame.Surface,
        rect: pygame.Rect,
        color: Tuple[int, ...],
        radius: int = 8,
        border_color: Optional[Tuple[int, ...]] = None,
        border_width: int = 1,
    ) -> None:
        """Draws a rounded rectangle with antialiased borders and alpha support."""
        if len(color) == 4 and color[3] < 255:
            shape_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(shape_surf, color, (0, 0, rect.width, rect.height), border_radius=radius)
            if border_color and border_width > 0:
                pygame.draw.rect(
                    shape_surf, border_color, (0, 0, rect.width, rect.height), border_width, border_radius=radius
                )
            surface.blit(shape_surf, rect.topleft)
        else:
            pygame.draw.rect(surface, color, rect, border_radius=radius)
            if border_color and border_width > 0:
                pygame.draw.rect(surface, border_color, rect, border_width, border_radius=radius)

    @classmethod
    def draw_glass_panel(
        cls,
        surface: pygame.Surface,
        rect: pygame.Rect,
        radius: int = 12,
        border_color: Optional[Tuple[int, ...]] = None,
        alpha: int = 220,
    ) -> None:
        """Renders a translucent glassmorphism container with soft border."""
        color = (cls.BG_PANEL[0], cls.BG_PANEL[1], cls.BG_PANEL[2], alpha)
        b_color = border_color if border_color else cls.BORDER_DEFAULT
        cls.draw_rounded_rect(surface, rect, color, radius=radius, border_color=b_color, border_width=1)

    @classmethod
    def draw_glow_circle(
        cls,
        surface: pygame.Surface,
        center: Tuple[int, int],
        radius: int,
        color: Tuple[int, int, int],
        glow_radius: int = 10,
        alpha: int = 120,
    ) -> None:
        """Draws a glowing neon aura around a circle."""
        cx, cy = center
        total_radius = radius + glow_radius
        glow_surf = pygame.Surface((total_radius * 2, total_radius * 2), pygame.SRCALPHA)

        # Multi-stage feathering for smooth light diffusion
        steps = 4
        for i in range(steps, 0, -1):
            r = radius + (glow_radius * i // steps)
            a = int(alpha * (steps - i + 1) / (steps * 2))
            glow_color = (color[0], color[1], color[2], a)
            pygame.draw.circle(glow_surf, glow_color, (total_radius, total_radius), r)

        # Inner solid core
        pygame.draw.circle(glow_surf, color, (total_radius, total_radius), radius)
        surface.blit(glow_surf, (cx - total_radius, cy - total_radius), special_flags=pygame.BLEND_ALPHA_SDL2)

    @classmethod
    def draw_badge(
        cls,
        surface: pygame.Surface,
        text: str,
        pos: Tuple[int, int],
        bg_color: Tuple[int, int, int],
        text_color: Tuple[int, int, int] = (255, 255, 255),
        font_size: int = 12,
    ) -> pygame.Rect:
        """Draws a compact pill status badge."""
        font = cls.get_font(font_size, bold=True)
        txt_surf = font.render(text.upper(), True, text_color)
        pad_x, pad_y = 8, 4
        badge_rect = pygame.Rect(pos[0], pos[1], txt_surf.get_width() + pad_x * 2, txt_surf.get_height() + pad_y * 2)
        cls.draw_rounded_rect(surface, badge_rect, bg_color, radius=badge_rect.height // 2)
        surface.blit(txt_surf, (pos[0] + pad_x, pos[1] + pad_y))
        return badge_rect
