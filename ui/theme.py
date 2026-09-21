"""Colour palette, spacing scale and font management."""
from __future__ import annotations

import pygame

Color = tuple[int, ...]

# --- palette ---------------------------------------------------------------
BG_TOP: Color = (7, 10, 24)
BG_BOTTOM: Color = (16, 10, 36)
PANEL_TOP: Color = (30, 38, 70)
PANEL_BOTTOM: Color = (15, 19, 40)
CARD_FILL: Color = (10, 14, 32, 150)
BORDER: Color = (84, 104, 170)

TEXT: Color = (234, 240, 255)
TEXT_DIM: Color = (144, 156, 196)
TEXT_FAINT: Color = (92, 104, 148)

CYAN: Color = (72, 222, 255)
MAGENTA: Color = (218, 96, 255)
GOLD: Color = (255, 206, 96)
GREEN: Color = (84, 236, 164)
RED: Color = (255, 94, 116)
ORANGE: Color = (255, 154, 84)
BLUE: Color = (104, 168, 255)

HUMAN_COLOR: Color = CYAN
AI_COLOR: Color = MAGENTA

ZONE_COLORS: dict[str, Color] = {
    "DANGER": RED,
    "SAFE": BLUE,
    "ADVANTAGE": GREEN,
}

# event-log colours by EventKind value
EVENT_COLORS: dict[str, Color] = {
    "system": TEXT_DIM,
    "roll": (200, 210, 240),
    "select": CYAN,
    "move": TEXT,
    "ladder": GREEN,
    "snake": RED,
    "shield": GOLD,
    "ai": MAGENTA,
    "win": GOLD,
}

# --- UI scale ----------------------------------------------------------------
DESIGN_W, DESIGN_H = 1440, 900


class _Scale:
    value = 1.0


def set_scale(value: float) -> None:
    _Scale.value = max(0.45, min(3.0, value))


def get_scale() -> float:
    return _Scale.value


def S(value: float) -> int:
    """Scale a design-space length (pixels at 1440x900) to the current UI scale."""
    return int(round(value * _Scale.value))


# --- fonts ---------------------------------------------------------------------
_FONT_CANDIDATES = ("segoeui", "sfprodisplay", "helveticaneue", "avenirnext", "avenir",
                    "inter", "roboto", "opensans", "dejavusans", "verdana", "arial")


class FontManager:
    """Loads fonts lazily with graceful fallbacks (never raises)."""

    def __init__(self) -> None:
        self._cache: dict[tuple[int, bool], pygame.font.Font] = {}
        self._family: str | None = None
        self._resolved = False

    def _resolve_family(self) -> str | None:
        if self._resolved:
            return self._family
        self._resolved = True
        for name in _FONT_CANDIDATES:
            try:
                if pygame.font.match_font(name):
                    self._family = name
                    break
            except Exception:
                continue
        return self._family

    def get(self, size: float, bold: bool = False) -> pygame.font.Font:
        """Font whose pixel size is ``size`` design px scaled to the window."""
        px = max(9, int(round(size * _Scale.value)))
        key = (px, bold)
        font = self._cache.get(key)
        if font is None:
            font = self._create(px, bold)
            self._cache[key] = font
        return font

    def _create(self, px: int, bold: bool) -> pygame.font.Font:
        family = self._resolve_family()
        try:
            if family:
                return pygame.font.SysFont(family, px, bold=bold)
        except Exception:
            pass
        try:
            return pygame.font.Font(None, int(px * 1.25))
        except Exception:
            pygame.font.init()
            return pygame.font.Font(None, int(px * 1.25))


fonts = FontManager()
