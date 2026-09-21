"""
Audio Manager module for AI-Powered Snake & Ladder.
Procedurally synthesizes crisp 16-bit PCM sound effects in memory using Python's standard wave library.
Zero external audio files required. Completely fault-tolerant and crash-proof.
"""

import io
import wave
import math
import struct
from typing import Dict, Optional
import pygame


class AudioManager:
    """
    Manages procedural sound effect synthesis and playback.
    """

    SAMPLE_RATE = 22050

    def __init__(self, enabled: bool = True):
        self.enabled: bool = enabled
        self.initialized: bool = False
        self.sounds: Dict[str, pygame.mixer.Sound] = {}

        self._init_mixer()
        if self.initialized and self.enabled:
            self._generate_all_sounds()

    def _init_mixer(self) -> None:
        """Initializes Pygame mixer safely."""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=self.SAMPLE_RATE, size=-16, channels=2, buffer=512)
            self.initialized = True
        except Exception:
            self.initialized = False

    def _create_wav_sound(self, sample_generator) -> Optional[pygame.mixer.Sound]:
        """Encodes procedural sample float generator [-1.0, 1.0] into a WAV Sound object."""
        if not self.initialized:
            return None

        bio = io.BytesIO()
        try:
            with wave.open(bio, "wb") as wf:
                wf.setnchannels(1)  # Mono
                wf.setsampwidth(2)   # 16-bit
                wf.setframerate(self.SAMPLE_RATE)
                frames = bytearray()

                for s in sample_generator:
                    val = max(-1.0, min(1.0, s))
                    ival = int(val * 32767)
                    frames.extend(struct.pack("<h", ival))

                wf.writeframes(frames)

            bio.seek(0)
            return pygame.mixer.Sound(bio)
        except Exception:
            return None

    def _generate_all_sounds(self) -> None:
        """Procedurally synthesizes all game sound effects."""
        # 1. Button Click (800Hz snap)
        def click_samples():
            duration = 0.04
            total_samples = int(duration * self.SAMPLE_RATE)
            for i in range(total_samples):
                t = i / self.SAMPLE_RATE
                env = 1.0 - (i / total_samples)
                yield math.sin(2 * math.pi * 880 * t) * env * 0.3

        # 2. Dice Roll Tumble (fluttering clicks)
        def dice_samples():
            duration = 0.08
            total_samples = int(duration * self.SAMPLE_RATE)
            for i in range(total_samples):
                t = i / self.SAMPLE_RATE
                freq = 300 + 400 * math.sin(2 * math.pi * 35 * t)
                env = math.exp(-i / (total_samples * 0.4))
                yield math.sin(2 * math.pi * freq * t) * env * 0.35

        # 3. Move Hop (440Hz bell)
        def move_samples():
            duration = 0.06
            total_samples = int(duration * self.SAMPLE_RATE)
            for i in range(total_samples):
                t = i / self.SAMPLE_RATE
                env = 1.0 - (i / total_samples)
                yield math.sin(2 * math.pi * 520 * t) * env * 0.3

        # 4. Ladder Climb (C5 - E5 - G5 ascending arpeggio)
        def ladder_samples():
            duration = 0.3
            total_samples = int(duration * self.SAMPLE_RATE)
            freqs = [523.25, 659.25, 783.99]
            for i in range(total_samples):
                idx = min(2, int((i / total_samples) * 3))
                f = freqs[idx]
                t = i / self.SAMPLE_RATE
                env = 1.0 - (i / total_samples)
                yield math.sin(2 * math.pi * f * t) * env * 0.4

        # 5. Snake Slide (descending hiss-like swoop)
        def snake_samples():
            duration = 0.35
            total_samples = int(duration * self.SAMPLE_RATE)
            for i in range(total_samples):
                frac = i / total_samples
                f = 500.0 - 320.0 * frac
                t = i / self.SAMPLE_RATE
                env = math.sin(frac * math.pi)
                yield math.sin(2 * math.pi * f * t) * env * 0.35

        # 6. Shield Block (Metallic harmonic clang)
        def shield_samples():
            duration = 0.25
            total_samples = int(duration * self.SAMPLE_RATE)
            for i in range(total_samples):
                t = i / self.SAMPLE_RATE
                env = math.exp(-i / (total_samples * 0.25))
                tone1 = math.sin(2 * math.pi * 600 * t)
                tone2 = math.sin(2 * math.pi * 1240 * t) * 0.5
                yield (tone1 + tone2) * env * 0.4

        # 7. Victory Fanfare (Celebratory chord)
        def victory_samples():
            duration = 0.6
            total_samples = int(duration * self.SAMPLE_RATE)
            chord = [523.25, 659.25, 783.99, 1046.50]
            for i in range(total_samples):
                t = i / self.SAMPLE_RATE
                env = 1.0 - (i / total_samples)
                val = sum(math.sin(2 * math.pi * f * t) for f in chord) / len(chord)
                yield val * env * 0.45

        # Map sound objects
        sound_gens = {
            "click": click_samples,
            "dice": dice_samples,
            "move": move_samples,
            "ladder": ladder_samples,
            "snake": snake_samples,
            "shield": shield_samples,
            "victory": victory_samples,
        }

        for name, gen in sound_gens.items():
            snd = self._create_wav_sound(gen())
            if snd:
                self.sounds[name] = snd

    def play(self, name: str) -> None:
        """Plays sound effect safely."""
        if not self.enabled or not self.initialized:
            return
        snd = self.sounds.get(name)
        if snd:
            try:
                snd.play()
            except Exception:
                pass
