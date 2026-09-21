"""AI-Powered Snake & Ladder - desktop application entry point (Pygame)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ui.app import App  # noqa: E402


def main() -> None:
    App().run()


if __name__ == "__main__":
    main()
