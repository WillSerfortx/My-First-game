"""
Board Renderer module for AI-Powered Snake & Ladder.
Renders the 10x10 serpentine board, risk-tinted cells, curved organic snakes with glowing eyes,
perspective ladders with rails and rungs, and animated player tokens with glowing auras.
"""

import pygame
import math
from typing import Tuple, List, Dict, Optional, Any
from game.board import Board
from game.player import Player
from .theme import Theme


class BoardRenderer:
    """
    High-fidelity 10x10 Snake & Ladder board renderer.
    """

    def __init__(self, board: Optional[Board] = None):
        self.board: Board = board if board is not None else Board()
        self.board_rect: pygame.Rect = pygame.Rect(0, 0, 700, 700)
        self.cell_size: float = 70.0

        # Precomputed cell centers and rects
        self.cell_rects: Dict[int, pygame.Rect] = {}
        self.cell_centers: Dict[int, Tuple[float, float]] = {}

    def update_layout(self, rect: pygame.Rect) -> None:
        """Updates board dimensions and cell boundaries based on available screen rectangle."""
        self.board_rect = pygame.Rect(rect)
        self.cell_size = self.board_rect.width / float(self.board.GRID_SIZE)

        self.cell_rects = {}
        self.cell_centers = {}

        for c in range(1, self.board.TOTAL_CELLS + 1):
            col, row = self.board.get_cell_coordinates(c)
            x = self.board_rect.x + col * self.cell_size
            y = self.board_rect.y + row * self.cell_size
            r = pygame.Rect(int(x), int(y), int(math.ceil(self.cell_size)), int(math.ceil(self.cell_size)))
            self.cell_rects[c] = r
            self.cell_centers[c] = (x + self.cell_size / 2.0, y + self.cell_size / 2.0)

    def draw(
        self,
        surface: pygame.Surface,
        human_player: Player,
        ai_player: Player,
        cell_zones: Optional[Dict[int, str]] = None,
        hovered_cell: Optional[int] = None,
    ) -> None:
        """Renders the entire game board with all layers."""
        self._draw_board_background(surface)
        self._draw_cells(surface, cell_zones, hovered_cell)
        self._draw_ladders(surface)
        self._draw_snakes(surface)
        self._draw_players(surface, human_player, ai_player)

    def _draw_board_background(self, surface: pygame.Surface) -> None:
        """Draws the outer frame and board backing."""
        frame_rect = self.board_rect.inflate(12, 12)
        Theme.draw_glass_panel(surface, frame_rect, radius=16, border_color=Theme.BORDER_ACCENT, alpha=230)
        # Inner clipping background
        pygame.draw.rect(surface, Theme.BG_DARK, self.board_rect, border_radius=12)

    def _draw_cells(
        self,
        surface: pygame.Surface,
        cell_zones: Optional[Dict[int, str]],
        hovered_cell: Optional[int],
    ) -> None:
        """Renders individual 100 cells with numbering and risk zone highlights."""
        font_num = Theme.get_font(12, bold=True)
        font_goal = Theme.get_font(14, bold=True)

        for c in range(1, self.board.TOTAL_CELLS + 1):
            rect = self.cell_rects[c]
            col, row = self.board.get_cell_coordinates(c)

            # Alternating grid shading
            is_even = (col + row) % 2 == 0
            base_color = Theme.BG_CELL_LIGHT if is_even else Theme.BG_CELL_DARK

            # Risk zone tinting from K-Means
            if cell_zones and c in cell_zones:
                zone = cell_zones[c]
                if zone == "Danger":
                    base_color = (35, 20, 28)
                elif zone == "Advantage":
                    base_color = (18, 36, 32)
                elif zone == "Safe":
                    base_color = (18, 28, 45)

            # Cell 100 highlight
            if c == 100:
                base_color = (38, 48, 80)

            # Hover highlight
            border_color = Theme.BORDER_DEFAULT
            border_w = 1
            if c == hovered_cell:
                border_color = Theme.CYAN_HUMAN
                border_w = 2

            pygame.draw.rect(surface, base_color, rect)
            pygame.draw.rect(surface, border_color, rect, border_w)

            # Cell number
            if c == 100:
                t_surf = font_goal.render("100 ★", True, Theme.AMBER_SHIELD)
                surface.blit(t_surf, (rect.x + 4, rect.y + 4))
            elif c == 1:
                t_surf = font_num.render("1 START", True, Theme.CYAN_HUMAN)
                surface.blit(t_surf, (rect.x + 4, rect.y + 4))
            else:
                t_surf = font_num.render(str(c), True, Theme.TEXT_MUTED)
                surface.blit(t_surf, (rect.x + 5, rect.y + 4))

            # Icon badges on snake head/ladder bottom
            if self.board.is_snake_head(c):
                # Snake icon indicator
                tail = self.board.get_snake_tail(c)
                ind_font = Theme.get_font(10, bold=True)
                s_surf = ind_font.render(f"▼{tail}", True, Theme.RED_DANGER)
                surface.blit(s_surf, (rect.right - s_surf.get_width() - 4, rect.bottom - s_surf.get_height() - 3))
            elif self.board.is_ladder_bottom(c):
                # Ladder icon indicator
                top = self.board.get_ladder_top(c)
                ind_font = Theme.get_font(10, bold=True)
                l_surf = ind_font.render(f"▲{top}", True, Theme.GREEN_ADVANTAGE)
                surface.blit(l_surf, (rect.right - l_surf.get_width() - 4, rect.bottom - l_surf.get_height() - 3))

    def _draw_ladders(self, surface: pygame.Surface) -> None:
        """Renders 9 dual-rail glowing ladders with cross rungs."""
        ladder_width = 14.0

        for bottom, top in self.board.ladders.items():
            start_x, start_y = self.cell_centers[bottom]
            end_x, end_y = self.cell_centers[top]

            dx = end_x - start_x
            dy = end_y - start_y
            length = math.hypot(dx, dy)
            if length < 1e-4:
                continue

            # Unit normal vector
            nx = -dy / length
            ny = dx / length

            # Left and right rail endpoints
            lx1 = start_x + nx * (ladder_width / 2.0)
            ly1 = start_y + ny * (ladder_width / 2.0)
            lx2 = end_x + nx * (ladder_width / 2.0)
            ly2 = end_y + ny * (ladder_width / 2.0)

            rx1 = start_x - nx * (ladder_width / 2.0)
            ry1 = start_y - ny * (ladder_width / 2.0)
            rx2 = end_x - nx * (ladder_width / 2.0)
            ry2 = end_y - ny * (ladder_width / 2.0)

            # Draw glowing outer rails
            glow_color = (16, 185, 129, 90)
            rail_color = Theme.GREEN_LADDER
            highlight_color = (167, 243, 208)

            pygame.draw.line(surface, rail_color, (lx1, ly1), (lx2, ly2), 4)
            pygame.draw.line(surface, rail_color, (rx1, ry1), (rx2, ry2), 4)

            # Inner rail core
            pygame.draw.line(surface, highlight_color, (lx1, ly1), (lx2, ly2), 1)
            pygame.draw.line(surface, highlight_color, (rx1, ry1), (rx2, ry2), 1)

            # Draw rungs
            rung_spacing = 22.0
            num_rungs = max(2, int(length // rung_spacing))
            for i in range(1, num_rungs):
                t = i / float(num_rungs)
                # Left point at t
                r_lx = lx1 + t * (lx2 - lx1)
                r_ly = ly1 + t * (ly2 - ly1)
                # Right point at t
                r_rx = rx1 + t * (rx2 - rx1)
                r_ry = ry1 + t * (ry2 - ry1)

                pygame.draw.line(surface, rail_color, (r_lx, r_ly), (r_rx, r_ry), 3)
                pygame.draw.line(surface, highlight_color, (r_lx, r_ly), (r_rx, r_ry), 1)

            # Small foot/top caps
            pygame.draw.circle(surface, rail_color, (int(start_x), int(start_y)), 5)
            pygame.draw.circle(surface, rail_color, (int(end_x), int(end_y)), 5)

    def _draw_snakes(self, surface: pygame.Surface) -> None:
        """Renders 10 curved serpentine snakes with glowing heads and eyes."""
        for head, tail in self.board.snakes.items():
            hx, hy = self.cell_centers[head]
            tx, ty = self.cell_centers[tail]

            dx = tx - hx
            dy = ty - hy
            dist = math.hypot(dx, dy)
            if dist < 1e-4:
                continue

            # Perpendicular vector for wave curves
            nx = -dy / dist
            ny = dx / dist

            # Sine wave curve points
            num_points = max(15, int(dist // 8))
            points: List[Tuple[float, float]] = []
            wave_amp = min(28.0, dist * 0.18)
            cycles = 2.5 if dist > 200 else 1.5

            for i in range(num_points + 1):
                t = i / float(num_points)
                # Straight line interpolation
                bx = hx + t * dx
                by = hy + t * dy
                # Sinusoidal wiggle that tapers to 0 at both head and tail
                envelope = math.sin(t * math.pi)
                wiggle = math.sin(t * cycles * 2 * math.pi) * wave_amp * envelope
                px = bx + nx * wiggle
                py = by + ny * wiggle
                points.append((px, py))

            # Draw layered tapered body
            for i in range(len(points) - 1):
                t = i / float(len(points))
                # Taper body width from 8 at head to 2 at tail
                w = max(2, int(8 * (1.0 - t * 0.75)))
                p1 = points[i]
                p2 = points[i + 1]
                # Body color gradient
                body_color = Theme.RED_SNAKE
                pygame.draw.line(surface, body_color, p1, p2, w + 2)
                pygame.draw.line(surface, (254, 202, 202), p1, p2, max(1, w // 2))

            # Snake Head
            head_radius = 9
            pygame.draw.circle(surface, Theme.RED_SNAKE, (int(hx), int(hy)), head_radius)
            pygame.draw.circle(surface, (185, 28, 28), (int(hx), int(hy)), head_radius, 2)

            # Glowing eyes
            # Eye offset toward tail direction
            eye_angle = math.atan2(dy, dx) + math.pi
            eye_dist = 4
            eye1_x = int(hx + math.cos(eye_angle + 0.6) * eye_dist)
            eye1_y = int(hy + math.sin(eye_angle + 0.6) * eye_dist)
            eye2_x = int(hx + math.cos(eye_angle - 0.6) * eye_dist)
            eye2_y = int(hy + math.sin(eye_angle - 0.6) * eye_dist)

            pygame.draw.circle(surface, Theme.AMBER_SHIELD, (eye1_x, eye1_y), 2)
            pygame.draw.circle(surface, Theme.AMBER_SHIELD, (eye2_x, eye2_y), 2)

            # Tail tip
            pygame.draw.circle(surface, Theme.RED_SNAKE, (int(tx), int(ty)), 3)

    def _draw_players(self, surface: pygame.Surface, human: Player, ai: Player) -> None:
        """Renders animated player pieces with neon orbs, rings, and smooth interpolation."""
        # Calculate human screen position
        h_pos = self._get_interpolated_pos(human.visual_cell)
        ai_pos = self._get_interpolated_pos(ai.visual_cell)

        # If both players are at the exact same location, slightly offset them horizontally
        dist_between = math.hypot(h_pos[0] - ai_pos[0], h_pos[1] - ai_pos[1])
        offset = 12.0 if dist_between < 10.0 else 0.0

        # Human Piece (Cyan theme)
        h_draw_pos = (h_pos[0] - offset, h_pos[1])
        self._render_single_player(
            surface=surface,
            pos=h_draw_pos,
            color=Theme.CYAN_HUMAN,
            glow_color=Theme.CYAN_HUMAN_GLOW,
            label="H",
            glow_phase=human.glow_timer,
        )

        # AI Piece (Purple theme)
        ai_draw_pos = (ai_pos[0] + offset, ai_pos[1])
        self._render_single_player(
            surface=surface,
            pos=ai_draw_pos,
            color=Theme.PURPLE_AI,
            glow_color=Theme.PURPLE_AI_GLOW,
            label="AI",
            glow_phase=ai.glow_timer,
        )

    def _render_single_player(
        self,
        surface: pygame.Surface,
        pos: Tuple[float, float],
        color: Tuple[int, int, int],
        glow_color: Tuple[int, int, int],
        label: str,
        glow_phase: float,
    ) -> None:
        """Renders a single player token with pulsing neon glow and center letter."""
        cx, cy = int(pos[0]), int(pos[1])
        radius = max(10, int(self.cell_size * 0.22))

        # Pulsing ring calculation
        pulse = (math.sin(glow_phase * 4.0) + 1.0) * 0.5  # 0.0 to 1.0
        glow_radius = int(8 + pulse * 6)

        # Outer glow
        Theme.draw_glow_circle(surface, (cx, cy), radius, color, glow_radius=glow_radius, alpha=100)

        # Inner solid orb
        pygame.draw.circle(surface, color, (cx, cy), radius)
        # White highlight crescent
        pygame.draw.circle(surface, (255, 255, 255), (cx - 2, cy - 2), max(2, radius // 3))

        # Token text label
        font = Theme.get_font(11, bold=True)
        txt = font.render(label, True, Theme.BG_DARK)
        surface.blit(txt, (cx - txt.get_width() // 2, cy - txt.get_height() // 2 + 1))

    def _get_interpolated_pos(self, cell_val: float) -> Tuple[float, float]:
        """Linearly interpolates coordinates between cell floor and ceil."""
        c1 = max(1, min(self.board.TOTAL_CELLS, int(math.floor(cell_val))))
        c2 = max(1, min(self.board.TOTAL_CELLS, int(math.ceil(cell_val))))
        frac = cell_val - math.floor(cell_val)

        p1 = self.cell_centers[c1]
        p2 = self.cell_centers[c2]

        x = p1[0] + frac * (p2[0] - p1[0])
        y = p1[1] + frac * (p2[1] - p1[1])
        return x, y

    def get_cell_at_pos(self, pos: Tuple[int, int]) -> Optional[int]:
        """Returns the cell number (1..100) colliding with screen mouse coordinates."""
        for c, rect in self.cell_rects.items():
            if rect.collidepoint(pos):
                return c
        return None
