"""Low-level drawing helpers: text, gradients, glows, glass panels and vector icons.

Expensive surfaces (gradients, glows, glass panels, shadows, text) are cached so
the per-frame cost stays low enough for 60 FPS.
"""
from __future__ import annotations

import math

import pygame

from . import theme
from .theme import Color

Point = tuple[float, float]


# ------------------------------------------------------------------ colours
def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_color(c1: Color, c2: Color, t: float) -> Color:
    t = max(0.0, min(1.0, t))
    n = min(len(c1), len(c2))
    return tuple(int(round(lerp(c1[i], c2[i], t))) for i in range(n))


def with_alpha(color: Color, alpha: int) -> Color:
    return (color[0], color[1], color[2], max(0, min(255, int(alpha))))


def lighten(color: Color, t: float) -> Color:
    return lerp_color(color[:3], (255, 255, 255), t)


def darken(color: Color, t: float) -> Color:
    return lerp_color(color[:3], (0, 0, 0), t)


# --------------------------------------------------------------------- text
_text_cache: dict[tuple, pygame.Surface] = {}


def render_text(font: pygame.font.Font, text: str, color: Color) -> pygame.Surface:
    key = (id(font), text, tuple(color))
    surf = _text_cache.get(key)
    if surf is None:
        if len(_text_cache) > 4000:
            _text_cache.clear()
        surf = font.render(text, True, tuple(color[:3]))
        if len(color) == 4 and color[3] < 255:
            surf = surf.copy()
            surf.set_alpha(color[3])
        _text_cache[key] = surf
    return surf


def draw_text(surface: pygame.Surface, text: str, font: pygame.font.Font, color: Color,
              pos: Point, anchor: str = "topleft", shadow: bool = False) -> pygame.Rect:
    """Draw text anchored at ``pos``; returns the covered rect."""
    surf = render_text(font, text, color)
    rect = surf.get_rect()
    setattr(rect, anchor, (int(pos[0]), int(pos[1])))
    if shadow:
        sh = render_text(font, text, (0, 0, 0, 150))
        surface.blit(sh, (rect.x + max(1, theme.S(1)), rect.y + max(1, theme.S(2))))
    surface.blit(surf, rect)
    return rect


def ellipsize(font: pygame.font.Font, text: str, max_width: int) -> str:
    """Shorten text with '...' so it fits ``max_width`` pixels."""
    if max_width <= 0:
        return ""
    if font.size(text)[0] <= max_width:
        return text
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if font.size(text[:mid] + "...")[0] <= max_width:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo].rstrip() + "..." if lo > 0 else "..."


_wrap_cache: dict[tuple, list[str]] = {}


def wrap_text(font: pygame.font.Font, text: str, max_width: int) -> list[str]:
    """Greedy word wrap (long words are hard-broken). Results are cached."""
    key = (id(font), text, max_width)
    cached = _wrap_cache.get(key)
    if cached is not None:
        return cached
    if len(_wrap_cache) > 1500:
        _wrap_cache.clear()
    result = _wrap_uncached(font, text, max_width)
    _wrap_cache[key] = result
    return result


def _wrap_uncached(font: pygame.font.Font, text: str, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        current = ""
        for word in words:
            candidate = word if not current else current + " " + word
            if font.size(candidate)[0] <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
            while font.size(word)[0] > max_width and len(word) > 1:
                cut = len(word)
                while cut > 1 and font.size(word[:cut])[0] > max_width:
                    cut -= 1
                lines.append(word[:cut])
                word = word[cut:]
            current = word
        lines.append(current)
    return lines


# ------------------------------------------------------- cached surfaces
_gradient_cache: dict[tuple, pygame.Surface] = {}
_mask_cache: dict[tuple, pygame.Surface] = {}
_glow_cache: dict[tuple, pygame.Surface] = {}
_panel_cache: dict[tuple, pygame.Surface] = {}
_shadow_cache: dict[tuple, pygame.Surface] = {}


def _trim(cache: dict, limit: int = 160) -> None:
    if len(cache) > limit:
        cache.clear()


def vertical_gradient(w: int, h: int, top: Color, bottom: Color) -> pygame.Surface:
    w, h = max(1, w), max(1, h)
    key = (w, h, tuple(top), tuple(bottom))
    surf = _gradient_cache.get(key)
    if surf is None:
        _trim(_gradient_cache, 60)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        top4 = tuple(top) + (255,) * (4 - len(top))
        bot4 = tuple(bottom) + (255,) * (4 - len(bottom))
        for y in range(h):
            t = y / max(1, h - 1)
            pygame.draw.line(surf, lerp_color(top4, bot4, t), (0, y), (w, y))
        _gradient_cache[key] = surf
    return surf


def rounded_mask(w: int, h: int, radius: int) -> pygame.Surface:
    key = (w, h, radius)
    mask = _mask_cache.get(key)
    if mask is None:
        _trim(_mask_cache)
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), pygame.Rect(0, 0, w, h),
                         border_radius=_clamp_radius(radius, w, h))
        _mask_cache[key] = mask
    return mask


def _clamp_radius(radius: int, w: int, h: int) -> int:
    return max(0, min(int(radius), w // 2, h // 2))


def glow_sprite(radius: int, color: Color, alpha: int = 160) -> pygame.Surface:
    """Soft radial glow (cached)."""
    radius = int(radius)
    step_q = 2 if radius < 60 else 8
    radius = max(2, int(round(radius / step_q)) * step_q)
    alpha = max(0, min(255, int(round(alpha / 12.0)) * 12))
    key = (radius, tuple(color[:3]), alpha)
    surf = _glow_cache.get(key)
    if surf is None:
        _trim(_glow_cache, 300)
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        step = 1 if radius < 40 else 2
        for r in range(radius, 0, -step):
            t = 1.0 - r / radius
            a = int(alpha * (t * t))
            pygame.draw.circle(surf, (color[0], color[1], color[2], a), (radius, radius), r)
        _glow_cache[key] = surf
    return surf


def draw_glow(surface: pygame.Surface, center: Point, radius: float, color: Color,
              alpha: int = 160) -> None:
    if alpha < 6 or radius < 2:
        return
    sprite = glow_sprite(int(radius), color, alpha)
    surface.blit(sprite, (int(center[0] - sprite.get_width() / 2),
                          int(center[1] - sprite.get_height() / 2)))


def glow_rect_surface(w: int, h: int, radius: int, color: Color, spread: int,
                      alpha: int) -> pygame.Surface:
    key = (w, h, radius, tuple(color[:3]), spread, alpha)
    surf = _glow_cache.get(key)
    if surf is None:
        _trim(_glow_cache, 300)
        surf = pygame.Surface((w + spread * 2, h + spread * 2), pygame.SRCALPHA)
        for i in range(spread, 0, -1):
            a = int(alpha * (1 - i / spread) ** 2)
            rect = pygame.Rect(spread - i, spread - i, w + 2 * i, h + 2 * i)
            pygame.draw.rect(surf, (color[0], color[1], color[2], a), rect, width=2,
                             border_radius=_clamp_radius(radius + i, rect.w, rect.h))
        _glow_cache[key] = surf
    return surf


def draw_glow_rect(surface: pygame.Surface, rect: pygame.Rect, color: Color, radius: int = 12,
                   spread: int = 10, alpha: int = 120) -> None:
    spread = max(2, spread)
    alpha = max(0, min(255, int(round(alpha / 16.0)) * 16))
    if alpha <= 0:
        return
    sprite = glow_rect_surface(rect.w, rect.h, radius, color, spread, alpha)
    surface.blit(sprite, (rect.x - spread, rect.y - spread))


def shadow_surface(w: int, h: int, radius: int, spread: int, alpha: int) -> pygame.Surface:
    key = (w, h, radius, spread, alpha)
    surf = _shadow_cache.get(key)
    if surf is None:
        _trim(_shadow_cache, 80)
        surf = pygame.Surface((w + spread * 2, h + spread * 2), pygame.SRCALPHA)
        for i in range(spread, -1, -1):
            a = int(alpha * (1 - i / (spread + 1)) ** 2)
            rect = pygame.Rect(spread - i, spread - i, w + 2 * i, h + 2 * i)
            pygame.draw.rect(surf, (0, 0, 0, a), rect,
                             border_radius=_clamp_radius(radius + i, rect.w, rect.h))
        _shadow_cache[key] = surf
    return surf


def draw_shadow(surface: pygame.Surface, rect: pygame.Rect, radius: int = 16,
                spread: int = 16, alpha: int = 110, offset: int = 6) -> None:
    sprite = shadow_surface(rect.w, rect.h, radius, spread, alpha)
    surface.blit(sprite, (rect.x - spread, rect.y - spread + offset))


def glass_panel_surface(w: int, h: int, radius: int, accent: Color, alpha: int = 225) -> pygame.Surface:
    """Rounded, gradient 'glass' panel with a glowing hairline border (cached)."""
    key = (w, h, radius, tuple(accent[:3]), alpha)
    surf = _panel_cache.get(key)
    if surf is None:
        _trim(_panel_cache, 120)
        surf = vertical_gradient(w, h, with_alpha(theme.PANEL_TOP, alpha),
                                 with_alpha(theme.PANEL_BOTTOM, alpha)).copy()
        r = _clamp_radius(radius, w, h)
        surf.blit(rounded_mask(w, h, r), (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        pygame.draw.rect(surf, with_alpha(accent, 120), pygame.Rect(0, 0, w, h), width=1,
                         border_radius=r)
        pygame.draw.line(surf, (255, 255, 255, 34), (r, 1), (max(r, w - r), 1))
        _panel_cache[key] = surf
    return surf


def fill_rrect(surface: pygame.Surface, rect: pygame.Rect, color: Color, radius: int = 8) -> None:
    """Filled rounded rect that honours alpha in ``color``."""
    if rect.w <= 0 or rect.h <= 0:
        return
    r = _clamp_radius(radius, rect.w, rect.h)
    if len(color) == 4 and color[3] < 255:
        tmp = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(tmp, color, tmp.get_rect(), border_radius=r)
        surface.blit(tmp, rect.topleft)
    else:
        pygame.draw.rect(surface, tuple(color[:3]), rect, border_radius=r)


def stroke_rrect(surface: pygame.Surface, rect: pygame.Rect, color: Color, radius: int = 8,
                 width: int = 1) -> None:
    if rect.w <= 0 or rect.h <= 0:
        return
    r = _clamp_radius(radius, rect.w, rect.h)
    if len(color) == 4 and color[3] < 255:
        tmp = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(tmp, color, tmp.get_rect(), width=width, border_radius=r)
        surface.blit(tmp, rect.topleft)
    else:
        pygame.draw.rect(surface, tuple(color[:3]), rect, width=width, border_radius=r)


def gradient_rrect(surface: pygame.Surface, rect: pygame.Rect, top: Color, bottom: Color,
                   radius: int = 8) -> None:
    if rect.w <= 0 or rect.h <= 0:
        return
    grad = vertical_gradient(rect.w, rect.h, top, bottom).copy()
    grad.blit(rounded_mask(rect.w, rect.h, radius), (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surface.blit(grad, rect.topleft)


# ------------------------------------------------------------------- shapes
def draw_polyline_thick(surface: pygame.Surface, color: Color, points: list[Point],
                        width: float) -> None:
    """Thick polyline with round joints (good for ladders / routes)."""
    if len(points) < 2:
        return
    w = max(1, int(width))
    pygame.draw.lines(surface, color, False, [(int(x), int(y)) for x, y in points], w)
    if w > 2:
        for x, y in points:
            pygame.draw.circle(surface, color, (int(x), int(y)), w // 2)


def dashed_line(surface: pygame.Surface, color: Color, a: Point, b: Point, dash: float,
                gap: float, offset: float = 0.0, width: int = 2) -> None:
    """Dashed line; ``offset`` animates the dashes."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    if length < 1:
        return
    ux, uy = dx / length, dy / length
    period = dash + gap
    pos = -(offset % period)
    while pos < length:
        s, e = max(0.0, pos), min(length, pos + dash)
        if e > s:
            pygame.draw.line(surface, color, (a[0] + ux * s, a[1] + uy * s),
                             (a[0] + ux * e, a[1] + uy * e), width)
        pos += period


# -------------------------------------------------------------------- icons
def draw_shield(surface: pygame.Surface, cx: float, cy: float, size: float, color: Color,
                filled: bool = True, glow: float = 0.0) -> None:
    """Vector shield icon. ``size`` is the half-height."""
    s = size
    pts = [(-0.80, -0.78), (0.0, -1.02), (0.80, -0.78), (0.80, 0.05), (0.50, 0.62),
           (0.0, 1.05), (-0.50, 0.62), (-0.80, 0.05)]
    poly = [(cx + x * s, cy + y * s) for x, y in pts]
    if glow > 0:
        draw_glow(surface, (cx, cy), s * 2.2, color, int(120 * glow))
    if filled:
        pygame.draw.polygon(surface, darken(color, 0.35), poly)
        inner = [(cx + x * s * 0.82, cy + y * s * 0.82) for x, y in pts]
        pygame.draw.polygon(surface, color, inner)
        hi = [(cx - 0.62 * s, cy - 0.60 * s), (cx, cy - 0.82 * s), (cx, cy + 0.72 * s),
              (cx - 0.38 * s, cy + 0.42 * s), (cx - 0.62 * s, cy + 0.02 * s)]
        pygame.draw.polygon(surface, lighten(color, 0.35), hi)
        pygame.draw.polygon(surface, lighten(color, 0.55), poly, max(1, int(s * 0.10)))
    else:
        dim = lerp_color(color, (20, 24, 44), 0.62)
        pygame.draw.polygon(surface, dim, poly, max(1, int(s * 0.14)))


def draw_check(surface: pygame.Surface, cx: float, cy: float, size: float, color: Color,
               width: int = 3) -> None:
    pts = [(cx - size * 0.55, cy + size * 0.02), (cx - size * 0.12, cy + size * 0.48),
           (cx + size * 0.62, cy - size * 0.42)]
    pygame.draw.lines(surface, color, False, [(int(x), int(y)) for x, y in pts], width)


def draw_star(surface: pygame.Surface, cx: float, cy: float, r: float, color: Color,
              rotation: float = 0.0) -> None:
    pts = []
    for i in range(10):
        ang = rotation - math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.45
        pts.append((cx + math.cos(ang) * rad, cy + math.sin(ang) * rad))
    pygame.draw.polygon(surface, color, pts)


def draw_chevron(surface: pygame.Surface, cx: float, cy: float, size: float, color: Color,
                 up: bool = True, width: int = 2) -> None:
    d = -1 if up else 1
    pts = [(cx - size, cy - d * size * 0.5), (cx, cy + d * size * 0.5), (cx + size, cy - d * size * 0.5)]
    pygame.draw.lines(surface, color, False, [(int(x), int(y)) for x, y in pts], width)


_PIPS = {
    1: [(0.5, 0.5)],
    2: [(0.28, 0.28), (0.72, 0.72)],
    3: [(0.26, 0.26), (0.5, 0.5), (0.74, 0.74)],
    4: [(0.28, 0.28), (0.72, 0.28), (0.28, 0.72), (0.72, 0.72)],
    5: [(0.28, 0.28), (0.72, 0.28), (0.5, 0.5), (0.28, 0.72), (0.72, 0.72)],
    6: [(0.29, 0.25), (0.71, 0.25), (0.29, 0.5), (0.71, 0.5), (0.29, 0.75), (0.71, 0.75)],
}


def draw_pips(surface: pygame.Surface, rect: pygame.Rect, value: int, color: Color,
              glow: bool = True) -> None:
    radius = max(2, int(rect.w * 0.085))
    for px, py in _PIPS.get(max(1, min(6, value)), _PIPS[1]):
        c = (rect.x + px * rect.w, rect.y + py * rect.h)
        if glow:
            draw_glow(surface, c, radius * 3.0, color, 110)
        pygame.draw.circle(surface, color, (int(c[0]), int(c[1])), radius)
        pygame.draw.circle(surface, lighten(color, 0.6),
                           (int(c[0] - radius * 0.25), int(c[1] - radius * 0.25)), max(1, radius // 2))


def draw_pawn(surface: pygame.Surface, x: float, y: float, r: float, color: Color,
              glow_alpha: int = 150, lift: float = 0.0) -> None:
    """Game piece. (x, y) is the point on the board it stands on; ``r`` ~ head radius."""
    shadow = pygame.Rect(0, 0, int(r * 2.6), int(r * 0.9))
    shadow.center = (int(x), int(y + r * 0.35))
    fill_rrect(surface, shadow, (0, 0, 0, 90), shadow.h // 2)
    base_y = y - lift
    draw_glow(surface, (x, base_y - r * 0.9), r * 3.4, color, glow_alpha)
    dark, light = darken(color, 0.45), lighten(color, 0.45)
    body = [(x - r * 1.05, base_y + r * 0.1), (x - r * 0.45, base_y - r * 1.15),
            (x + r * 0.45, base_y - r * 1.15), (x + r * 1.05, base_y + r * 0.1)]
    pygame.draw.polygon(surface, dark, body)
    inner = [(x - r * 0.9, base_y + r * 0.02), (x - r * 0.38, base_y - r * 1.08),
             (x + r * 0.38, base_y - r * 1.08), (x + r * 0.9, base_y + r * 0.02)]
    pygame.draw.polygon(surface, color, inner)
    pygame.draw.ellipse(surface, dark, pygame.Rect(int(x - r * 1.15), int(base_y - r * 0.25),
                                                    int(r * 2.3), int(r * 0.7)))
    pygame.draw.ellipse(surface, color, pygame.Rect(int(x - r * 1.0), int(base_y - r * 0.3),
                                                     int(r * 2.0), int(r * 0.55)))
    head = (int(x), int(base_y - r * 1.55))
    pygame.draw.circle(surface, dark, head, int(r * 0.78))
    pygame.draw.circle(surface, color, head, int(r * 0.68))
    pygame.draw.circle(surface, light, (int(x - r * 0.22), int(base_y - r * 1.78)), max(1, int(r * 0.24)))
