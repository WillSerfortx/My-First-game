"""Menu-style screens: Home, How It Works and the AI Lab analytics dashboard."""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from ai.features import FEATURE_DESCRIPTIONS, FEATURE_NAMES
from game.board import Board
from game.constants import NUM_CELLS

from . import draw, theme
from .animations import Tween, ease_out_cubic
from .game_screen import GameScreen  # noqa: F401  (re-exported for convenience)
from .theme import S, fonts
from .widgets import (Button, Card, HeatmapCell, Panel, ProgressBar, StatusBadge, Tooltip, fitted_font,
                      mouse_pos)

if TYPE_CHECKING:  # pragma: no cover
    from .app import App


def _screen_header(surface: pygame.Surface, vp: pygame.Rect, title: str, subtitle: str,
                   back: Button) -> pygame.Rect:
    m = S(18)
    draw.draw_text(surface, title, fonts.get(28, True), theme.CYAN, (vp.x + m + S(2), vp.y + S(10)))
    draw.draw_text(surface, title, fonts.get(28, True), (245, 250, 255), (vp.x + m, vp.y + S(8)), shadow=True)
    draw.draw_text(surface, subtitle, fonts.get(11.5, True), theme.TEXT_DIM, (vp.x + m + S(3), vp.y + S(44)))
    back.rect = pygame.Rect(vp.right - m - S(130), vp.y + S(14), S(130), S(36))
    back.draw(surface)
    return pygame.Rect(vp.x + m, vp.y + S(64), vp.w - 2 * m, vp.h - S(64) - m)


# ======================================================================== Home
class HomeScreen:
    """Animated landing screen."""

    def __init__(self, app: "App") -> None:
        self.app = app
        self.time = 0.0
        self.intro = Tween(0.0, 1.0, 1.1, ease_out_cubic)
        self.buttons = [
            Button("START GAME", self._start, "primary", 20),
            Button("AI LAB", lambda: self._go("lab"), "secondary", 18),
            Button("HOW IT WORKS", lambda: self._go("how"), "secondary", 18),
            Button("QUIT", self._quit, "danger", 18),
        ]
        self.load_bar = ProgressBar(theme.CYAN, 3.0)

    def on_enter(self) -> None:
        self.intro.restart()

    def _start(self) -> None:
        self.app.audio.play("click")
        if self.app.loader.ready:
            self.app.start_game()
        elif self.app.loader.error:
            self.app.toasts.push("AI could not be prepared - see the message below", theme.RED)
        else:
            self.app.toasts.push("The AI is still training - one moment...", theme.GOLD)

    def _go(self, name: str) -> None:
        self.app.audio.play("click")
        self.app.goto(name)

    def _quit(self) -> None:
        self.app.audio.play("click")
        self.app.quit()

    def handle_event(self, event: pygame.event.Event) -> None:
        for b in self.buttons:
            b.handle_event(event)
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self._start()

    def update(self, dt: float) -> None:
        self.time += dt
        self.intro.update(dt)
        for b in self.buttons:
            b.update(dt)
        self.load_bar.set(self.app.loader.progress)
        self.load_bar.update(dt)
        self.buttons[0].enabled = True

    def draw(self, surface: pygame.Surface, vp: pygame.Rect) -> None:
        e = self.intro.value
        cx = vp.centerx
        slide = int((1 - e) * S(30))
        f_small = fonts.get(22, True)
        spaced = " ".join("AI-POWERED")
        draw.draw_text(surface, spaced, f_small, theme.CYAN, (cx, vp.y + S(112) + slide), "midtop", shadow=True)
        title = "SNAKE & LADDER"
        f_title = fitted_font(title, int(vp.w * 0.86), 96, True, 30)
        y = vp.y + S(150) + slide
        for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3), (-2, 2), (2, -2)):
            draw.draw_text(surface, title, f_title, draw.with_alpha(theme.MAGENTA, 90),
                           (cx + dx * theme.get_scale() * 1.5, y + dy * theme.get_scale() * 1.5), "midtop")
        draw.draw_text(surface, title, f_title, (246, 248, 255), (cx, y), "midtop", shadow=True)
        sy = y + f_title.get_height() + S(6)
        draw.draw_text(surface, "Strategic Gameplay", fonts.get(24), theme.TEXT, (cx, sy), "midtop")
        draw.draw_text(surface, "with Intelligent Decision-Making", fonts.get(18), theme.TEXT_DIM,
                       (cx, sy + S(34)), "midtop")

        # decorative pawns
        for side, col, ph in ((-1, theme.HUMAN_COLOR, 0.0), (1, theme.AI_COLOR, 1.7)):
            px = cx + side * min(vp.w * 0.30, S(470))
            py = vp.y + S(255) + math.sin(self.time * 2.2 + ph) * S(8)
            draw.draw_pawn(surface, px, py, S(26), col, 170, lift=0.0)

        bw, bh, gap = S(340), S(58), S(16)
        by = vp.y + S(440)
        for i, b in enumerate(self.buttons):
            b.rect = pygame.Rect(cx - bw // 2, by + i * (bh + gap) + int((1 - e) * S(20) * (i + 1)), bw, bh)
            b.draw(surface)

        # four techniques (exactly four)
        chips = [("BFS", theme.CYAN), ("A*", theme.GOLD), ("LOGISTIC REGRESSION", theme.GREEN), ("K-MEANS", theme.MAGENTA)]
        widths = [fonts.get(11.5, True).size(t)[0] + S(34) for t, _ in chips]
        x = cx - (sum(widths) + S(10) * (len(chips) - 1)) // 2
        cy = by + 4 * (bh + gap) + S(6)
        for (text, col), w in zip(chips, widths):
            rect = StatusBadge.draw(surface, text, col, (x, cy), "topleft", self.time)
            x += rect.w + S(10)

        self._draw_ai_status(surface, vp)

    def _draw_ai_status(self, surface: pygame.Surface, vp: pygame.Rect) -> None:
        loader = self.app.loader
        cx = vp.centerx
        y = vp.bottom - S(58)
        f = fonts.get(13)
        if loader.error:
            draw.draw_text(surface, "AI unavailable: " + draw.ellipsize(f, loader.error, int(vp.w * 0.7)), f,
                           theme.RED, (cx, y), "midtop")
        elif loader.ready and loader.bundle:
            b = loader.bundle
            s = b.summary
            msg = (f"AI READY  -  Logistic Regression trained on {s.n_rows:,} cell visits from "
                   f"{s.n_games:,} simulated games ({b.source})")
            draw.draw_glow(surface, (cx - f.size(msg)[0] // 2 - S(14), y + S(8)), S(12), theme.GREEN, 150)
            pygame.draw.circle(surface, theme.GREEN, (cx - f.size(msg)[0] // 2 - S(14), y + S(8)), S(4))
            draw.draw_text(surface, msg, f, theme.TEXT_DIM, (cx, y), "midtop")
        else:
            draw.draw_text(surface, f"Preparing AI: {loader.message}", f, theme.TEXT_DIM, (cx, y), "midtop")
            bar = pygame.Rect(0, 0, min(S(420), vp.w // 2), S(8))
            bar.midtop = (cx, y + S(26))
            self.load_bar.draw(surface, bar)


# =================================================================== How it works
HOW_TOPICS = [
    ("DUAL DICE & SHIELDS", theme.CYAN, [
        "Every turn you roll two dice and choose ONE of the two values. Exact finish is required: a die that would overshoot cell 100 cannot be played.",
        "Each player owns 2 shields. Landing on a snake head lets you spend a shield: the snake is blocked and you keep the head cell.",
    ]),
    ("BFS - SHORTEST PATH", theme.BLUE, [
        "The board is a directed graph (cells 1-100). BFS runs from every cell to cell 100 and stores the minimum number of rolls, snakes and ladders included.",
        "The table gives strategic distance-to-goal and is also the admissible heuristic used by A*.",
    ]),
    ("A* - STRATEGIC EVALUATION", theme.GOLD, [
        "For each candidate destination A* searches the safest fast route to cell 100 (routes may not land on snake heads).",
        "Each step costs one roll plus the chance the next roll meets a snake. The route cost is normalised to a 0.0 - 1.0 score: higher is better.",
    ]),
    ("LOGISTIC REGRESSION", theme.GREEN, [
        "10,000 random games are simulated. Every visited cell yields 5 features: dist_to_snake, dist_to_ladder, snakes_within_6, ladders_within_6, position_pct.",
        "A real scikit-learn model learns the probability that a player standing on a cell goes on to win.",
    ]),
    ("K-MEANS - RISK ZONES", theme.MAGENTA, [
        "The same five features cluster the 100 cells into K = 3 groups. Clusters are named from their measured snake/ladder surroundings: DANGER, SAFE, ADVANTAGE.",
        "K-Means drives the risk heat-map and the zone shown next to each candidate; it is analytical information, not part of the score.",
    ]),
    ("THE AI DECISION", theme.ORANGE, [
        "final_score = 0.60 x A* score + 0.40 x Logistic Regression probability.",
        "The AI evaluates both dice, compares the two weighted scores and plays the higher one. Its shield choice weighs the benefit of keeping the snake-head cell against the value of saving the shield.",
    ]),
]


class HowItWorksScreen:
    def __init__(self, app: "App") -> None:
        self.app = app
        self.time = 0.0
        self.back = Button("BACK", lambda: app.goto("home"), "secondary", 14)
        self.panels = [Panel(t, c, 0.06 * i) for i, (t, c, _) in enumerate(HOW_TOPICS)]

    def on_enter(self) -> None:
        for i, p in enumerate(self.panels):
            p.replay(0.06 * i)

    def handle_event(self, event: pygame.event.Event) -> None:
        self.back.handle_event(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.goto("home")

    def update(self, dt: float) -> None:
        self.time += dt
        self.back.update(dt)
        for p in self.panels:
            p.update(dt)

    def draw(self, surface: pygame.Surface, vp: pygame.Rect) -> None:
        area = _screen_header(surface, vp, "HOW IT WORKS", "FOUR AI TECHNIQUES, ONE STRATEGIC OPPONENT", self.back)
        gap = S(14)
        cols, rows = 3, 2
        cw = (area.w - gap * (cols - 1)) // cols
        ch = (area.h - gap * (rows - 1)) // rows
        font = fonts.get(13.5)
        lh = font.get_linesize() + S(4)
        for i, ((title, color, paras), panel) in enumerate(zip(HOW_TOPICS, self.panels)):
            r, c = divmod(i, cols)
            rect = pygame.Rect(area.x + c * (cw + gap), area.y + r * (ch + gap), cw, ch)
            content = panel.draw_background(surface, rect)
            y = content.y
            for para in paras:
                for line in draw.wrap_text(font, para, content.w):
                    if y + lh > content.bottom:
                        break
                    draw.draw_text(surface, line, font, theme.TEXT if para.startswith("final_score") else theme.TEXT_DIM, (content.x, y))
                    y += lh
                y += S(8)
            panel.draw_veil(surface, rect)


# ========================================================================= AI Lab
class AILabScreen:
    """Analytics dashboard: risk heat-map, features, models, simulation and metrics."""

    def __init__(self, app: "App") -> None:
        self.app = app
        self.time = 0.0
        self.back = Button("BACK", lambda: app.goto("home"), "secondary", 14)
        self.panels = {k: Panel(t, c, d) for k, (t, c, d) in {
            "heat": ("CELL RISK HEATMAP  -  K-MEANS (K = 3)", theme.MAGENTA, 0.0),
            "profile": ("CLUSTER PROFILES  -  MEASURED FEATURE MEANS", theme.RED, 0.08),
            "models": ("MODEL INFORMATION", theme.CYAN, 0.04),
            "sim": ("SIMULATION & TRAINING DATA", theme.BLUE, 0.10),
            "features": ("FEATURE INFORMATION", theme.GOLD, 0.14),
            "perf": ("LOGISTIC REGRESSION PERFORMANCE", theme.GREEN, 0.18),
        }.items()}
        self.cells = {c: HeatmapCell(c) for c in range(1, NUM_CELLS + 1)}
        self.load_bar = ProgressBar(theme.CYAN, 3.0)

    def on_enter(self) -> None:
        for p in self.panels.values():
            p.replay(p.appear.delay)

    def handle_event(self, event: pygame.event.Event) -> None:
        self.back.handle_event(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.goto("home")

    def update(self, dt: float) -> None:
        self.time += dt
        self.back.update(dt)
        for p in self.panels.values():
            p.update(dt)
        if self.app.loader.ready:
            for c in self.cells.values():
                c.update(dt)
        self.load_bar.set(self.app.loader.progress)
        self.load_bar.update(dt)

    # ----------------------------------------------------------------- draw
    def draw(self, surface: pygame.Surface, vp: pygame.Rect) -> None:
        area = _screen_header(surface, vp, "AI LAB", "ANALYTICS  |  TRAINING PIPELINE  |  MODEL INTERNALS", self.back)
        bundle = self.app.bundle
        if bundle is None:
            self._draw_loading(surface, area)
            return
        gap = S(14)
        left_w = int(area.w * 0.42)
        left = pygame.Rect(area.x, area.y, left_w, area.h)
        right = pygame.Rect(left.right + gap, area.y, area.w - left_w - gap, area.h)
        heat_h = int(left.h * 0.70)
        rects = {
            "heat": pygame.Rect(left.x, left.y, left.w, heat_h),
            "profile": pygame.Rect(left.x, left.y + heat_h + gap, left.w, left.h - heat_h - gap),
        }
        r1 = int(right.h * 0.27)
        r2 = int(right.h * 0.29)
        mw = int(right.w * 0.56)
        rects["models"] = pygame.Rect(right.x, right.y, mw, r1)
        rects["sim"] = pygame.Rect(right.x + mw + gap, right.y, right.w - mw - gap, r1)
        rects["features"] = pygame.Rect(right.x, right.y + r1 + gap, right.w, r2)
        rects["perf"] = pygame.Rect(right.x, right.y + r1 + r2 + 2 * gap, right.w, right.h - r1 - r2 - 2 * gap)

        tooltip: tuple | None = None
        for key, rect in rects.items():
            panel = self.panels[key]
            content = panel.draw_background(surface, rect)
            fn = getattr(self, f"_draw_{key}")
            result = fn(surface, content)
            if result:
                tooltip = result
            panel.draw_veil(surface, rect)
        if tooltip:
            Tooltip.draw(surface, tooltip[0], mouse_pos(), tooltip[1], tooltip[2])

    def _draw_loading(self, surface: pygame.Surface, area: pygame.Rect) -> None:
        loader = self.app.loader
        rect = pygame.Rect(0, 0, min(S(560), area.w), S(170))
        rect.center = area.center
        panel = self.panels["heat"]
        c = panel.draw_background(surface, rect)
        if loader.error:
            draw.draw_text(surface, "The AI could not be prepared:", fonts.get(15, True), theme.RED, (c.centerx, c.y + S(16)), "midtop")
            f = fonts.get(13)
            draw.draw_text(surface, draw.ellipsize(f, loader.error, c.w), f, theme.TEXT_DIM, (c.centerx, c.y + S(46)), "midtop")
        else:
            draw.draw_text(surface, loader.message, fonts.get(15, True), theme.TEXT, (c.centerx, c.y + S(16)), "midtop")
            bar = pygame.Rect(c.x, c.y + S(60), c.w, S(10))
            self.load_bar.draw(surface, bar)

    # -- heatmap -------------------------------------------------------------
    def _draw_heat(self, surface: pygame.Surface, c: pygame.Rect):
        b = self.app.bundle
        cl = b.clusterer
        legend_h = S(34)
        side = max(S(40), min(c.w, c.h - legend_h - S(6)))
        gx, gy = c.x + (c.w - side) // 2, c.y
        cs = side / 10.0
        max_h = max(1e-6, max(abs(h) for h in cl.hazards))
        hover: tuple | None = None
        for cell, w in self.cells.items():
            row, col = Board.cell_to_grid(cell)
            w.rect = pygame.Rect(int(gx + col * cs), int(gy + (9 - row) * cs), int(cs) + 1, int(cs) + 1)
            zone = cl.zone_of(cell)
            marker = "snake" if cell in b.board.snakes else "ladder" if cell in b.board.ladders else None
            w.draw(surface, theme.ZONE_COLORS[zone], abs(cl.hazard_of(cell)) / max_h, marker)
        pos = mouse_pos()
        for cell, w in self.cells.items():
            if w.rect.collidepoint(pos):
                f = b.features.features_for(cell)
                an = self.app.decision_engine.analyze(cell)
                lines = [f"{name}: {f[i]:.0f}" if i < 4 else f"{name}: {f[i]:.0f}%" for i, name in enumerate(FEATURE_NAMES)]
                lines += [f"hazard {an.hazard:+.2f}   LR win {an.win_probability:.0%}",
                          f"A* {an.astar_score:.2f}   BFS {an.bfs_rolls} rolls"]
                hover = (lines, f"CELL {cell}  -  {an.zone}", theme.ZONE_COLORS[an.zone])
                break
        # legend
        y = c.bottom - legend_h // 2
        x = c.x
        for prof in cl.profiles:
            col = theme.ZONE_COLORS[prof.zone]
            r = StatusBadge.draw(surface, f"{prof.zone}  {prof.size} cells", col, (x, y), "midleft", self.time)
            x += r.w + S(10)
        draw.draw_chevron(surface, x + S(6), y, S(4), theme.RED, up=False, width=2)
        draw.draw_text(surface, "snake", fonts.get(11), theme.TEXT_DIM, (x + S(16), y), "midleft")
        x += S(60)
        draw.draw_chevron(surface, x + S(6), y, S(4), theme.GREEN, up=True, width=2)
        draw.draw_text(surface, "ladder", fonts.get(11), theme.TEXT_DIM, (x + S(16), y), "midleft")
        return hover

    # -- cluster profiles ------------------------------------------------------
    def _draw_profile(self, surface: pygame.Surface, c: pygame.Rect):
        cl = self.app.bundle.clusterer
        headers = ["ZONE", "CELLS", "d_snake", "d_ladder", "snk<=6", "lad<=6", "pos %", "hazard"]
        fr = [0.0, 0.20, 0.31, 0.43, 0.56, 0.68, 0.80, 0.91]
        hf, bf = fonts.get(10.5, True), fonts.get(12.5)
        row_h = max(S(20), (c.h - S(34)) // 3)
        for h, f in zip(headers, fr):
            draw.draw_text(surface, h, hf, theme.TEXT_DIM, (c.x + int(c.w * f), c.y + S(6)), "midleft")
        for i, prof in enumerate(cl.profiles):
            y = c.y + S(22) + i * row_h + row_h // 2
            col = theme.ZONE_COLORS[prof.zone]
            draw.fill_rrect(surface, pygame.Rect(c.x - S(4), y - row_h // 2 + 2, c.w + S(8), row_h - 4), draw.with_alpha(col, 22), S(6))
            StatusBadge.draw(surface, prof.zone, col, (c.x, y), "midleft", self.time, size=10.5)
            m = prof.means
            vals = [str(prof.size), f"{m['dist_to_snake']:.1f}", f"{m['dist_to_ladder']:.1f}",
                    f"{m['snakes_within_6']:.2f}", f"{m['ladders_within_6']:.2f}", f"{m['position_pct']:.0f}",
                    f"{prof.hazard:+.2f}"]
            for v, f in zip(vals, fr[1:]):
                draw.draw_text(surface, v, bf, theme.TEXT, (c.x + int(c.w * f), y), "midleft")
        note = f"silhouette {cl.silhouette:.3f}   inertia {cl.inertia:.1f}   zones ranked by mean hazard"
        draw.draw_text(surface, draw.ellipsize(fonts.get(11), note, c.w), fonts.get(11), theme.TEXT_FAINT,
                       (c.x, c.bottom - S(2)), "bottomleft")
        return None

    # -- models -------------------------------------------------------------------
    def _draw_models(self, surface: pygame.Surface, c: pygame.Rect):
        b = self.app.bundle
        m = b.model.metrics
        rows = [
            ("BFS", theme.CYAN, f"Min rolls from every cell to 100; cell 1 needs {b.bfs.min_rolls(1)}"),
            ("A*", theme.GOLD, "Risk-aware safe route; BFS table is the heuristic"),
            ("Logistic Regression", theme.GREEN, f"5 features -> win probability ({m.accuracy:.1%} held-out accuracy)" if m else "5 features -> win probability"),
            ("K-Means", theme.MAGENTA, f"K = 3 zones, silhouette {b.clusterer.silhouette:.2f}"),
        ]
        rh = c.h // 4
        nf, df = fonts.get(12.5, True), fonts.get(11.5)
        for i, (name, col, desc) in enumerate(rows):
            y = c.y + i * rh + rh // 2
            badge = StatusBadge.draw(surface, name, col, (c.x, y), "midleft", self.time, size=11)
            x = c.x + S(150)
            draw.draw_text(surface, draw.ellipsize(df, desc, c.right - x), df, theme.TEXT_DIM, (x, y), "midleft")
        return None

    # -- simulation ---------------------------------------------------------------
    def _draw_sim(self, surface: pygame.Surface, c: pygame.Rect):
        b = self.app.bundle
        s = b.summary
        sec = b.seconds
        rows = [
            ("Simulated games", f"{s.n_games:,}"),
            ("Training rows", f"{s.n_rows:,}"),
            ("Rows labelled won", f"{s.win_fraction:.1%}"),
            ("Avg game length", f"{s.avg_game_length:.1f} turns"),
            ("Source", b.source),
        ]
        if "simulation" in sec:
            rows.append(("Sim / LR / K-Means", f"{sec.get('simulation', 0):.1f}s / {sec.get('logistic_regression', 0):.1f}s / {sec.get('kmeans', 0):.2f}s"))
        rh = c.h // len(rows)
        lf, vf = fonts.get(11.5), fonts.get(12.5, True)
        for i, (k, v) in enumerate(rows):
            y = c.y + i * rh + rh // 2
            draw.draw_text(surface, k, lf, theme.TEXT_DIM, (c.x, y), "midleft")
            draw.draw_text(surface, draw.ellipsize(vf, v, c.w // 2), vf, theme.TEXT, (c.right, y), "midright")
        return None

    # -- features ------------------------------------------------------------------
    def _draw_features(self, surface: pygame.Surface, c: pygame.Rect):
        m = self.app.bundle.model.metrics
        coefs = m.coefficients if m else {}
        peak = max([abs(v) for v in coefs.values()] + [1e-6])
        rh = c.h // len(FEATURE_NAMES)
        nf, df = fonts.get(12.5, True), fonts.get(11)
        name_w = int(c.w * 0.22)
        bar_w = int(c.w * 0.26)
        for i, name in enumerate(FEATURE_NAMES):
            y = c.y + i * rh + rh // 2
            draw.draw_text(surface, name, nf, theme.GOLD, (c.x, y), "midleft")
            desc_x = c.x + name_w
            draw.draw_text(surface, draw.ellipsize(df, FEATURE_DESCRIPTIONS[name], c.w - name_w - bar_w - S(60)), df,
                           theme.TEXT_DIM, (desc_x, y), "midleft")
            coef = coefs.get(name, 0.0)
            zero = c.right - bar_w // 2 - S(46)
            draw.draw_text(surface, "coef", fonts.get(10), theme.TEXT_FAINT, (zero - bar_w // 2 - S(4), y), "midright")
            pygame.draw.line(surface, (90, 106, 160), (zero, y - rh // 3), (zero, y + rh // 3))
            w = int((bar_w // 2) * abs(coef) / peak)
            col = theme.GREEN if coef >= 0 else theme.RED
            bar = pygame.Rect(zero if coef >= 0 else zero - w, y - S(4), max(2, w), S(8))
            draw.fill_rrect(surface, bar, col, 3)
            draw.draw_text(surface, f"{coef:+.2f}", fonts.get(11, True), theme.TEXT, (c.right, y), "midright")
        return None

    # -- performance ----------------------------------------------------------------
    def _draw_perf(self, surface: pygame.Surface, c: pygame.Rect):
        m = self.app.bundle.model.metrics
        if m is None:
            return None
        left_w = int(c.w * 0.44)
        rows = [
            ("Accuracy", f"{m.accuracy:.1%}", theme.GREEN),
            ("Majority baseline", f"{m.baseline_accuracy:.1%}", theme.TEXT_DIM),
            ("ROC AUC", f"{m.roc_auc:.3f}", theme.CYAN),
            ("Precision", f"{m.precision:.3f}", theme.TEXT),
            ("Recall", f"{m.recall:.3f}", theme.TEXT),
            ("F1", f"{m.f1:.3f}", theme.TEXT),
        ]
        rh = (c.h - S(20)) // len(rows)
        lf, vf = fonts.get(12), fonts.get(13, True)
        for i, (k, v, col) in enumerate(rows):
            y = c.y + i * rh + rh // 2
            draw.draw_text(surface, k, lf, theme.TEXT_DIM, (c.x, y), "midleft")
            draw.draw_text(surface, v, vf, col, (c.x + left_w - S(12), y), "midright")
        note = f"train {m.n_train:,} rows | held-out {m.n_test:,} rows (unseen games)"
        draw.draw_text(surface, draw.ellipsize(fonts.get(10.5), note, left_w), fonts.get(10.5), theme.TEXT_FAINT,
                       (c.x, c.bottom), "bottomleft")

        rx = c.x + left_w + S(10)
        rw = c.right - rx
        # confusion matrix
        cm_h = int((c.h - S(4)) * 0.56)
        cell_w, cell_h = (rw - S(70)) // 2, (cm_h - S(34)) // 2
        top = c.y + S(2)
        draw.draw_text(surface, "CONFUSION MATRIX", fonts.get(10.5, True), theme.TEXT_DIM, (rx, top))
        gx, gy = rx + S(66), top + S(22)
        for j, lab in enumerate(("pred lost", "pred won")):
            draw.draw_text(surface, lab, fonts.get(10), theme.TEXT_FAINT, (gx + j * cell_w + cell_w // 2, gy - S(3)), "midbottom")
        peak = max(max(r) for r in m.confusion) or 1
        for i, lab in enumerate(("lost", "won")):
            draw.draw_text(surface, "actual " + lab, fonts.get(10), theme.TEXT_FAINT, (gx - S(4), gy + i * cell_h + cell_h // 2), "midright")
            for j in range(2):
                r = pygame.Rect(gx + j * cell_w, gy + i * cell_h, cell_w - S(3), cell_h - S(3))
                good = i == j
                col = theme.GREEN if good else theme.RED
                draw.fill_rrect(surface, r, draw.with_alpha(col, 30 + int(110 * m.confusion[i][j] / peak)), S(6))
                draw.stroke_rrect(surface, r, draw.with_alpha(col, 150), S(6), 1)
                draw.draw_text(surface, f"{m.confusion[i][j]:,}", fonts.get(12.5, True), theme.TEXT, r.center, "center")
        # probability examples
        ey = c.y + cm_h + S(8)
        draw.draw_text(surface, "PROBABILITY EXAMPLES  (cell -> win probability)", fonts.get(10.5, True), theme.TEXT_DIM, (rx, ey))
        n = len(m.examples)
        cw = (rw - S(4) * (n - 1)) // max(1, n)
        for k, (cell, p) in enumerate(m.examples):
            r = pygame.Rect(rx + k * (cw + S(4)), ey + S(18), cw, c.bottom - ey - S(18))
            Card.draw(surface, r, theme.GREEN, glow=0.0, radius=S(6))
            draw.draw_text(surface, f"#{cell}", fonts.get(10.5), theme.TEXT_DIM, (r.centerx, r.y + S(5)), "midtop")
            draw.draw_text(surface, f"{p:.0%}", fonts.get(13, True), theme.TEXT, (r.centerx, r.bottom - S(4)), "midbottom")
        return None
