"""Player state."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .constants import SHIELDS_PER_PLAYER, START_CELL


class PlayerId(Enum):
    HUMAN = "Human"
    AI = "AI"

    @property
    def other(self) -> "PlayerId":
        return PlayerId.AI if self is PlayerId.HUMAN else PlayerId.HUMAN


@dataclass
class Player:
    pid: PlayerId
    position: int = START_CELL
    shields: int = SHIELDS_PER_PLAYER
    snakes_hit: int = 0
    ladders_hit: int = 0
    shields_used: int = 0
    turns: int = 0

    @property
    def name(self) -> str:
        return self.pid.value
