"""Reusable UI components: Button, Panel, Card, ProgressBar, DiceWidget, StatCard,
EventLog, HeatmapCell, DecisionScoreBar, StatusBadge, Tooltip, Modal, Toast, MiniChart."""
from __future__ import annotations

import math
import time
from typing import Callable, Sequence

import pygame

from . import draw, theme
from .animations import (SmoothValue, Tween, clamp01, ease_out_back, ease_out_bounce,
                         ease_out_cubic, pulse)
from .theme import Color, S, fonts


def fitted_font(text: str, max_width: int, size: float, bold: bool = False,
                min_size: float = 8) -> pygame.font.Font:
    """Largest font (<= ``size`` design px) whose rendering of ``text`` fits ``max_width``."""
    s = size
    while s > min_size:
        f = fonts.get(s, bold)
        if f.size(text)[0] <= max_width:
            return f
        s -= 1
    return fonts.get(min_size, bold)


def mouse_pos() -> tuple[int, int]:
    try:
        return pygame.mouse.get_pos()
    except Exception:
        return (-1, -1)


# ================================================================== Button
class Button:
    """Animated button with hover glow and press feedback."""

    STYLES = {
        "primary": ((58, 184, 255), (104, 82, 238), theme.CYAN),
        "secondary": ((36, 46, 86), (24, 30, 60), theme.BLUE),
        "danger": ((236, 80, 110), (150, 40, 90), theme.RED),
        "gold": ((255, 200, 90), (222, 128, 60), theme.GOLD),
        "success": ((70, 226, 160), (30, 150, 130), theme.GREEN),
    }

    def __init__(self, label: str, on_click: Callable[[], None] | None = None,
                 style: str = "primary", font_size: float = 16, toggle: bool = False) -> None:
        self.label = label
        self.on_click = on_click
        self.style = style
        self.font_size = font_size
        self.toggle = toggle
        self.active = False
        self.enabled = True
        self.visible = True
        self.rect = pygame.Rect(0, 0, 100, 40)
        self.hover = SmoothValue(0.0, 14)
        self.press = SmoothValue(0.0, 24)
        self._down = False

    def hit(self, pos: tuple[int, int]) -> bool:
        return self.visible and self.enabled and self.rect.collidepoint(pos)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Returns True when the button was clicked."""
        if not (self.visible and self.enabled):
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._down = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_down, self._down = self._down, False
            if was_down and self.rect.collidepoint(event.pos):
                if self.toggle:
                    self.active = not self.active
                if self.on_click:
                    self.on_click()
                return True
        return False

    def update(self, dt: float) -> None:
        over = self.hit(mouse_pos())
        self.hover.set(1.0 if over else 0.0)
        self.press.set(1.0 if (self._down and over) else 0.0)
        self.hover.update(dt)
        self.press.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return
        top, bottom, glow = self.STYLES.get(self.style, self.STYLES["primary"])
        h, pr = self.hover.value, self.press.value
        r = self.rect.inflate(-int(pr * S(4)), -int(pr * S(4)))
        radius = max(6, r.h // 3)
        if not self.enabled:
            top, bottom, glow = (48, 54, 84), (34, 38, 62), theme.TEXT_FAINT
        elif self.style == "secondary" and (self.active or h > 0.01):
            top = draw.lerp_color(top, (70, 90, 160), max(h * 0.6, 1.0 if self.active else 0.0))
        if self.enabled and (h > 0.02 or self.active):
            strength = max(h, 0.8 if self.active else 0.0)
            draw.draw_glow_rect(surface, r, glow, radius, S(12), int(40 + 120 * strength))
        draw.gradient_rrect(surface, r, draw.lighten(top, 0.10 * h), draw.lighten(bottom, 0.06 * h), radius)
        border = glow if self.enabled else theme.TEXT_FAINT
        draw.stroke_rrect(surface, r, draw.with_alpha(border, int(90 + 120 * max(h, 0.6 if self.active else 0.0))),
                          radius, 1)
        hl = pygame.Rect(r.x + radius // 2, r.y + 2, r.w - radius, max(1, r.h // 3))
        draw.fill_rrect(surface, hl, (255, 255, 255, 24), hl.h // 2)
        font = fitted_font(self.label, r.w - S(16), self.font_size, True)
        color = theme.TEXT if self.enabled else theme.TEXT_FAINT
        draw.draw_text(surface, self.label, font, color, r.center, "center", shadow=self.enabled)


# ================================================================== Panel
class Panel:
    """Glass panel with a title, accent underline and an appear animation."""

    def __init__(self, title: str = "", accent: Color = theme.CYAN, delay: float = 0.0) -> None:
        self.title = title
        self.accent = accent
        self.appear = Tween(0.0, 1.0, 0.6, ease_out_cubic, delay)

    def replay(self, delay: float = 0.0) -> None:
        self.appear.restart(delay=delay)

    def update(self, dt: float) -> None:
        self.appear.update(dt)

    def draw_background(self, surface: pygame.Surface, rect: pygame.Rect) -> pygame.Rect:
        """Draw the panel; returns the padded content rect."""
        off = int((1.0 - self.appear.value) * S(16))
        r = rect.move(0, off)
        radius = S(16)
        draw.draw_shadow(surface, r, radius, S(14), 100, S(5))
        surface.blit(draw.glass_panel_surface(r.w, r.h, radius, self.accent), r.topleft)
        pad = S(14)
        top = r.y + pad
        if self.title:
            font = fonts.get(12.5, True)
            bar = pygame.Rect(r.x + pad, r.y + pad + S(1), S(3), S(14))
            draw.fill_rrect(surface, bar, self.accent, 2)
            draw.draw_text(surface, self.title, font, draw.lighten(self.accent, 0.35),
                           (r.x + pad + S(10), r.y + pad - S(1)))
            line_y = r.y + pad + S(21)
            pygame.draw.line(surface, draw.with_alpha(self.accent, 70),
                             (r.x + pad, line_y), (r.right - pad, line_y))
            top = line_y + S(8)
        return pygame.Rect(r.x + pad, top, r.w - 2 * pad, max(0, r.bottom - pad - top))

    def draw_veil(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Fade-in: drawn AFTER the content so text fades together with the panel."""
        p = self.appear.value
        if p < 0.995:
            r = rect.move(0, int((1.0 - p) * S(16))).inflate(S(4), S(4))
            draw.fill_rrect(surface, r, (10, 12, 28, int((1.0 - p) * 235)), S(16))


class Card:
    """Inner rounded container."""

    @staticmethod
    def draw(surface: pygame.Surface, rect: pygame.Rect, accent: Color | None = None,
             fill: Color = theme.CARD_FILL, glow: float = 0.0, radius: int | None = None) -> None:
        radius = S(10) if radius is None else radius
        if glow > 0.01 and accent:
            draw.draw_glow_rect(surface, rect, accent, radius, S(10), int(130 * glow))
        draw.fill_rrect(surface, rect, fill, radius)
        border = draw.with_alpha(accent, int(70 + 130 * glow)) if accent else (90, 108, 170, 60)
        draw.stroke_rrect(surface, rect, border, radius, 1)


# ============================================================= ProgressBar
class ProgressBar:
    """Animated horizontal bar (value 0..1)."""

    def __init__(self, color: Color = theme.CYAN, speed: float = 5.0) -> None:
        self.color = color
        self.value = SmoothValue(0.0, speed)

    def set(self, target: float, snap: bool = False) -> None:
        self.value.set(clamp01(target), snap)

    def update(self, dt: float) -> None:
        self.value.update(dt)

    def draw(self, surface: pygame.Surface, rect: pygame.Rect, color: Color | None = None,
             glow: bool = True) -> None:
        color = color or self.color
        radius = max(2, rect.h // 2)
        draw.fill_rrect(surface, rect, (8, 11, 26, 220), radius)
        w = int(rect.w * clamp01(self.value.value))
        if w >= 3:
            fill = pygame.Rect(rect.x, rect.y, w, rect.h)
            draw.gradient_rrect(surface, fill, draw.lighten(color, 0.25), draw.darken(color, 0.25), radius)
            if glow and rect.h >= 4:
                draw.draw_glow(surface, (fill.right - 1, fill.centery), rect.h * 1.6, color, 130)
        draw.stroke_rrect(surface, rect, (110, 128, 190, 60), radius, 1)


class DecisionScoreBar:
    """Labelled score bar whose fill and number animate in after an optional delay."""

    def __init__(self, label: str, color: Color, decimals: int = 2, strong: bool = False) -> None:
        self.label = label
        self.color = color
        self.decimals = decimals
        self.strong = strong
        self.bar = ProgressBar(color, speed=4.5)
        self._pending: float | None = None
        self._delay = 0.0

    def reveal(self, value: float, delay: float = 0.0) -> None:
        self.bar.set(0.0, snap=True)
        self._pending, self._delay = value, delay

    def set_now(self, value: float) -> None:
        self._pending = None
        self.bar.set(value, snap=True)

    def update(self, dt: float) -> None:
        if self._pending is not None:
            self._delay -= dt
            if self._delay <= 0:
                self.bar.set(self._pending)
                self._pending = None
        self.bar.update(dt)

    def draw(self, surface: pygame.Surface, rect: pygame.Rect, dim: bool = False) -> None:
        font = fonts.get(12.5, self.strong)
        col = theme.TEXT_DIM if not self.strong else theme.TEXT
        if dim:
            col = theme.TEXT_FAINT
        label_w = int(rect.w * 0.40)
        draw.draw_text(surface, draw.ellipsize(font, self.label, label_w), font, col,
                       (rect.x, rect.centery), "midleft")
        val_w = S(44)
        bar_h = max(5, int(rect.h * (0.46 if self.strong else 0.34)))
        bar = pygame.Rect(rect.x + label_w, rect.centery - bar_h // 2,
                          rect.w - label_w - val_w - S(6), bar_h)
        self.bar.draw(surface, bar, draw.lerp_color(self.color, (90, 96, 130), 0.7) if dim else self.color)
        text = f"{self.bar.value.value:.{self.decimals}f}"
        vf = fonts.get(13.5 if self.strong else 12.5, True)
        draw.draw_text(surface, text, vf, theme.TEXT if not dim else theme.TEXT_FAINT,
                       (rect.right, rect.centery), "midright")


# ============================================================= StatusBadge
class StatusBadge:
    """Pill-shaped label with an optional pulsing dot."""

    @staticmethod
    def draw(surface: pygame.Surface, text: str, color: Color, pos: tuple[float, float],
             anchor: str = "topleft", t: float = 0.0, dot: bool = False, size: float = 11.5,
             filled: bool = True) -> pygame.Rect:
        font = fonts.get(size, True)
        tw, th = font.size(text)
        pad_x, pad_y = S(9), S(3)
        dot_w = S(12) if dot else 0
        rect = pygame.Rect(0, 0, tw + pad_x * 2 + dot_w, th + pad_y * 2)
        setattr(rect, anchor, (int(pos[0]), int(pos[1])))
        radius = rect.h // 2
        draw.fill_rrect(surface, rect, draw.with_alpha(color, 46 if filled else 18), radius)
        draw.stroke_rrect(surface, rect, draw.with_alpha(color, 170), radius, 1)
        x = rect.x + pad_x
        if dot:
            cy = rect.centery
            draw.draw_glow(surface, (x + S(3), cy), S(9), color, int(90 + 90 * pulse(t, 1.2)))
            pygame.draw.circle(surface, color, (x + S(3), cy), max(2, S(3)))
            x += dot_w
        draw.draw_text(surface, text, font, draw.lighten(color, 0.35), (x, rect.centery), "midleft")
        return rect


# ================================================================ StatCard
class StatCard:
    """Small label/value tile."""

    @staticmethod
    def draw(surface: pygame.Surface, rect: pygame.Rect, label: str, value: str,
             sub: str | None = None, color: Color = theme.TEXT, accent: Color | None = None) -> None:
        Card.draw(surface, rect, accent)
        pad = S(9)
        lf = fonts.get(10)
        draw.draw_text(surface, draw.ellipsize(lf, label.upper(), rect.w - 2 * pad), lf,
                       theme.TEXT_DIM, (rect.x + pad, rect.y + S(6)))
        avail = rect.w - 2 * pad - (fonts.get(11).size(sub)[0] + S(6) if sub else 0)
        vf = fitted_font(value, max(S(20), avail), 21, True, 11)
        draw.draw_text(surface, value, vf, color, (rect.x + pad, rect.bottom - S(6)), "bottomleft")
        if sub:
            sf = fonts.get(11)
            draw.draw_text(surface, sub, sf, theme.TEXT_DIM, (rect.right - pad, rect.bottom - S(8)),
                           "bottomright")


# =============================================================== DiceWidget
class DiceWidget:
    """A die that rolls, settles and can be hovered / selected."""

    def __init__(self, index: int, accent: Color = theme.CYAN) -> None:
        self.index = index
        self.accent = accent
        self.value = 1
        self.shown = 1
        self.rolling = False
        self.selectable = False
        self.valid = True
        self.chosen = False
        self.visible_value = True
        self.rect = pygame.Rect(0, 0, 80, 80)
        self.hover = SmoothValue(0.0, 14)
        self._elapsed = 0.0
        self._dur = 0.9
        self._delay = 0.0
        self._next_face = 0.0
        self._settle = Tween(1.0, 1.0, 0.4, ease_out_bounce)
        self.finished_flag = False
        self._rng_state = 1 + index * 7

    def set_accent(self, color: Color) -> None:
        self.accent = color

    def roll(self, final_value: int, duration: float = 0.9, delay: float = 0.0) -> None:
        self.value = final_value
        self.rolling = True
        self._elapsed = 0.0
        self._dur = duration
        self._delay = delay
        self._next_face = 0.0
        self.chosen = False
        self.finished_flag = False

    def show(self, value: int) -> None:
        """Display a value without animating."""
        self.value = self.shown = value
        self.rolling = False

    def contains(self, pos: tuple[int, int]) -> bool:
        return self.rect.collidepoint(pos)

    def consume_finished(self) -> bool:
        flag, self.finished_flag = self.finished_flag, False
        return flag

    def _random_face(self) -> int:
        self._rng_state = (self._rng_state * 1103515245 + 12345) & 0x7FFFFFFF
        return 1 + (self._rng_state >> 8) % 6

    def update(self, dt: float) -> None:
        hovering = self.selectable and self.valid and self.rect.collidepoint(mouse_pos())
        self.hover.set(1.0 if hovering else 0.0)
        self.hover.update(dt)
        self._settle.update(dt)
        if not self.rolling:
            return
        self._elapsed += dt
        active = self._elapsed - self._delay
        if active < 0:
            return
        p = clamp01(active / self._dur)
        if active >= self._dur:
            self.rolling = False
            self.shown = self.value
            self._settle = Tween(0.0, 1.0, 0.45, ease_out_bounce)
            self.finished_flag = True
            return
        self._next_face -= dt
        if self._next_face <= 0:
            self.shown = self._random_face()
            self._next_face = 0.045 + 0.13 * p * p

    def draw(self, surface: pygame.Surface, t: float) -> None:
        r = self.rect
        angle = 0.0
        ox = oy = 0
        if self.rolling and self._elapsed >= self._delay:
            p = clamp01((self._elapsed - self._delay) / self._dur)
            damp = 1.0 - p
            ox = int(math.sin(self._elapsed * 38) * S(7) * damp)
            oy = -int(abs(math.cos(self._elapsed * 21)) * S(14) * damp)
            angle = (1.0 - ease_out_cubic(p)) * 540.0
        else:
            oy = -int((1.0 - self._settle.value) * S(16)) if self._settle.progress < 1 else 0
        lift = self.hover.value * S(4)
        body = r.move(ox, oy - int(lift))
        pulse_v = pulse(t, 1.4) if (self.selectable and self.valid) else 0.0
        strength = max(self.hover.value, 0.55 * pulse_v)

        size = body.w
        die = pygame.Surface((size, size), pygame.SRCALPHA)
        face = pygame.Rect(0, 0, size, size)
        top = draw.lerp_color((52, 64, 118), draw.darken(self.accent, 0.35), 0.35 + 0.25 * strength)
        bottom = (18, 22, 50)
        if not self.valid:
            top, bottom = (36, 40, 64), (20, 22, 40)
        draw.gradient_rrect(die, face, top, bottom, size // 5)
        rim = self.accent if self.valid else theme.TEXT_FAINT
        if self.chosen:
            rim = theme.GOLD
        draw.stroke_rrect(die, face, draw.with_alpha(rim, int(150 + 100 * strength)), size // 5, max(2, S(2)))
        shine = pygame.Rect(size // 8, size // 14, size * 3 // 4, size // 6)
        draw.fill_rrect(die, shine, (255, 255, 255, 26), shine.h // 2)
        pip_col = draw.lighten(self.accent, 0.55) if self.valid else theme.TEXT_FAINT
        if self.chosen:
            pip_col = (255, 236, 170)
        draw.draw_pips(die, face, self.shown, pip_col, glow=self.valid)
        if angle:
            die = pygame.transform.rotate(die, angle)

        draw_rect = die.get_rect(center=body.center)
        if self.valid and (strength > 0.02 or self.chosen):
            col = theme.GOLD if self.chosen else self.accent
            draw.draw_glow_rect(surface, body, col, size // 5, S(14),
                                int(60 + 140 * max(strength, 1.0 if self.chosen else 0)))
        draw.draw_shadow(surface, body, size // 5, S(10), 90, S(6))
        surface.blit(die, draw_rect.topleft)
        if not self.valid:
            pygame.draw.line(surface, draw.with_alpha(theme.RED, 200)[:3],
                             (body.x + size // 6, body.y + size // 6),
                             (body.right - size // 6, body.bottom - size // 6), max(2, S(3)))
        if self.chosen:
            badge = pygame.Rect(0, 0, S(24), S(24))
            badge.center = (body.right - S(2), body.y + S(2))
            pygame.draw.circle(surface, theme.GOLD, badge.center, badge.w // 2)
            draw.draw_check(surface, badge.centerx, badge.centery, S(8), (40, 30, 10), max(2, S(2)))


# ================================================================ EventLog
class EventLog:
    """Scrolling, colour-coded log with auto-follow and a scrollbar."""

    def __init__(self) -> None:
        self.scroll = 0.0
        self.follow = True
        self._lines: list[tuple[Color, str, str, bool, float]] = []
        self._key: tuple | None = None
        self._max_scroll = 0.0
        self._rect = pygame.Rect(0, 0, 10, 10)
        self._dragging = False

    def _rebuild(self, events: Sequence, width: int, font: pygame.font.Font) -> None:
        self._lines = []
        ts_w = font.size("00:00:00   ")[0]
        for ev in events:
            color = theme.EVENT_COLORS.get(ev.kind.value, theme.TEXT)
            stamp = time.strftime("%H:%M:%S", time.localtime(ev.timestamp))
            wrapped = draw.wrap_text(font, ev.text, max(S(40), width - ts_w - S(10)))
            for i, line in enumerate(wrapped):
                self._lines.append((color, stamp if i == 0 else "", line, i == 0, ev.timestamp))

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEWHEEL and self._rect.collidepoint(mouse_pos()):
            self.scroll = max(0.0, min(self._max_scroll, self.scroll - event.y * S(36)))
            self.follow = self.scroll >= self._max_scroll - 2

    def draw(self, surface: pygame.Surface, rect: pygame.Rect, events: Sequence, now: float,
             dt: float = 0.016) -> None:
        self._rect = rect
        font = fonts.get(12)
        lh = font.get_linesize() + S(3)
        key = (len(events), rect.w, theme.get_scale())
        if key != self._key:
            self._rebuild(events, rect.w, font)
            self._key = key
        total = len(self._lines) * lh
        self._max_scroll = max(0.0, total - rect.h + S(4))
        if self.follow:
            self.scroll += (self._max_scroll - self.scroll) * min(1.0, dt * 12)
            if abs(self._max_scroll - self.scroll) < 0.5:
                self.scroll = self._max_scroll
        self.scroll = max(0.0, min(self._max_scroll, self.scroll))

        old_clip = surface.get_clip()
        surface.set_clip(rect.clip(old_clip))
        ts_w = font.size("00:00:00   ")[0]
        first = int(self.scroll // lh)
        y = rect.y - int(self.scroll - first * lh)
        for i in range(first, len(self._lines)):
            if y > rect.bottom:
                break
            color, stamp, text, is_first, born = self._lines[i]
            age = now - born
            fresh = clamp01(1.0 - age / 2.5)
            if is_first:
                bar = pygame.Rect(rect.x, y + S(1), S(2), lh - S(3))
                draw.fill_rrect(surface, bar, draw.with_alpha(color, 90 + int(150 * fresh)), 1)
                if fresh > 0:
                    draw.fill_rrect(surface, pygame.Rect(rect.x, y, rect.w, lh - S(1)),
                                    draw.with_alpha(color, int(24 * fresh)), 3)
            draw.draw_text(surface, stamp, font, theme.TEXT_FAINT, (rect.x + S(7), y))
            draw.draw_text(surface, text, font, draw.lerp_color(color, (255, 255, 255), 0.25 * fresh),
                           (rect.x + ts_w + S(4), y))
            y += lh
        surface.set_clip(old_clip)

        if self._max_scroll > 0:
            track = pygame.Rect(rect.right - S(4), rect.y, S(3), rect.h)
            draw.fill_rrect(surface, track, (255, 255, 255, 18), 2)
            thumb_h = max(S(18), int(rect.h * rect.h / max(rect.h, total)))
            ty = rect.y + int((rect.h - thumb_h) * (self.scroll / self._max_scroll))
            draw.fill_rrect(surface, pygame.Rect(track.x, ty, track.w, thumb_h),
                            draw.with_alpha(theme.CYAN, 150), 2)


# ============================================================== HeatmapCell
class HeatmapCell:
    """One cell of the K-Means risk heatmap."""

    def __init__(self, cell: int) -> None:
        self.cell = cell
        self.rect = pygame.Rect(0, 0, 10, 10)
        self.hover = SmoothValue(0.0, 16)

    def update(self, dt: float) -> None:
        self.hover.set(1.0 if self.rect.collidepoint(mouse_pos()) else 0.0)
        self.hover.update(dt)

    def draw(self, surface: pygame.Surface, zone_color: Color, intensity: float,
             marker: str | None = None) -> None:
        r = self.rect.inflate(-S(3), -S(3))
        radius = max(3, r.w // 7)
        h = self.hover.value
        base = (16, 20, 44)
        col = draw.lerp_color(base, zone_color, 0.28 + 0.42 * clamp01(intensity) + 0.2 * h)
        if h > 0.02:
            draw.draw_glow_rect(surface, r, zone_color, radius, S(9), int(150 * h))
        draw.gradient_rrect(surface, r, draw.lighten(col, 0.10), draw.darken(col, 0.18), radius)
        draw.stroke_rrect(surface, r, draw.with_alpha(zone_color, int(90 + 140 * h)), radius, 1)
        f = fonts.get(max(9, r.h / theme.get_scale() * 0.30), True)
        draw.draw_text(surface, str(self.cell), f, theme.TEXT, r.center, "center", shadow=True)
        if marker == "snake":
            draw.draw_chevron(surface, r.right - S(9), r.bottom - S(8), S(4), theme.RED, up=False, width=2)
        elif marker == "ladder":
            draw.draw_chevron(surface, r.right - S(9), r.bottom - S(8), S(4), theme.GREEN, up=True, width=2)


# ================================================================= Tooltip
class Tooltip:
    """Small floating info box."""

    @staticmethod
    def draw(surface: pygame.Surface, lines: Sequence[str | tuple[str, Color]],
             pos: tuple[int, int], title: str | None = None, accent: Color = theme.CYAN) -> None:
        if not lines and not title:
            return
        font, tfont = fonts.get(12), fonts.get(13, True)
        rows: list[tuple[str, Color, pygame.font.Font]] = []
        if title:
            rows.append((title, accent, tfont))
        for ln in lines:
            text, col = (ln, theme.TEXT) if isinstance(ln, str) else ln
            rows.append((text, col, font))
        pad = S(10)
        w = max(f.size(t)[0] for t, _, f in rows) + 2 * pad
        lh = font.get_linesize() + S(2)
        h = len(rows) * lh + 2 * pad - S(2)
        sw, sh = surface.get_size()
        x = min(max(S(4), pos[0] + S(16)), max(S(4), sw - w - S(4)))
        y = min(max(S(4), pos[1] + S(18)), max(S(4), sh - h - S(4)))
        rect = pygame.Rect(x, y, w, h)
        draw.draw_shadow(surface, rect, S(10), S(10), 130, S(4))
        draw.fill_rrect(surface, rect, (14, 18, 40, 245), S(10))
        draw.stroke_rrect(surface, rect, draw.with_alpha(accent, 180), S(10), 1)
        yy = rect.y + pad - S(1)
        for text, col, f in rows:
            draw.draw_text(surface, text, f, col, (rect.x + pad, yy))
            yy += lh


# ================================================================== Modal
class Modal:
    """Centered dialog with a dimmed backdrop and buttons."""

    def __init__(self, title: str, lines: Sequence[str] = (), buttons: Sequence[Button] = (),
                 accent: Color = theme.CYAN) -> None:
        self.title = title
        self.lines = list(lines)
        self.buttons = list(buttons)
        self.accent = accent
        self.visible = False
        self.appear = Tween(0.0, 1.0, 0.35, ease_out_back)

    def open(self) -> None:
        self.visible = True
        self.appear.restart()

    def close(self) -> None:
        self.visible = False

    def set_content(self, title: str, lines: Sequence[str]) -> None:
        self.title = title
        self.lines = list(lines)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Consumes every event while visible. Returns True if handled."""
        if not self.visible:
            return False
        for b in self.buttons:
            b.handle_event(event)
        return event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION,
                              pygame.MOUSEWHEEL)

    def update(self, dt: float) -> None:
        if not self.visible:
            return
        self.appear.update(dt)
        for b in self.buttons:
            b.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return
        sw, sh = surface.get_size()
        p = clamp01(self.appear.progress)
        veil = pygame.Surface((sw, sh), pygame.SRCALPHA)
        veil.fill((4, 6, 16, int(185 * p)))
        surface.blit(veil, (0, 0))
        width = min(S(540), int(sw * 0.92))
        body_font, title_font = fonts.get(14), fonts.get(20, True)
        wrapped: list[str] = []
        for ln in self.lines:
            wrapped += draw.wrap_text(body_font, ln, width - S(56))
        lh = body_font.get_linesize() + S(4)
        height = S(24) + S(30) + S(14) + len(wrapped) * lh + S(20) + S(46) + S(22)
        scale = 0.92 + 0.08 * min(1.0, self.appear.value)
        rect = pygame.Rect(0, 0, int(width * scale), int(height * scale))
        rect.center = (sw // 2, sh // 2)
        draw.draw_glow_rect(surface, rect, self.accent, S(18), S(22), int(90 * p))
        surface.blit(draw.glass_panel_surface(rect.w, rect.h, S(18), self.accent, 245), rect.topleft)
        draw.draw_text(surface, self.title, title_font, theme.TEXT, (rect.centerx, rect.y + S(24)),
                       "midtop", shadow=True)
        y = rect.y + S(24) + S(30) + S(14)
        for ln in wrapped:
            draw.draw_text(surface, ln, body_font, theme.TEXT_DIM, (rect.centerx, y), "midtop")
            y += lh
        if self.buttons:
            gap = S(12)
            bw = min(S(170), (rect.w - S(40) - gap * (len(self.buttons) - 1)) // len(self.buttons))
            total = bw * len(self.buttons) + gap * (len(self.buttons) - 1)
            x = rect.centerx - total // 2
            for b in self.buttons:
                b.rect = pygame.Rect(x, rect.bottom - S(22) - S(46), bw, S(46))
                b.draw(surface)
                x += bw + gap


# ================================================================== Toast
class ToastManager:
    """Short-lived notifications at the top of the screen."""

    def __init__(self) -> None:
        self._toasts: list[dict] = []

    def push(self, text: str, color: Color = theme.CYAN, duration: float = 2.6) -> None:
        self._toasts.append({"text": text, "color": color, "life": duration, "max": duration})
        self._toasts = self._toasts[-4:]

    def update(self, dt: float) -> None:
        for t in self._toasts:
            t["life"] -= dt
        self._toasts = [t for t in self._toasts if t["life"] > 0]

    def draw(self, surface: pygame.Surface, top: int) -> None:
        font = fonts.get(14, True)
        y = top
        for t in self._toasts:
            age = t["max"] - t["life"]
            slide = ease_out_cubic(clamp01(age / 0.3))
            fade = clamp01(t["life"] / 0.4)
            text_w = font.size(t["text"])[0]
            rect = pygame.Rect(0, 0, text_w + S(44), S(38))
            rect.midtop = (surface.get_width() // 2, int(y - (1 - slide) * S(24)))
            tmp = pygame.Surface((rect.w + S(40), rect.h + S(40)), pygame.SRCALPHA)
            inner = pygame.Rect(S(20), S(20), rect.w, rect.h)
            draw.draw_glow_rect(tmp, inner, t["color"], rect.h // 2, S(14), 90)
            draw.fill_rrect(tmp, inner, (12, 16, 36, 240), rect.h // 2)
            draw.stroke_rrect(tmp, inner, draw.with_alpha(t["color"], 200), rect.h // 2, 1)
            pygame.draw.circle(tmp, t["color"], (inner.x + S(16), inner.centery), S(4))
            draw.draw_text(tmp, t["text"], font, theme.TEXT, (inner.x + S(28), inner.centery), "midleft")
            tmp.set_alpha(int(255 * fade * slide))
            surface.blit(tmp, (rect.x - S(20), rect.y - S(20)))
            y += rect.h + S(8)


# ================================================================ MiniChart
class MiniChart:
    """Tiny animated line chart (used for the progress-over-turns graph)."""

    def __init__(self) -> None:
        self.reveal = SmoothValue(0.0, 4.0)

    def update(self, dt: float) -> None:
        self.reveal.update(dt)

    def draw(self, surface: pygame.Surface, rect: pygame.Rect,
             series: Sequence[tuple[Color, Sequence[float]]], y_max: float = 100.0,
             title: str | None = None) -> None:
        Card.draw(surface, rect)
        pad = S(8)
        top_pad = S(20) if title else pad
        if title:
            draw.draw_text(surface, title.upper(), fonts.get(11), theme.TEXT_DIM, (rect.x + pad, rect.y + S(5)))
        plot = pygame.Rect(rect.x + pad + S(22), rect.y + top_pad, rect.w - 2 * pad - S(22),
                           rect.h - top_pad - pad)
        if plot.w < 10 or plot.h < 10:
            return
        small = fonts.get(10)
        for frac in (0.0, 0.5, 1.0):
            y = plot.bottom - int(plot.h * frac)
            pygame.draw.line(surface, (60, 74, 120), (plot.x, y), (plot.right, y))
            draw.draw_text(surface, str(int(y_max * frac)), small, theme.TEXT_FAINT, (plot.x - S(4), y), "midright")
        n = max((len(v) for _, v in series), default=0)
        self.reveal.set(max(0, n - 1))
        shown = self.reveal.value
        for color, values in series:
            if len(values) < 2:
                continue
            pts: list[tuple[float, float]] = []
            for i, v in enumerate(values):
                if i > shown:
                    break
                px = plot.x + plot.w * (i / max(1, n - 1))
                pts.append((px, plot.bottom - plot.h * clamp01(v / y_max)))
            nxt = int(shown) + 1
            if 0 < nxt < len(values) and shown < len(values) - 1:
                f = shown - int(shown)
                i = int(shown)
                px = plot.x + plot.w * ((i + f) / max(1, n - 1))
                v = values[i] + (values[nxt] - values[i]) * f
                pts.append((px, plot.bottom - plot.h * clamp01(v / y_max)))
            if len(pts) >= 2:
                pygame.draw.lines(surface, color, False, [(int(x), int(y)) for x, y in pts], max(2, S(2)))
            if pts:
                draw.draw_glow(surface, pts[-1], S(9), color, 150)
                pygame.draw.circle(surface, color, (int(pts[-1][0]), int(pts[-1][1])), max(2, S(3)))
