"""
Reusable UI Widgets for AI-Powered Snake & Ladder.
Includes Button, Card, DiceWidget, ShieldWidget, DecisionScoreBar, EventLogWidget, StatCard, and Modal.
"""

import pygame
import math
from typing import Tuple, Optional, Callable, List, Dict, Any
from .theme import Theme
from game.dice import DualDice


class Button:
    """
    Interactive button with hover animation, click effects, and customizable styling.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        callback: Optional[Callable[[], None]] = None,
        bg_color: Tuple[int, int, int] = Theme.BG_CARD,
        hover_color: Tuple[int, int, int] = Theme.BG_CARD_HOVER,
        text_color: Tuple[int, int, int] = Theme.TEXT_WHITE,
        border_color: Optional[Tuple[int, int, int]] = Theme.BORDER_DEFAULT,
        radius: int = 8,
        font_size: int = 15,
        bold: bool = True,
    ):
        self.rect: pygame.Rect = pygame.Rect(rect)
        self.text: str = text
        self.callback: Optional[Callable[[], None]] = callback
        self.bg_color: Tuple[int, int, int] = bg_color
        self.hover_color: Tuple[int, int, int] = hover_color
        self.text_color: Tuple[int, int, int] = text_color
        self.border_color: Optional[Tuple[int, int, int]] = border_color
        self.radius: int = radius
        self.font_size: int = font_size
        self.bold: bool = bold

        self.is_hovered: bool = False
        self.is_pressed: bool = False
        self.disabled: bool = False
        self.hover_progress: float = 0.0  # 0.0 to 1.0 for smooth lerp

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handles mouse hover and click events. Returns True if button was clicked."""
        if self.disabled:
            self.is_hovered = False
            self.is_pressed = False
            return False

        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.is_pressed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.is_pressed and self.rect.collidepoint(event.pos):
                self.is_pressed = False
                if self.callback:
                    self.callback()
                return True
            self.is_pressed = False
        return False

    def update(self, dt: float) -> None:
        """Smoothly interpolates hover state."""
        target = 1.0 if self.is_hovered and not self.disabled else 0.0
        self.hover_progress += (target - self.hover_progress) * min(1.0, dt * 15.0)

    def draw(self, surface: pygame.Surface) -> None:
        """Renders the button with interpolated colors and shadows."""
        # Color interpolation
        r = int(self.bg_color[0] + (self.hover_color[0] - self.bg_color[0]) * self.hover_progress)
        g = int(self.bg_color[1] + (self.hover_color[1] - self.bg_color[1]) * self.hover_progress)
        b = int(self.bg_color[2] + (self.hover_color[2] - self.bg_color[2]) * self.hover_progress)
        current_bg = (r, g, b)

        # Draw glow if hovered
        if self.hover_progress > 0.05 and not self.disabled:
            glow_color = self.border_color if self.border_color else Theme.BORDER_ACCENT
            glow_rect = self.rect.inflate(int(4 * self.hover_progress), int(4 * self.hover_progress))
            Theme.draw_rounded_rect(
                surface, glow_rect, (glow_color[0], glow_color[1], glow_color[2], int(40 * self.hover_progress)),
                radius=self.radius + 2
            )

        # Draw main button
        draw_rect = self.rect.move(0, 1 if self.is_pressed else 0)
        border = Theme.BORDER_ACCENT if self.is_hovered and not self.disabled else self.border_color
        Theme.draw_rounded_rect(surface, draw_rect, current_bg, radius=self.radius, border_color=border, border_width=1)

        # Draw text
        font = Theme.get_font(self.font_size, bold=self.bold)
        txt_color = Theme.TEXT_SUBTLE if self.disabled else self.text_color
        txt_surf = font.render(self.text, True, txt_color)
        txt_rect = txt_surf.get_rect(center=draw_rect.center)
        surface.blit(txt_surf, txt_rect)


class Card:
    """
    Glassmorphism card container with header title and optional accent badge.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        title: str = "",
        badge_text: str = "",
        badge_color: Tuple[int, int, int] = Theme.BORDER_ACCENT,
        radius: int = 12,
        border_color: Optional[Tuple[int, int, int]] = None,
    ):
        self.rect: pygame.Rect = pygame.Rect(rect)
        self.title: str = title
        self.badge_text: str = badge_text
        self.badge_color: Tuple[int, int, int] = badge_color
        self.radius: int = radius
        self.border_color: Optional[Tuple[int, int, int]] = border_color

    def draw(self, surface: pygame.Surface) -> None:
        """Renders the glass card body and header."""
        Theme.draw_glass_panel(surface, self.rect, radius=self.radius, border_color=self.border_color)

        if self.title:
            font = Theme.get_font(14, bold=True)
            txt_surf = font.render(self.title.upper(), True, Theme.TEXT_MUTED)
            surface.blit(txt_surf, (self.rect.x + 16, self.rect.y + 14))

        if self.badge_text:
            badge_x = self.rect.right - 16
            font_badge = Theme.get_font(11, bold=True)
            b_surf = font_badge.render(self.badge_text.upper(), True, Theme.TEXT_WHITE)
            bw = b_surf.get_width() + 14
            bh = 20
            b_rect = pygame.Rect(badge_x - bw, self.rect.y + 12, bw, bh)
            Theme.draw_rounded_rect(surface, b_rect, self.badge_color, radius=10)
            surface.blit(b_surf, (b_rect.centerx - b_surf.get_width() // 2, b_rect.centery - b_surf.get_height() // 2))


class DiceWidget:
    """
    Renders an interactive, polished die with pips, rounded corners, glowing selection,
    and rolling physics.
    """

    def __init__(self, size: int = 70):
        self.size: int = size
        self.rect: pygame.Rect = pygame.Rect(0, 0, size, size)
        self.value: int = 1
        self.is_selected: bool = False
        self.is_hovered: bool = False
        self.is_selectable: bool = False
        self.accent_color: Tuple[int, int, int] = Theme.CYAN_HUMAN
        self.pip_color: Tuple[int, int, int] = Theme.TEXT_WHITE
        self.bg_color: Tuple[int, int, int] = Theme.BG_CARD

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handles click selection when selectable."""
        if not self.is_selectable:
            self.is_hovered = False
            return False

        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False

    def draw(self, surface: pygame.Surface, pos: Tuple[int, int], value: int, rotation: float = 0.0) -> None:
        """Renders the die face at pos with pips."""
        self.rect.topleft = pos
        self.value = value

        # Base die surface
        die_surf = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        inner_rect = pygame.Rect(0, 0, self.size, self.size)

        # Background with subtle gradient
        bg = (38, 48, 68) if self.is_hovered else (24, 32, 48)
        border = self.accent_color if (self.is_selected or self.is_hovered) else Theme.BORDER_DEFAULT
        border_w = 3 if self.is_selected else (2 if self.is_hovered else 1)

        Theme.draw_rounded_rect(die_surf, inner_rect, bg, radius=14, border_color=border, border_width=border_w)

        # Draw pips
        pips = DualDice.PIP_LAYOUTS.get(self.value, [])
        pip_radius = max(3, self.size // 12)
        pip_color = self.accent_color if self.is_selected else Theme.TEXT_WHITE

        for px, py in pips:
            cx = int(px * self.size)
            cy = int(py * self.size)
            # Soft pip shadow
            pygame.draw.circle(die_surf, (10, 15, 25, 180), (cx, cy + 1), pip_radius)
            # Pip core
            pygame.draw.circle(die_surf, pip_color, (cx, cy), pip_radius)

        # If rolling with rotation angle, rotate surface
        if abs(rotation) > 0.5:
            rotated = pygame.transform.rotate(die_surf, rotation)
            rot_rect = rotated.get_rect(center=self.rect.center)
            surface.blit(rotated, rot_rect)
        else:
            surface.blit(die_surf, self.rect)

        # Glow ring when selected
        if self.is_selected:
            Theme.draw_glow_circle(surface, self.rect.center, self.size // 2, self.accent_color, glow_radius=8, alpha=90)


class ShieldWidget:
    """
    Renders visual shield charges with glowing vector shield icons.
    """

    @classmethod
    def draw_shield_icon(
        cls,
        surface: pygame.Surface,
        center: Tuple[int, int],
        size: int = 24,
        color: Tuple[int, int, int] = Theme.AMBER_SHIELD,
        filled: bool = True,
    ) -> None:
        """Draws a vector shield shape."""
        cx, cy = center
        half = size // 2
        pts = [
            (cx - half, cy - half),
            (cx + half, cy - half),
            (cx + half, cy),
            (cx, cy + half),
            (cx - half, cy),
        ]
        if filled:
            # Translucent fill
            fill_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            fill_pts = [(p[0] - cx + size, p[1] - cy + size) for p in pts]
            pygame.draw.polygon(fill_surf, (color[0], color[1], color[2], 180), fill_pts)
            pygame.draw.polygon(fill_surf, color, fill_pts, 2)
            surface.blit(fill_surf, (cx - size, cy - size))
        else:
            pygame.draw.polygon(surface, Theme.BORDER_DEFAULT, pts, 2)


class DecisionScoreBar:
    """
    Visual comparison bar showing candidate A* score, win probability, and weighted total.
    """

    @classmethod
    def draw(
        cls,
        surface: pygame.Surface,
        rect: pygame.Rect,
        label: str,
        value: float,  # 0.0 to 1.0
        color: Tuple[int, int, int],
        font_size: int = 12,
    ) -> None:
        """Renders an animated progress bar with label and percentage."""
        font = Theme.get_font(font_size, bold=False)
        lbl_surf = font.render(label, True, Theme.TEXT_MUTED)
        val_surf = font.render(f"{value * 100:.1f}%", True, Theme.TEXT_WHITE)

        surface.blit(lbl_surf, (rect.x, rect.y - 16))
        surface.blit(val_surf, (rect.right - val_surf.get_width(), rect.y - 16))

        # Background track
        Theme.draw_rounded_rect(surface, rect, (20, 27, 40), radius=rect.height // 2)

        # Filled bar
        fill_w = max(4, int(rect.width * max(0.0, min(1.0, value))))
        fill_rect = pygame.Rect(rect.x, rect.y, fill_w, rect.height)
        Theme.draw_rounded_rect(surface, fill_rect, color, radius=rect.height // 2)


class EventLogWidget:
    """
    Scrollable event log with categorized event entries and timestamps.
    """

    CATEGORY_COLORS = {
        "system": Theme.TEXT_MUTED,
        "dice": Theme.AMBER_SHIELD,
        "choice": Theme.CYAN_HUMAN,
        "ai": Theme.PURPLE_AI,
        "move": Theme.TEXT_WHITE,
        "ladder": Theme.GREEN_LADDER,
        "snake": Theme.RED_SNAKE,
        "shield": Theme.AMBER_SHIELD,
        "warning": Theme.RED_DANGER,
        "victory": Theme.GREEN_ADVANTAGE,
    }

    def __init__(self, rect: pygame.Rect):
        self.rect: pygame.Rect = pygame.Rect(rect)
        self.scroll_offset: int = 0
        self.line_height: int = 22

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handles mouse wheel scrolling."""
        if event.type == pygame.MOUSEWHEEL and self.rect.collidepoint(pygame.mouse.get_pos()):
            self.scroll_offset -= event.y * self.line_height
            self.scroll_offset = max(0, self.scroll_offset)

    def draw(self, surface: pygame.Surface, events: List[Dict[str, Any]]) -> None:
        """Renders event logs inside the container with clipping."""
        Theme.draw_glass_panel(surface, self.rect, radius=8, border_color=Theme.BORDER_DEFAULT)

        clip_rect = self.rect.inflate(-16, -16)
        clip_surf = pygame.Surface((clip_rect.width, clip_rect.height), pygame.SRCALPHA)

        total_height = len(events) * self.line_height
        max_scroll = max(0, total_height - clip_rect.height)
        # Auto-scroll to bottom if user is near end
        if self.scroll_offset > max_scroll:
            self.scroll_offset = max_scroll

        y = -self.scroll_offset
        font = Theme.get_font(12, bold=False)
        time_font = Theme.get_font(11, bold=True)

        for ev in reversed(events):
            if 0 <= y + self.line_height and y <= clip_rect.height:
                cat = ev.get("category", "system")
                color = self.CATEGORY_COLORS.get(cat, Theme.TEXT_WHITE)

                # Time stamp
                t_surf = time_font.render(ev.get("time", ""), True, Theme.TEXT_SUBTLE)
                clip_surf.blit(t_surf, (0, y + 2))

                # Dot marker
                pygame.draw.circle(clip_surf, color, (65, y + 8), 3)

                # Message text
                msg_surf = font.render(ev.get("message", ""), True, color)
                clip_surf.blit(msg_surf, (76, y + 2))

            y += self.line_height

        surface.blit(clip_surf, clip_rect.topleft)


class StatCard:
    """
    Compact status and statistics card.
    """

    @classmethod
    def draw(
        cls,
        surface: pygame.Surface,
        rect: pygame.Rect,
        label: str,
        value: str,
        subtext: str = "",
        accent_color: Tuple[int, int, int] = Theme.CYAN_HUMAN,
    ) -> None:
        """Renders a structured stat card."""
        Theme.draw_rounded_rect(
            surface, rect, (24, 32, 48), radius=8, border_color=Theme.BORDER_DEFAULT, border_width=1
        )

        # Left vertical accent bar
        bar_rect = pygame.Rect(rect.x, rect.y, 4, rect.height)
        Theme.draw_rounded_rect(surface, bar_rect, accent_color, radius=2)

        # Label
        lbl_font = Theme.get_font(11, bold=True)
        l_surf = lbl_font.render(label.upper(), True, Theme.TEXT_MUTED)
        surface.blit(l_surf, (rect.x + 12, rect.y + 8))

        # Value
        val_font = Theme.get_font(20, bold=True)
        v_surf = val_font.render(value, True, Theme.TEXT_WHITE)
        surface.blit(v_surf, (rect.x + 12, rect.y + 24))

        # Subtext
        if subtext:
            sub_font = Theme.get_font(11, bold=False)
            s_surf = sub_font.render(subtext, True, Theme.TEXT_SUBTLE)
            surface.blit(s_surf, (rect.x + 12, rect.y + 48))


class Modal:
    """
    Floating dialog box overlay with darkened backdrop.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        title: str,
        message: str,
        buttons: List[Button],
        accent_color: Tuple[int, int, int] = Theme.BORDER_ACCENT,
    ):
        self.rect: pygame.Rect = pygame.Rect(rect)
        self.title: str = title
        self.message: str = message
        self.buttons: List[Button] = buttons
        self.accent_color: Tuple[int, int, int] = accent_color

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Dispatches event to modal buttons."""
        for btn in self.buttons:
            if btn.handle_event(event):
                return True
        return False

    def update(self, dt: float) -> None:
        for btn in self.buttons:
            btn.update(dt)

    def draw(self, surface: pygame.Surface, screen_size: Tuple[int, int]) -> None:
        """Renders the darkened modal backdrop and dialog panel."""
        # Backdrop
        overlay = pygame.Surface(screen_size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        # Dialog Box
        Theme.draw_glass_panel(surface, self.rect, radius=16, border_color=self.accent_color, alpha=240)

        # Title
        t_font = Theme.get_font(20, bold=True)
        t_surf = t_font.render(self.title, True, Theme.TEXT_WHITE)
        surface.blit(t_surf, (self.rect.centerx - t_surf.get_width() // 2, self.rect.y + 24))

        # Message
        m_font = Theme.get_font(14, bold=False)
        lines = self.message.split("\n")
        y = self.rect.y + 60
        for line in lines:
            m_surf = m_font.render(line, True, Theme.TEXT_MUTED)
            surface.blit(m_surf, (self.rect.centerx - m_surf.get_width() // 2, y))
            y += 22

        # Buttons
        for btn in self.buttons:
            btn.draw(surface)
