"""Delta-time based animation primitives (frame-rate independent)."""
from __future__ import annotations

import math
from typing import Callable, Sequence

Easing = Callable[[float], float]


# ------------------------------------------------------------------ easings
def linear(t: float) -> float:
    return t


def ease_out_cubic(t: float) -> float:
    return 1.0 - (1.0 - t) ** 3


def ease_in_cubic(t: float) -> float:
    return t ** 3


def ease_in_out_cubic(t: float) -> float:
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_out_back(t: float) -> float:
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def ease_out_bounce(t: float) -> float:
    n1, d1 = 7.5625, 2.75
    if t < 1 / d1:
        return n1 * t * t
    if t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    if t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    t -= 2.625 / d1
    return n1 * t * t + 0.984375


def clamp01(t: float) -> float:
    return max(0.0, min(1.0, t))


# ------------------------------------------------------------------- tween
class Tween:
    """value(t) from ``start`` to ``end`` over ``duration`` seconds (after ``delay``)."""

    def __init__(self, start: float = 0.0, end: float = 1.0, duration: float = 0.4,
                 easing: Easing = ease_out_cubic, delay: float = 0.0) -> None:
        self.start, self.end, self.duration = start, end, max(1e-6, duration)
        self.easing, self.delay = easing, delay
        self.elapsed = 0.0

    def restart(self, start: float | None = None, end: float | None = None,
                delay: float | None = None) -> None:
        if start is not None:
            self.start = start
        if end is not None:
            self.end = end
        if delay is not None:
            self.delay = delay
        self.elapsed = 0.0

    def update(self, dt: float) -> None:
        self.elapsed += dt

    @property
    def progress(self) -> float:
        return clamp01((self.elapsed - self.delay) / self.duration)

    @property
    def finished(self) -> bool:
        return self.elapsed - self.delay >= self.duration

    @property
    def value(self) -> float:
        return self.start + (self.end - self.start) * self.easing(self.progress)


class SmoothValue:
    """Exponentially smoothed value (hover glows, animated bars...)."""

    def __init__(self, value: float = 0.0, speed: float = 10.0) -> None:
        self.value = value
        self.target = value
        self.speed = speed

    def set(self, target: float, snap: bool = False) -> None:
        self.target = target
        if snap:
            self.value = target

    def update(self, dt: float) -> None:
        # exact solution of dv/dt = speed * (target - v): independent of frame rate
        k = 1.0 - math.exp(-self.speed * dt)
        self.value += (self.target - self.value) * k
        if abs(self.target - self.value) < 1e-4:
            self.value = self.target


class Timer:
    """Simple countdown."""

    def __init__(self, duration: float = 0.0) -> None:
        self.remaining = duration

    def start(self, duration: float) -> None:
        self.remaining = duration

    def update(self, dt: float) -> bool:
        """Advance; returns True once (on the frame it expires)."""
        if self.remaining <= 0:
            return False
        self.remaining -= dt
        return self.remaining <= 0

    @property
    def active(self) -> bool:
        return self.remaining > 0


def pulse(t: float, speed: float = 2.0, low: float = 0.0, high: float = 1.0) -> float:
    """Smooth 0..1 oscillation mapped to [low, high]."""
    return low + (high - low) * (0.5 + 0.5 * math.sin(t * speed * math.tau))


# ----------------------------------------------------------- path helpers
def polyline_length(points: Sequence[tuple[float, float]]) -> float:
    return sum(math.dist(points[i], points[i + 1]) for i in range(len(points) - 1))


def polyline_point(points: Sequence[tuple[float, float]], t: float) -> tuple[float, float]:
    """Point at fraction ``t`` (by arc length) along a polyline."""
    if not points:
        return (0.0, 0.0)
    if len(points) == 1 or t <= 0:
        return points[0]
    if t >= 1:
        return points[-1]
    total = polyline_length(points)
    if total <= 0:
        return points[0]
    target = t * total
    walked = 0.0
    for i in range(len(points) - 1):
        seg = math.dist(points[i], points[i + 1])
        if walked + seg >= target and seg > 0:
            f = (target - walked) / seg
            return (points[i][0] + (points[i + 1][0] - points[i][0]) * f,
                    points[i][1] + (points[i + 1][1] - points[i][1]) * f)
        walked += seg
    return points[-1]
