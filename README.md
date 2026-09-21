# AI-Powered Snake & Ladder: Strategic Gameplay with Intelligent Decision-Making

A university AI Lab project integrating classical search algorithms and statistical machine learning into an intelligent, modern desktop board game. Built **100% in Python** using **Pygame**, **NumPy**, and **scikit-learn**.

---

## 🎬 Gameplay Demo

<p align="center">
  <video src="assets/demo.mov" width="100%" controls="controls"></video>
</p>

> 📹 **Watch Video:** If inline playback is not supported by your browser, you can [view or download the video directly](assets/demo.mov) or [download from Releases](https://github.com/WillSerfortx/ai_snake_ladder/releases/download/v1.0.0/Screen_Recording.mov).

---

## 1. Project Overview

Traditional Snake & Ladder is purely stochastic, offering zero player agency: dice rolls dictate every move deterministically until someone reaches cell 100.

**AI-Powered Snake & Ladder** transforms this classic children's game into an authentic **decision-making problem under uncertainty**:
1. **Dual-Dice Choice**: Every turn, two independent $d6$ dice are rolled. The active player must evaluate both outcomes and select one to execute.
2. **Shield Power-Ups**: Each player starts with **2 shields** that can be strategically deployed to block a snake and preserve board position.
3. **Directed Graph Board**: The 100-cell board is modeled as an adjacency-list directed graph with overshoot bounce-back mechanics.
4. **Transparent AI Decision Engine**: Rather than relying on black-box decisions, the AI analyzes both candidate dice in real time across four distinct AI techniques and displays its full quantitative evaluation to the player.

---

## 2. The Four AI / Search / ML Techniques

The system integrates four core AI methods:

```
                  ┌───────────────────────────────┐
                  │          DUAL DICE            │
                  │        (Dice 1, Dice 2)       │
                  └──────────────┬────────────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
          [ Candidate A ]                 [ Candidate B ]
                 │                               │
        ┌────────┴────────┐             ┌────────┴────────┐
        ▼                 ▼             ▼                 ▼
   A* Pathfinding    Logistic Reg    A* Pathfinding    Logistic Reg
    (60% Weight)     (40% Weight)     (60% Weight)     (40% Weight)
        │                 │             │                 │
        └────────┬────────┘             └────────┬────────┘
                 ▼                               ▼
          Final Score A                   Final Score B
                 │                               │
                 └───────────────┬───────────────┘
                                 ▼
                     Highest Score Selected
                     (With K-Means Risk Map &
                      Strategic Shield Evaluation)
```

### 1. BFS (Breadth-First Search) — Shortest Path Analysis
* **Implementation**: `ai/bfs.py`
* **Purpose**: Operates on the directed board graph (incorporating ladders and snakes) to calculate the exact minimum number of rolls required to reach cell 100 from every cell on the board ($1 \dots 100$).
* **Results**: Cell 100 requires $0$ rolls. Starting at Cell 1 requires approximately $7$ rolls under optimal conditions.
* **Role**: Serves as the precomputed admissible heuristic lookup table for A* search and provides strategic proximity data for game analytics.

### 2. A* Pathfinding — Strategic Candidate Evaluation
* **Implementation**: `ai/astar.py`
* **Purpose**: Evaluates candidate move destinations $s'$ using the cost function $f(s') = g(s') + h(s')$.
  * $g(s') = 1.0$ (step cost of one dice roll).
  * $h(s') = \text{min\_rolls}[s']$ (admissible BFS shortest path heuristic).
* **Normalized Score**: Produces an objective score in $[0.0, 1.0]$ based on heuristic distance to goal, board progress percentage, ladder capture rewards, and snake avoidance.

### 3. Logistic Regression — Win Probability Estimation
* **Implementation**: `ai/logistic_model.py`
* **Training Pipeline**: Trained on a dataset extracted from **10,000 simulated games** (`ai/data_generator.py`), capturing every visited cell and whether the player won ($1$) or lost ($0$).
* **The 5 Extracted Cell Features**:
  1. `dist_to_snake`: Forward distance to nearest snake head ahead.
  2. `dist_to_ladder`: Forward distance to nearest ladder base ahead.
  3. `snakes_within_6`: Count of snake heads in immediate roll range ($c+1 \dots c+6$).
  4. `ladders_within_6`: Count of ladder bases in immediate roll range ($c+1 \dots c+6$).
  5. `position_pct`: Cell progress as a board percentage ($c / 100.0$).
* **Output**: Calibrated win probability $P(\text{win} \mid \mathbf{x}) \in [0.0, 1.0]$. Real validation metrics (accuracy, confusion matrix, coefficients) are viewable in the AI Lab screen.

### 4. K-Means Clustering ($K=3$) — Strategic Risk Heatmap
* **Implementation**: `ai/kmeans_model.py`
* **Purpose**: Unsupervised clustering of all 100 cells across the 5 strategic features into $K=3$ distinct risk zones:
  * **Danger**: Characterized by high `snakes_within_6` and low `dist_to_snake`.
  * **Safe**: Stable transit zones with low immediate threat density.
  * **Advantage**: Characterized by high ladder opportunities and advanced board progress.
* **Analytical Visualization**: Renders an interactive 100-cell risk heatmap on both the game board and the dedicated AI Lab analytics dashboard.

---

## 3. The AI Decision Engine Formula

For candidate moves $A$ and $B$, the AI evaluates both states using the weighted formula:

$$\text{final\_score} = 0.60 \times \text{astar\_score} + 0.40 \times \text{logistic\_probability}$$

The candidate with the higher score is automatically executed. 

### Strategic Shield Decision
If the chosen move lands on a snake head, the AI calculates the position loss:

$$\Delta_{\text{loss}} = \text{snake\_head} - \text{snake\_tail}$$

If $\Delta_{\text{loss}} \ge 15$ cells or the game is in the endgame ($\text{cell} \ge 65$) and shields remain, the AI expends 1 shield to neutralize the snake and hold its position.

---

## 4. Visual Design & User Interface

* **Dark Glassmorphism Theme**: Cyber navy background (`#0B0F19`), translucent elevated panels, and glowing neon accents.
* **Player Styling**:
  * **Human**: Electric Cyan (`#06B6D4`)
  * **AI**: Cyber Purple (`#A855F7`)
* **Dynamic Animations**:
  * Alternating boustrophedon 10x10 board with curved sinusoidal snake bodies and perspective glowing ladders.
  * Cell-by-cell smooth token interpolation with trail effects.
  * 3D pip dice widgets with rotational roll physics.
  * Real-time score comparison bars.
* **Procedural Sound**: Audio is synthesized dynamically in memory using Python's standard `wave` library—no external audio files required.

---

## 5. Project Architecture

```
my_snake_and_ladders/
├── main.py                     # Window management & 60 FPS main loop
├── requirements.txt            # Project dependencies
├── README.md                   # University documentation
│
├── game/
│   ├── __init__.py
│   ├── board.py                # 10x10 grid, 10 snakes, 9 ladders, directed graph
│   ├── player.py               # Player state, shields, animation path interpolation
│   ├── dice.py                 # Dual-dice roll mechanics, physics, and pip maps
│   ├── rules.py                # Overshoot bounce, ladder/snake, shield logic
│   └── game_engine.py          # State machine, turns, and event logging
│
├── ai/
│   ├── __init__.py
│   ├── bfs.py                  # BFS shortest path & min rolls lookup table
│   ├── astar.py                # A* state scoring (0.0 - 1.0)
│   ├── features.py             # 5 cell features extractor
│   ├── data_generator.py       # 10,000 game simulation pipeline
│   ├── logistic_model.py       # Logistic Regression win probability predictor
│   ├── kmeans_model.py         # K-Means (K=3) risk clustering & heatmap
│   └── decision_engine.py      # Dual candidate evaluation & 60/40 weighted formula
│
├── ui/
│   ├── __init__.py
│   ├── theme.py                # Dark glassmorphism palette, fonts, glow utilities
│   ├── widgets.py              # Button, Card, Dice, Shield, ScoreBar, EventLog, Modal
│   ├── board_renderer.py       # Board graphics, curved snakes, glowing ladders, tokens
│   ├── particles.py            # Ambient dust, roll sparks, ladder/snake/shield VFX
│   ├── audio.py                # Procedural 16-bit PCM sound synthesizer
│   └── screens.py              # HomeScreen, GameScreen, AnalyticsScreen (AI Lab)
│
├── data/                       # Cached training datasets and model weights
│
└── tests/
    ├── __init__.py
    ├── test_board.py           # Board, snakes, ladders, coordinates
    ├── test_bfs.py             # BFS reachable paths and min rolls
    ├── test_astar.py           # A* candidate scoring
    ├── test_features.py        # 5 feature extraction bounds
    ├── test_models.py          # Logistic Regression & K-Means
    ├── test_game_rules.py      # Movement, bounce-back, shields, win detection
    └── test_algorithm_compliance.py  # Strictly verifies the 4 required AI models
```

---

## 6. Installation & Execution

### Prerequisites
* Python 3.11+
* Standard C build tools (for Pygame if compiling from source)

### Setup
```bash
# 1. Create a virtual environment
python3 -m venv venv

# 2. Activate virtual environment
# On macOS / Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# 3. Install required packages
pip install -r requirements.txt
```

### Run the Game
```bash
python3 main.py
```

*On the very first run, the system automatically simulates 10,000 games and trains the Logistic Regression and K-Means models in ~2 seconds, caching the results to `data/` for instant subsequent startups.*

---

## 7. Running the Test Suite

Execute all automated unit and integration tests using `pytest`:

```bash
pytest tests/ -v
```

All 7 test suites validate board construction, BFS paths, A* scores, 5-feature dimensions, model training, game rules, and strict algorithm compliance.
