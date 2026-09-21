"""
Particle System module for AI-Powered Snake & Ladder.
Provides lightweight, tasteful visual particle effects:
- Ambient floating dust
- Dice roll spark bursts
- Ladder climb golden ascension sparkles
- Snake bite sizzles
- Shield activation shockwaves
- Victory fireworks
"""

import pygame
import random
import math
from typing import List, Tuple, Optional
from .theme import Theme


class Particle:
    """A single animated particle with velocity, color, life, and fade."""

    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        color: Tuple[int, int, int],
        life: float,
        size: float = 3.0,
        gravity: float = 0.0,
        shrink: bool = True,
    ):
        self.x: float = x
        self.y: float = y
        self.vx: float = vx
        self.vy: float = vy
        self.color: Tuple[int, int, int] = color
        self.life: float = life
        self.max_life: float = life
        self.size: float = size
        self.gravity: float = gravity
        self.shrink: bool = shrink

    def update(self, dt: float) -> bool:
        """Updates particle position and life. Returns True if alive."""
        self.life -= dt
        if self.life <= 0:
            return False

        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        return True

    def draw(self, surface: pygame.Surface) -> None:
        """Renders the particle with alpha fade."""
        alpha_factor = max(0.0, min(1.0, self.life / self.max_life))
        current_size = self.size * (alpha_factor if self.shrink else 1.0)
        if current_size < 1.0:
            return

        alpha = int(255 * alpha_factor)
        p_surf = pygame.Surface((int(current_size * 2 + 2), int(current_size * 2 + 2)), pygame.SRCALPHA)
        color_with_alpha = (self.color[0], self.color[1], self.color[2], alpha)
        pygame.draw.circle(p_surf, color_with_alpha, (int(current_size + 1), int(current_size + 1)), int(current_size))
        surface.blit(p_surf, (int(self.x - current_size), int(self.y - current_size)))


class Shockwave:
    """An expanding translucent circle for shield and impact bursts."""

    def __init__(
        self,
        x: float,
        y: float,
        color: Tuple[int, int, int],
        max_radius: float = 60.0,
        duration: float = 0.5,
    ):
        self.x: float = x
        self.y: float = y
        self.color: Tuple[int, int, int] = color
        self.max_radius: float = max_radius
        self.duration: float = duration
        self.timer: float = 0.0

    def update(self, dt: float) -> bool:
        self.timer += dt
        return self.timer < self.duration

    def draw(self, surface: pygame.Surface) -> None:
        frac = min(1.0, self.timer / self.duration)
        radius = int(self.max_radius * frac)
        alpha = int(220 * (1.0 - frac))
        if radius <= 1 or alpha <= 0:
            return

        surf = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
        c = (self.color[0], self.color[1], self.color[2], alpha)
        pygame.draw.circle(surf, c, (radius + 2, radius + 2), radius, width=3)
        surface.blit(surf, (int(self.x - radius - 2), int(self.y - radius - 2)))


class ParticleManager:
    """
    Manages pools of particles and shockwaves.
    """

    def __init__(self):
        self.particles: List[Particle] = []
        self.shockwaves: List[Shockwave] = []
        self.ambient_particles: List[Particle] = []
        self._init_ambient(1440, 900)

    def _init_ambient(self, width: int, height: int) -> None:
        """Initializes subtle ambient floating particles."""
        self.ambient_particles = []
        for _ in range(40):
            p = Particle(
                x=random.uniform(0, width),
                y=random.uniform(0, height),
                vx=random.uniform(-10, 10),
                vy=random.uniform(-15, -5),
                color=(random.choice([(99, 102, 241), (6, 182, 212), (168, 85, 247)])),
                life=random.uniform(4.0, 10.0),
                size=random.uniform(1.0, 2.5),
                shrink=False,
            )
            self.ambient_particles.append(p)

    def emit_dice_burst(self, pos: Tuple[float, float]) -> None:
        """Emits spark burst when dice is rolled or selected."""
        for _ in range(16):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(50, 140)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            color = random.choice([Theme.AMBER_SHIELD, (254, 240, 138), Theme.CYAN_HUMAN])
            self.particles.append(
                Particle(pos[0], pos[1], vx, vy, color, life=random.uniform(0.3, 0.6), size=3.0, gravity=80.0)
            )

    def emit_ladder_sparkle(self, pos: Tuple[float, float]) -> None:
        """Emits ascending golden/green sparkles when ladder is climbed."""
        for _ in range(25):
            angle = random.uniform(-math.pi * 0.8, -math.pi * 0.2)
            speed = random.uniform(40, 160)
            color = random.choice([Theme.GREEN_LADDER, (167, 243, 208), (250, 204, 21)])
            self.particles.append(
                Particle(pos[0], pos[1], math.cos(angle) * speed, math.sin(angle) * speed, color, life=random.uniform(0.5, 0.9), size=3.5)
            )

    def emit_snake_sizzle(self, pos: Tuple[float, float]) -> None:
        """Emits red/purple sparks when sliding down snake."""
        for _ in range(20):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(30, 120)
            color = random.choice([Theme.RED_SNAKE, (254, 202, 202), (147, 51, 234)])
            self.particles.append(
                Particle(pos[0], pos[1], math.cos(angle) * speed, math.sin(angle) * speed, color, life=random.uniform(0.4, 0.7), size=3.0, gravity=100.0)
            )

    def emit_shield_shockwave(self, pos: Tuple[float, float]) -> None:
        """Emits golden shield forcefield shockwave."""
        self.shockwaves.append(Shockwave(pos[0], pos[1], color=Theme.AMBER_SHIELD, max_radius=80.0, duration=0.6))
        for _ in range(30):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(60, 180)
            self.particles.append(
                Particle(pos[0], pos[1], math.cos(angle) * speed, math.sin(angle) * speed, Theme.AMBER_SHIELD, life=random.uniform(0.4, 0.8), size=3.0)
            )

    def emit_victory_confetti(self, width: int, height: int) -> None:
        """Emits celebration confetti across top of screen."""
        for _ in range(60):
            x = random.uniform(0, width)
            vx = random.uniform(-40, 40)
            vy = random.uniform(60, 180)
            color = random.choice([
                Theme.CYAN_HUMAN,
                Theme.PURPLE_AI,
                Theme.AMBER_SHIELD,
                Theme.GREEN_LADDER,
                (236, 72, 153),
            ])
            self.particles.append(Particle(x, -10, vx, vy, color, life=random.uniform(2.5, 4.0), size=4.0, gravity=30.0))

    def update(self, dt: float, screen_size: Tuple[int, int]) -> None:
        """Updates all particle states and respawns ambient dust."""
        w, h = screen_size

        # Update event particles
        self.particles = [p for p in self.particles if p.update(dt)]
        self.shockwaves = [s for s in self.shockwaves if s.update(dt)]

        # Update ambient particles
        for p in self.ambient_particles:
            if not p.update(dt) or p.y < -10:
                p.x = random.uniform(0, w)
                p.y = h + 10
                p.life = random.uniform(5.0, 10.0)
                p.max_life = p.life

    def draw(self, surface: pygame.Surface) -> None:
        """Renders ambient dust, active shockwaves, and particle sparkles."""
        for p in self.ambient_particles:
            p.draw(surface)
        for s in self.shockwaves:
            s.draw(surface)
        for p in self.particles:
            p.draw(surface)
