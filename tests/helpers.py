"""Shared, cached test fixtures (built once per test session)."""
from __future__ import annotations

import tempfile
from functools import lru_cache
from pathlib import Path

from ai.pipeline import AIBundle, build_ai
from game.board import Board


@lru_cache(maxsize=1)
def get_board() -> Board:
    return Board()


@lru_cache(maxsize=1)
def get_small_bundle() -> AIBundle:
    """A quickly trained AI (1,500 games) that never touches the real cache."""
    tmp = Path(tempfile.mkdtemp(prefix="snl_test_"))
    return build_ai(get_board(), data_dir=tmp, n_games=1500, seed=7)
