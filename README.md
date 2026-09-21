# AI-Powered Snake & Ladder

> 🎮 **[PLAY LIVE ONLINE DIRECTLY IN BROWSER](https://willserfortx.github.io/My-First-game/)** (No download or installation required!)
>
> 📹 **[Watch Gameplay Demo Video](assets/demo.mov)**

**Strategic Gameplay with Intelligent Decision-Making** - an authentic AI board game powered by
four AI / search / machine-learning techniques: **BFS, A\*, Logistic Regression and K-Means**.
Play directly online in your browser via GitHub Pages or run locally in Python (Pygame).

## Description

**The traditional problem.** In classic Snake & Ladder the dice decide everything - there is no
decision to make. This project turns the game into a strategy problem:

* **Dual dice** - every turn two dice are rolled and the player chooses *one* of the two values.
  Exact finish is required: a die that would overshoot cell 100 cannot be played (if neither die is
  playable the turn is skipped).
* **Shields** - each player owns **2 shields**. When a move ends on a snake head the player may spend a
  shield to block the snake; the piece then stays on the snake-head cell. The human is asked (with an
  AI advisor hint); the AI decides by itself and explains why.
* **Graph-based board** - the 10x10 board (10 snakes, 9 ladders, boustrophedon numbering) is a directed
  graph with an adjacency list (`Board.graph[cell]`); snake/ladder redirections are baked into the edges
  and shared by BFS, A*, feature extraction and the simulator.
* **Transparent AI** - the AI Analysis panel shows both candidate moves, their A* score, Logistic
  Regression win probability, K-Means risk zone and final weighted score, then announces its choice.

## AI techniques (four)

### BFS - shortest path analysis
`ai/bfs.py`. BFS runs from **every** cell to cell 100 over the board graph and stores
`min_rolls[cell]` (best case, snakes and ladders included; cell 1 needs 7 rolls on the default board).
It is displayed in the UI ("Minimum Rolls to Goal"), can be drawn as a route on the board (`P`), and
serves as the heuristic for A*.

### A\* - strategic candidate evaluation
`ai/astar.py`. For each candidate destination A* searches the *safest fast route* to cell 100:
routes may not land on snake heads and each step costs `1 + snakes_within_6(next cell) / 6`
(one roll plus the chance the next roll meets a snake). The heuristic is the BFS table, which is
admissible and consistent. The route cost is normalised to `0.0 - 1.0` (`1 - cost / max_cost`,
goal = 1.0); higher is better.

### Logistic Regression - win-probability prediction
`ai/data_generator.py`, `ai/logistic_model.py`. **10,000 random games** (two random players using the
real rules) are simulated. Every visited cell yields five features:

| feature | meaning |
|---|---|
| `dist_to_snake` | cells to the nearest snake head ahead (capped at 12) |
| `dist_to_ladder` | cells to the nearest ladder bottom ahead (capped at 12) |
| `snakes_within_6` | snake heads within one die roll ahead |
| `ladders_within_6` | ladder bottoms within one die roll ahead |
| `position_pct` | board progress, 0-100 |

The label is `won = 1` if that player eventually won the game, else `0`. A scikit-learn pipeline
(`StandardScaler` + `LogisticRegression`) is trained on 80 % of the *games* and evaluated on the unseen
20 %; the AI Lab shows accuracy, majority baseline, ROC AUC, precision/recall/F1, the confusion matrix
and probability examples - all calculated, none invented. Because both players in the simulation act
randomly, the labels are noisy and accuracy is modest by nature; the model is still a genuine, trained
predictor whose probability rises with progress and falls near snakes.

### K-Means - risk-zone clustering and heat-map
`ai/kmeans_model.py`. K-Means with **K = 3** clusters the 100 cells on their five (standardised)
features. Clusters are named from measured properties: every cell gets
`hazard = (snakes_within_6 - ladders_within_6) + (1/dist_to_snake - 1/dist_to_ladder)`; clusters are
ranked by mean hazard -> **DANGER** (highest), **SAFE**, **ADVANTAGE** (lowest). K-Means provides the
risk heat-map (`H` in game, AI Lab screen) and the risk zone shown next to every candidate. It is
analytical information only and is *not* part of the score.

### Final decision
```
final_score = 0.60 * A*_score + 0.40 * logistic_win_probability
```
The AI plays the die with the higher score. Two rules sit around the formula: a die that overshoots is
illegal, and a die that reaches cell 100 is played immediately. Shield use: the AI compares the benefit of
keeping the snake-head cell (same 60/40 blend) with a reserve threshold that is higher when fewer shields
remain and halves in the end-game (cells >= 75).

## Training pipeline
```
data generation -> feature extraction -> training dataset -> Logistic Regression -> K-Means
                -> saved models / cached results -> game AI
```
The pipeline runs once in a background thread while the menu is shown, then everything is cached in
`data/` (`training_data.npz`, `models.pkl`, plus a readable `training_sample.csv`). The cache is
invalidated automatically when the board layout or pipeline version changes. Individual moves only do
table look-ups, so the game stays responsive.

## Architecture
```
ai_snake_ladder/
|-- main.py                 entry point
|-- game/                   pure game logic (no UI, no AI)
|   |-- constants.py  board.py  player.py  dice.py  rules.py  game_engine.py
|-- ai/                     search + machine learning
|   |-- bfs.py  astar.py  features.py  data_generator.py
|   |-- logistic_model.py  kmeans_model.py  pipeline.py  decision_engine.py
|-- ui/                     Pygame interface
|   |-- app.py              window, resize handling, background AI loading, main loop
|   |-- screens.py          Home, How It Works, AI Lab
|   |-- game_screen.py      in-game screen and turn state machine
|   |-- board_renderer.py   board, curved snakes, ladders, tokens, overlays
|   |-- widgets.py          Button, Panel, Card, ProgressBar, DiceWidget, StatCard, EventLog,
|   |                       HeatmapCell, DecisionScoreBar, StatusBadge, Tooltip, Modal, Toast, MiniChart
|   |-- animations.py  particles.py  audio.py  draw.py  theme.py
|-- assets/  data/  tests/
```
Design rules: game logic never imports the UI; the UI never contains AI maths; animation is
delta-time based; expensive surfaces (gradients, glows, panels, text) are cached.

## Installation
Python 3.11 or newer.
```bash
python -m venv venv
# Windows:  venv\Scripts\activate        macOS / Linux:  source venv/bin/activate
pip install -r requirements.txt
```
Run:
```bash
python main.py
```
The first launch trains the AI (a few seconds); later launches load the cache instantly.

## Controls
| key | action |
|---|---|
| `SPACE` / `ENTER` | roll dice |
| `1` / `2` or click | choose die 1 / 2 (hover a die to preview its destination) |
| `Y` / `N` | use / decline a shield |
| `H` | K-Means risk heat-map on the board |
| `P` | BFS route overlay |
| `M` | sound on / off |
| `F11` | fullscreen |
| `ESC` | pause / back |

The window is resizable; the layout is scaled proportionally and letter-boxed for extreme aspect ratios.
Sound effects are generated in code (no audio files) and the game runs silently if no audio device exists.
Fonts and images fall back gracefully when unavailable.

## Testing
```bash
pytest
```
Covers the board graph, movement/snakes/ladders/overshoot/win, BFS, A*, features, both ML models, the
decision engine, shields, turn alternation, and a headless end-to-end UI smoke test (SDL dummy driver).
