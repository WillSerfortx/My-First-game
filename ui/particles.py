"""Small particle system and ambient background orbs."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame

from . import draw, theme
from .theme import Color

MAX_PARTICLES = 700


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    size: float
    color: Color
    gravity: float = 0.0
    drag: float = 0.0


class ParticleSystem:
    """Glowing sparks in screen space (frame-rate independent)."""

    def __init__(self) -> None:
        self.particles: list[Particle] = []
        self._rng = random.Random()

    def clear(self) -> None:
        self.particles.clear()

    def emit(self, x: float, y: float, color: Color, count: int = 12, speed: float = 120.0,
             life: float = 0.8, size: float = 4.0, gravity: float = 0.0, spread: float = math.tau,
             direction: float = 0.0, drag: float = 1.2) -> None:
        rng = self._rng
        for _ in range(count):
            if len(self.particles) >= MAX_PARTICLES:
                return
            ang = direction + (rng.random() - 0.5) * spread
            spd = speed * (0.35 + rng.random() * 0.65)
            lf = life * (0.6 + rng.random() * 0.4)
            self.particles.append(Particle(x, y, math.cos(ang) * spd, math.sin(ang) * spd, lf, lf,
                                           size * (0.6 + rng.random() * 0.8), color, gravity, drag))

    # presets ------------------------------------------------------------
    def burst(self, x: float, y: float, color: Color, count: int = 18) -> None:
        self.emit(x, y, color, count, speed=170, life=0.8, size=theme.S(4))

    def sparkle_trail(self, x: float, y: float, color: Color) -> None:
        self.emit(x, y, color, 2, speed=40, life=0.6, size=theme.S(3), gravity=-20)

    def fountain(self, x: float, y: float, color: Color, count: int = 30) -> None:
        self.emit(x, y, color, count, speed=320, life=1.4, size=theme.S(4), gravity=380,
                  spread=math.radians(70), direction=-math.pi / 2, drag=0.4)

    def update(self, dt: float) -> None:
        alive: list[Particle] = []
        for p in self.particles:
            p.life -= dt
            if p.life <= 0:
                continue
            p.vy += p.gravity * dt
            damp = max(0.0, 1.0 - p.drag * dt)
            p.vx *= damp
            p.vy *= damp
            p.x += p.vx * dt
            p.y += p.vy * dt
            alive.append(p)
        self.particles = alive

    def draw(self, surface: pygame.Surface) -> None:
        for p in self.particles:
            t = p.life / p.max_life
            radius = max(2.0, p.size * (0.4 + 0.9 * t) * 2.2)
            draw.draw_glow(surface, (p.x, p.y), radius, p.color, int(220 * t))


class AmbientField:
    """Slowly drifting glow orbs over a cached gradient + grid background."""

    RADII = (0.055, 0.085, 0.12)      # bucketed so the glow sprites are cached
    ALPHAS = (28, 40, 54)

    def __init__(self, count: int = 14, seed: int = 5) -> None:
        rng = random.Random(seed)
        palette = [theme.CYAN, theme.MAGENTA, theme.BLUE, theme.GOLD]
        self.orbs = [{
            "x": rng.random(), "y": rng.random(),
            "vx": (rng.random() - 0.5) * 0.02, "vy": -0.006 - rng.random() * 0.02,
            "r": rng.choice(self.RADII), "c": rng.choice(palette), "a": rng.choice(self.ALPHAS),
        } for _ in range(count)]
        self.time = 0.0
        self._bg_key: tuple | None = None
        self._bg: pygame.Surface | None = None

    def update(self, dt: float) -> None:
        self.time += dt
        for o in self.orbs:
            o["x"] = (o["x"] + o["vx"] * dt) % 1.0
            o["y"] = (o["y"] + o["vy"] * dt) % 1.0

    def _build_background(self, w: int, h: int) -> pygame.Surface:
        bg = draw.vertical_gradient(w, h, theme.BG_TOP, theme.BG_BOTTOM).copy()
        grid = max(24, int(48 * theme.get_scale()))
        line = (26, 34, 70)
        for x in range(0, w, grid):
            pygame.draw.line(bg, line, (x, 0), (x, h))
        for y in range(0, h, grid):
            pygame.draw.line(bg, line, (0, y), (w, y))
        return bg

    def draw(self, surface: pygame.Surface) -> None:
        w, h = surface.get_size()
        key = (w, h, round(theme.get_scale(), 2))
        if self._bg_key != key or self._bg is None:
            self._bg = self._build_background(w, h)
            self._bg_key = key
        surface.blit(self._bg, (0, 0))
        for o in self.orbs:
            draw.draw_glow(surface, (o["x"] * w, o["y"] * h), o["r"] * min(w, h) * 1.6, o["c"], o["a"])
