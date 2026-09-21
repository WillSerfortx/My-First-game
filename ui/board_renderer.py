"""Renders the 10x10 board: cells, curved snakes, ladders, tokens and overlays."""
from __future__ import annotations

import math
import time

import pygame

from game.board import Board
from game.constants import BOARD_SIZE, GOAL_CELL, START_CELL

from . import draw, theme
from .animations import pulse
from .theme import Color, S, fonts

SNAKE_PALETTES: list[tuple[Color, Color]] = [
    ((0, 200, 150), (150, 255, 220)), ((255, 122, 60), (255, 206, 150)),
    ((208, 88, 255), (238, 190, 255)), ((255, 84, 116), (255, 176, 190)),
    ((88, 172, 255), (176, 218, 255)), ((246, 204, 70), (255, 240, 170)),
    ((110, 224, 92), (200, 255, 170)), ((255, 122, 196), (255, 200, 232)),
    ((66, 214, 224), (170, 244, 248)), ((176, 138, 255), (222, 204, 255)),
]

Frac = tuple[float, float]


class BoardRenderer:
    """Draws the board inside a square rect; positions are exposed as fractions of the grid
    so token/path animation is independent of the window size."""

    def __init__(self, board: Board, clusterer=None) -> None:
        self.board = board
        self.clusterer = clusterer
        self.rect = pygame.Rect(0, 0, 100, 100)
        self.grid_rect = pygame.Rect(0, 0, 100, 100)
        self.cell_px = 10.0
        self._static: dict[bool, pygame.Surface] = {}
        self._built_size: tuple[int, int] | None = None
        self._built_scale = 0.0
        self._changed_at = 0.0
        self._scaled_preview: tuple[tuple[int, int], pygame.Surface] | None = None
        self.snake_paths: dict[int, list[Frac]] = {}
        self.ladder_paths: dict[int, list[Frac]] = {}
        self._build_paths()

    # ------------------------------------------------------------- geometry
    @staticmethod
    def cell_center_frac(cell: int) -> Frac:
        row, col = Board.cell_to_grid(cell)
        return ((col + 0.5) / BOARD_SIZE, (BOARD_SIZE - 1 - row + 0.5) / BOARD_SIZE)

    def set_rect(self, rect: pygame.Rect) -> None:
        if rect.size != self.rect.size:
            self._changed_at = time.time()
        self.rect = pygame.Rect(rect)
        pad = S(12)
        self.grid_rect = self.rect.inflate(-2 * pad, -2 * pad)
        self.cell_px = self.grid_rect.w / BOARD_SIZE

    def frac_to_screen(self, frac: Frac) -> tuple[float, float]:
        return (self.grid_rect.x + frac[0] * self.grid_rect.w,
                self.grid_rect.y + frac[1] * self.grid_rect.h)

    def cell_center(self, cell: int) -> tuple[float, float]:
        return self.frac_to_screen(self.cell_center_frac(cell))

    def cell_rect(self, cell: int) -> pygame.Rect:
        cx, cy = self.cell_center(cell)
        cs = self.cell_px
        return pygame.Rect(int(cx - cs / 2), int(cy - cs / 2), int(cs), int(cs))

    def cell_at(self, pos: tuple[int, int]) -> int | None:
        if not self.grid_rect.collidepoint(pos):
            return None
        col = int((pos[0] - self.grid_rect.x) / self.cell_px)
        row_from_top = int((pos[1] - self.grid_rect.y) / self.cell_px)
        col = max(0, min(BOARD_SIZE - 1, col))
        row = BOARD_SIZE - 1 - max(0, min(BOARD_SIZE - 1, row_from_top))
        return Board.grid_to_cell(row, col)

    # -------------------------------------------------------- snake / ladder
    def _build_paths(self) -> None:
        for i, (head, tail) in enumerate(sorted(self.board.snakes.items())):
            self.snake_paths[head] = self._snake_path(self.cell_center_frac(head),
                                                      self.cell_center_frac(tail), i)
        for bottom, top in self.board.ladders.items():
            self.ladder_paths[bottom] = [self.cell_center_frac(bottom), self.cell_center_frac(top)]

    @staticmethod
    def _snake_path(a: Frac, b: Frac, seed: int) -> list[Frac]:
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy) or 1e-6
        nx, ny = -dy / length, dx / length
        waves = max(2.0, length / 0.11)
        amp = 0.034 if length > 0.15 else 0.02
        phase = seed * 1.7
        count = max(30, int(length / 0.005))
        pts: list[Frac] = []
        for i in range(count + 1):
            t = i / count
            env = math.sin(math.pi * t) ** 0.7
            off = amp * env * math.sin(t * waves * math.pi + phase)
            pts.append((a[0] + dx * t + nx * off, a[1] + dy * t + ny * off))
        return pts

    # ----------------------------------------------------------- static layer
    def _zone_color(self, cell: int) -> Color:
        return theme.ZONE_COLORS.get(self.clusterer.zone_of(cell), theme.BLUE) if self.clusterer else theme.BLUE

    def _build_static(self, heat: bool) -> pygame.Surface:
        w, h = self.rect.size
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        frame = pygame.Rect(0, 0, w, h)
        draw.gradient_rrect(surf, frame, (36, 46, 88), (14, 18, 42), S(24))
        draw.stroke_rrect(surf, frame, (110, 150, 240, 170), S(24), 2)
        draw.stroke_rrect(surf, frame.inflate(-S(6), -S(6)), (255, 255, 255, 22), S(21), 1)
        off = (self.grid_rect.x - self.rect.x, self.grid_rect.y - self.rect.y)
        cs = self.cell_px

        def local_rect(cell: int) -> pygame.Rect:
            u, v = self.cell_center_frac(cell)
            cx, cy = off[0] + u * self.grid_rect.w, off[1] + v * self.grid_rect.h
            return pygame.Rect(int(cx - cs / 2), int(cy - cs / 2), int(cs), int(cs))

        def local_pt(frac: Frac) -> Frac:
            return (off[0] + frac[0] * self.grid_rect.w, off[1] + frac[1] * self.grid_rect.h)

        heads, tails = set(self.board.snakes), set(self.board.snakes.values())
        bottoms, tops = set(self.board.ladders), set(self.board.ladders.values())
        radius = max(4, int(cs * 0.14))
        for cell in range(START_CELL, GOAL_CELL + 1):
            r = local_rect(cell).inflate(-S(3), -S(3))
            row, col = Board.cell_to_grid(cell)
            top, bottom = ((34, 44, 82), (24, 31, 62)) if (row + col) % 2 == 0 else ((28, 37, 72), (19, 25, 52))
            border: Color = (86, 104, 168, 70)
            if cell in heads:
                top, bottom, border = (96, 34, 56), (54, 22, 42), (255, 96, 120, 200)
            elif cell in tails:
                top, bottom, border = (24, 74, 78), (16, 46, 56), (80, 236, 210, 170)
            elif cell in bottoms:
                top, bottom, border = (98, 76, 30), (58, 44, 22), (255, 208, 100, 200)
            elif cell in tops:
                top, bottom, border = (26, 84, 62), (16, 52, 44), (100, 248, 170, 170)
            if cell == GOAL_CELL:
                top, bottom, border = (190, 148, 52), (110, 76, 34), (255, 226, 140, 255)
            elif cell == START_CELL:
                top, bottom, border = (30, 96, 84), (18, 58, 58), (100, 250, 190, 220)
            if heat:
                zc = self._zone_color(cell)
                top = draw.lerp_color(top, zc, 0.42)
                bottom = draw.lerp_color(bottom, zc, 0.30)
                border = draw.with_alpha(zc, 180)
            draw.gradient_rrect(surf, r, top, bottom, radius)
            draw.stroke_rrect(surf, r, border, radius, 2 if (cell in heads | tails | bottoms | tops or cell in (1, 100)) else 1)

        for bottom_cell, top_cell in self.board.ladders.items():
            self._draw_ladder(surf, [local_pt(p) for p in self.ladder_paths[bottom_cell]])
        for i, head in enumerate(sorted(self.board.snakes)):
            self._draw_snake(surf, [local_pt(p) for p in self.snake_paths[head]], SNAKE_PALETTES[i % 10])

        nf = fonts.get(cs / theme.get_scale() * 0.21, True)
        for cell in range(START_CELL, GOAL_CELL + 1):
            r = local_rect(cell)
            draw.draw_text(surf, str(cell), nf, (198, 210, 244), (r.x + S(8), r.y + S(6)), shadow=True)
            if cell == GOAL_CELL:
                draw.draw_star(surf, r.centerx, r.centery + S(2), cs * 0.22, (255, 240, 170))
                draw.draw_text(surf, "GOAL", fonts.get(cs / theme.get_scale() * 0.17, True),
                               (60, 40, 10), (r.centerx, r.bottom - S(9)), "midbottom")
            elif cell == START_CELL:
                draw.draw_text(surf, "START", fonts.get(cs / theme.get_scale() * 0.17, True),
                               theme.GREEN, (r.centerx, r.bottom - S(9)), "midbottom", shadow=True)
            elif cell in heads:
                draw.draw_chevron(surf, r.right - S(15), r.bottom - S(14), cs * 0.09, (255, 130, 146), up=False, width=max(2, S(2)))
            elif cell in bottoms:
                draw.draw_chevron(surf, r.right - S(15), r.bottom - S(14), cs * 0.09, (255, 220, 130), up=True, width=max(2, S(2)))
        return surf

    def _draw_ladder(self, surf: pygame.Surface, pts: list[Frac]) -> None:
        (x0, y0), (x1, y1) = pts[0], pts[-1]
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy) or 1.0
        ux, uy = dx / length, dy / length
        nx, ny = -uy, ux
        half = self.cell_px * 0.13
        rail = max(3, int(self.cell_px * 0.065))
        wood, wood_dark, wood_light = (236, 190, 108), (98, 62, 26), (255, 232, 170)
        left = ((x0 + nx * half, y0 + ny * half), (x1 + nx * half, y1 + ny * half))
        right = ((x0 - nx * half, y0 - ny * half), (x1 - nx * half, y1 - ny * half))
        for a, b in (left, right):                               # soft shadow
            pygame.draw.line(surf, (12, 16, 30), (a[0] + 2, a[1] + 3), (b[0] + 2, b[1] + 3), rail + 2)
        rungs = max(3, int(length / (self.cell_px * 0.34)))
        for i in range(1, rungs):
            t = i / rungs
            cx, cy = x0 + dx * t, y0 + dy * t
            pygame.draw.line(surf, wood_dark, (cx + nx * half, cy + ny * half), (cx - nx * half, cy - ny * half), max(3, rail))
            pygame.draw.line(surf, wood, (cx + nx * half, cy + ny * half), (cx - nx * half, cy - ny * half), max(2, rail - 2))
        for a, b in (left, right):
            pygame.draw.line(surf, wood_dark, a, b, rail + 2)
            pygame.draw.line(surf, wood, a, b, rail)
            pygame.draw.line(surf, wood_light, (a[0] - nx, a[1] - ny), (b[0] - nx, b[1] - ny), max(1, rail // 3))
        for p in ((x0, y0), (x1, y1)):
            draw.draw_glow(surf, p, self.cell_px * 0.36, theme.GOLD, 110)
            pygame.draw.circle(surf, wood_dark, (int(p[0]), int(p[1])), max(4, int(self.cell_px * 0.10)))
            pygame.draw.circle(surf, wood_light, (int(p[0]), int(p[1])), max(3, int(self.cell_px * 0.07)))

    def _draw_snake(self, surf: pygame.Surface, pts: list[Frac], palette: tuple[Color, Color]) -> None:
        base, light = palette
        dark = draw.darken(base, 0.55)
        n = len(pts)
        cs = self.cell_px
        for i in range(n - 1, -1, -1):                            # shadow + outline, tail first
            t = i / max(1, n - 1)
            r = cs * (0.150 - 0.105 * t ** 0.85)
            pygame.draw.circle(surf, (10, 14, 26), (int(pts[i][0] + 2), int(pts[i][1] + 3)), int(r + 2))
        for i in range(n - 1, -1, -1):
            t = i / max(1, n - 1)
            r = cs * (0.150 - 0.105 * t ** 0.85)
            pygame.draw.circle(surf, dark, (int(pts[i][0]), int(pts[i][1])), int(r + 1.5))
        for i in range(n - 1, -1, -1):
            t = i / max(1, n - 1)
            r = cs * (0.150 - 0.105 * t ** 0.85)
            band = (i // 5) % 2 == 0
            col = base if band else draw.lerp_color(base, light, 0.35)
            pygame.draw.circle(surf, col, (int(pts[i][0]), int(pts[i][1])), max(1, int(r)))
            if i % 5 == 2:
                pygame.draw.circle(surf, draw.lerp_color(col, light, 0.6),
                                   (int(pts[i][0] - r * 0.25), int(pts[i][1] - r * 0.3)), max(1, int(r * 0.35)))
        # head
        hx, hy = pts[0]
        fx, fy = pts[min(4, n - 1)]
        dx, dy = hx - fx, hy - fy
        d = math.hypot(dx, dy) or 1.0
        ux, uy = dx / d, dy / d
        nx, ny = -uy, ux
        hr = cs * 0.185
        tongue_base = (hx + ux * hr * 0.9, hy + uy * hr * 0.9)
        tongue_end = (hx + ux * hr * 1.9, hy + uy * hr * 1.9)
        pygame.draw.line(surf, (255, 70, 96), tongue_base, tongue_end, max(1, int(cs * 0.03)))
        for s in (-1, 1):
            pygame.draw.line(surf, (255, 70, 96), tongue_end,
                             (tongue_end[0] + ux * hr * 0.35 + nx * s * hr * 0.35,
                              tongue_end[1] + uy * hr * 0.35 + ny * s * hr * 0.35), max(1, int(cs * 0.025)))
        pygame.draw.circle(surf, dark, (int(hx), int(hy)), int(hr + 1.5))
        pygame.draw.circle(surf, draw.lerp_color(base, light, 0.2), (int(hx), int(hy)), int(hr))
        for s in (-1, 1):
            ex, ey = hx + ux * hr * 0.28 + nx * s * hr * 0.5, hy + uy * hr * 0.28 + ny * s * hr * 0.5
            pygame.draw.circle(surf, (255, 255, 255), (int(ex), int(ey)), max(2, int(hr * 0.30)))
            pygame.draw.circle(surf, (20, 10, 30), (int(ex + ux * hr * 0.08), int(ey + uy * hr * 0.08)), max(1, int(hr * 0.15)))

    # ------------------------------------------------------------ dynamic draw
    def draw(self, surface: pygame.Surface, t: float, heat: bool = False) -> None:
        size = self.rect.size
        if self._built_size != size or self._built_scale != theme.get_scale():
            stable = time.time() - self._changed_at > 0.25
            if self._built_size is None or stable or not self._static.get(heat):
                self._static = {}
                self._built_size, self._built_scale = size, theme.get_scale()
                self._scaled_preview = None
            else:
                # while the window is being dragged show the old bitmap, scaled
                old = self._static[heat]
                if self._scaled_preview is None or self._scaled_preview[0] != size:
                    self._scaled_preview = (size, pygame.transform.smoothscale(old, size))
                draw.draw_shadow(surface, self.rect, S(24), S(22), 130, S(8))
                surface.blit(self._scaled_preview[1], self.rect.topleft)
                return
        if heat not in self._static:
            self._static[heat] = self._build_static(heat)
        glow_a = 44 + int(16 * pulse(t, 0.4))
        draw.draw_glow_rect(surface, self.rect, theme.CYAN, S(24), S(26), glow_a)
        draw.draw_shadow(surface, self.rect, S(24), S(22), 130, S(8))
        surface.blit(self._static[heat], self.rect.topleft)

    # -------------------------------------------------------------- overlays
    def draw_cell_ring(self, surface: pygame.Surface, cell: int, color: Color, t: float,
                       strength: float = 1.0) -> None:
        r = self.cell_rect(cell).inflate(-S(2), -S(2))
        p = pulse(t, 1.2)
        draw.draw_glow_rect(surface, r, color, max(4, int(self.cell_px * 0.14)), S(12),
                            int((70 + 90 * p) * strength))
        draw.stroke_rrect(surface, r, draw.with_alpha(color, int(200 * strength)),
                          max(4, int(self.cell_px * 0.14)), max(2, S(3)))

    def draw_destination_marker(self, surface: pygame.Surface, cell: int, color: Color, t: float,
                                label: str = "") -> None:
        self.draw_cell_ring(surface, cell, color, t, 0.9)
        cx, cy = self.cell_center(cell)
        bob = math.sin(t * 5) * S(3)
        if label:
            font = fonts.get(12, True)
            tw = font.size(label)[0]
            bubble = pygame.Rect(0, 0, tw + S(16), S(22))
            bubble.midbottom = (int(cx), int(cy - self.cell_px * 0.34 + bob))
            draw.fill_rrect(surface, bubble, (10, 14, 34, 235), bubble.h // 2)
            draw.stroke_rrect(surface, bubble, draw.with_alpha(color, 220), bubble.h // 2, 1)
            draw.draw_text(surface, label, font, theme.TEXT, bubble.center, "center")

    def draw_route(self, surface: pygame.Surface, cells: tuple[int, ...], color: Color, t: float) -> None:
        """Animated dashed route through ``cells`` (BFS / A* path overlay)."""
        pts = [self.cell_center(c) for c in cells]
        for a, b in zip(pts, pts[1:]):
            draw.dashed_line(surface, color, a, b, S(8), S(6), t * S(40), max(2, S(3)))
        for i, (x, y) in enumerate(pts):
            draw.draw_glow(surface, (x, y), S(14), color, 120)
            pygame.draw.circle(surface, color, (int(x), int(y)), max(3, S(4)))

    def draw_token(self, surface: pygame.Surface, frac: Frac, color: Color, t: float,
                   lift: float = 0.0, x_offset: float = 0.0, phase: float = 0.0,
                   scale: float = 1.0) -> None:
        x, y = self.frac_to_screen(frac)
        bob = math.sin(t * 3.2 + phase) * self.cell_px * 0.035
        r = self.cell_px * 0.155 * scale
        draw.draw_pawn(surface, x + x_offset, y + self.cell_px * 0.22, r, color,
                       glow_alpha=150, lift=lift + bob + self.cell_px * 0.05)
