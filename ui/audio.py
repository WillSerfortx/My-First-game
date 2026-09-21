"""Procedurally generated sound effects (no audio files required).

If the mixer or NumPy synthesis is unavailable every call silently does nothing.
"""
from __future__ import annotations

import math

import numpy as np
import pygame

SAMPLE_RATE = 22050


def _tone(freq: float, dur: float, vol: float = 0.4, kind: str = "sine",
          slide: float = 0.0, decay: float = 6.0) -> np.ndarray:
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    f = freq + slide * (t / dur)
    phase = 2 * np.pi * np.cumsum(f) / SAMPLE_RATE
    if kind == "square":
        wave = np.sign(np.sin(phase)) * 0.6
    elif kind == "saw":
        wave = 2 * ((phase / (2 * np.pi)) % 1.0) - 1.0
    else:
        wave = np.sin(phase)
    env = np.exp(-decay * t / dur) * np.minimum(1.0, t / 0.004)
    return wave * env * vol


def _seq(parts: list[tuple[float, np.ndarray]], total: float) -> np.ndarray:
    out = np.zeros(int(SAMPLE_RATE * total))
    for start, snd in parts:
        i = int(start * SAMPLE_RATE)
        j = min(out.size, i + snd.size)
        if j > i:
            out[i:j] += snd[: j - i]
    return out


def _synthesize() -> dict[str, np.ndarray]:
    rng = np.random.default_rng(3)
    sounds: dict[str, np.ndarray] = {}
    sounds["click"] = _tone(1300, 0.05, 0.55, decay=5)
    ticks = [(i * 0.055 + rng.random() * 0.02,
              _tone(700 + rng.random() * 900, 0.03, 0.8, "square", decay=3)) for i in range(9)]
    sounds["dice"] = _seq(ticks, 0.62)
    sounds["move"] = _tone(520, 0.07, 0.5, decay=4)
    sounds["ladder"] = _seq([(i * 0.09, _tone(f, 0.16, 0.3, decay=4))
                             for i, f in enumerate((440, 554, 659, 880))], 0.55)
    sounds["snake"] = _tone(520, 0.6, 0.3, "saw", slide=-380, decay=3)
    shimmer = _tone(880, 0.5, 0.22, decay=3) + _tone(1320, 0.5, 0.16, decay=4)
    sounds["shield"] = shimmer * (0.7 + 0.3 * np.sin(np.linspace(0, 40, shimmer.size)))
    sounds["ai"] = _seq([(0, _tone(660, 0.09, 0.25)), (0.1, _tone(990, 0.12, 0.25))], 0.25)
    sounds["victory"] = _seq([(i * 0.13, _tone(f, 0.35, 0.3, decay=3))
                              for i, f in enumerate((523, 659, 784, 1046, 784, 1046, 1318))], 1.2)
    return sounds


class AudioManager:
    """Loads generated sounds; ``play`` is always safe to call."""

    def __init__(self) -> None:
        self.enabled = True
        self.available = False
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2)
            for name, wave in _synthesize().items():
                data = np.clip(wave, -1.0, 1.0)
                pcm = (np.column_stack([data, data]) * 32767).astype(np.int16)
                self._sounds[name] = pygame.sndarray.make_sound(np.ascontiguousarray(pcm))
            self.available = True
        except Exception:
            self.available = False

    def play(self, name: str, volume: float = 0.6) -> None:
        if not (self.enabled and self.available):
            return
        try:
            snd = self._sounds.get(name)
            if snd is not None:
                snd.set_volume(volume)
                snd.play()
        except Exception:
            pass

    def toggle(self) -> bool:
        self.enabled = not self.enabled
        return self.enabled
