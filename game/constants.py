"""Global constants for the Snake & Ladder rules and the AI feature window."""
from __future__ import annotations

BOARD_SIZE = 10                  # cells per side
NUM_CELLS = BOARD_SIZE * BOARD_SIZE
START_CELL = 1
GOAL_CELL = NUM_CELLS
DICE_SIDES = 6
SHIELDS_PER_PLAYER = 2

# head -> tail (moves the player DOWN)
SNAKES: dict[int, int] = {
    16: 6, 47: 26, 49: 11, 56: 53, 62: 19,
    64: 60, 87: 24, 93: 73, 95: 75, 98: 78,
}
# bottom -> top (moves the player UP)
LADDERS: dict[int, int] = {
    2: 38, 4: 14, 9: 31, 21: 42, 28: 84,
    36: 44, 51: 67, 71: 91, 80: 100,
}

# Feature-engineering window: "within 6" = one die roll ahead,
# distances are capped at two rolls (12 cells) because anything further away
# is not tactically relevant to the next move.
NEAR_WINDOW = DICE_SIDES
DIST_CAP = 2 * DICE_SIDES

# Training pipeline
SIMULATED_GAMES = 10_000
SIMULATION_SEED = 42
KMEANS_CLUSTERS = 3
