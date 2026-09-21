/**
 * AI-Powered Snake & Ladder — Exact Replica Engine for Web
 * Matches ui/screens.py, ui/game_screen.py, ui/board_renderer.py from ai_snake_ladder.zip
 */

(() => {
  'use strict';

  // --- Constants & Rules (Matches game/constants.py) ---
  const BOARD_SIZE = 10;
  const NUM_CELLS = 100;
  const GOAL_CELL = 100;
  const START_CELL = 1;
  const WEIGHT_ASTAR = 0.60;
  const WEIGHT_LOGISTIC = 0.40;
  const SHIELD_THRESHOLD = { 2: 0.10, 1: 0.16 };
  const ENDGAME_CELL = 75;
  const ENDGAME_FACTOR = 0.5;

  const SNAKES = GAME_AI_DATA.snakes;
  const LADDERS = GAME_AI_DATA.ladders;

  // Exact 10 Snake Palettes from ui/board_renderer.py
  const SNAKE_PALETTES = [
    ['#00c896', '#96ffdc'], ['#ff7a3c', '#ffce96'],
    ['#d058ff', '#eebfff'], ['#ff5474', '#ffb0be'],
    ['#58acff', '#b0daff'], ['#f6cc46', '#fff0aa'],
    ['#6ee05c', '#c8ffa8'], ['#ff7ac4', '#ffc8e8'],
    ['#42d6e0', '#aaf4f8'], ['#b08aff', '#dec8ff']
  ];

  // Colors from ui/theme.py
  const THEME = {
    bgTop: '#070a18',
    bgBottom: '#100a24',
    panelTop: '#1e2646',
    panelBottom: '#0f1328',
    cyan: '#48deff',
    magenta: '#da60ff',
    gold: '#ffce60',
    green: '#54eca4',
    red: '#ff5e74',
    blue: '#68a8ff',
    cellEven: '#222c52',
    cellOdd: '#1a2244',
    cellHead: '#602238',
    cellTail: '#184a4e',
    cellBottom: '#624c1e',
    cellTop: '#1a543e',
    cellGoal: '#be9434',
    cellStart: '#1e6054'
  };

  // --- Sound Effects System (Matches ui/audio.py) ---
  class SoundManager {
    constructor() {
      this.enabled = true;
      this.ctx = null;
    }

    init() {
      if (!this.ctx) {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (AudioCtx) this.ctx = new AudioCtx();
      }
      if (this.ctx && this.ctx.state === 'suspended') {
        this.ctx.resume();
      }
    }

    play(name) {
      if (!this.enabled) return;
      this.init();
      if (!this.ctx) return;
      const t = this.ctx.currentTime;

      try {
        switch (name) {
          case 'click': {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.frequency.setValueAtTime(1300, t);
            gain.gain.setValueAtTime(0.2, t);
            gain.gain.exponentialRampToValueAtTime(0.001, t + 0.05);
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start(t);
            osc.stop(t + 0.05);
            break;
          }
          case 'dice': {
            for (let i = 0; i < 8; i++) {
              const delay = i * 0.06;
              const osc = this.ctx.createOscillator();
              const gain = this.ctx.createGain();
              osc.type = 'square';
              osc.frequency.setValueAtTime(700 + Math.random() * 800, t + delay);
              gain.gain.setValueAtTime(0.12, t + delay);
              gain.gain.exponentialRampToValueAtTime(0.001, t + delay + 0.03);
              osc.connect(gain);
              gain.connect(this.ctx.destination);
              osc.start(t + delay);
              osc.stop(t + delay + 0.03);
            }
            break;
          }
          case 'move': {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.frequency.setValueAtTime(520, t);
            gain.gain.setValueAtTime(0.2, t);
            gain.gain.exponentialRampToValueAtTime(0.001, t + 0.07);
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start(t);
            osc.stop(t + 0.07);
            break;
          }
          case 'ladder': {
            [440, 554, 659, 880].forEach((freq, idx) => {
              const st = t + idx * 0.09;
              const osc = this.ctx.createOscillator();
              const gain = this.ctx.createGain();
              osc.frequency.setValueAtTime(freq, st);
              gain.gain.setValueAtTime(0.18, st);
              gain.gain.exponentialRampToValueAtTime(0.001, st + 0.15);
              osc.connect(gain);
              gain.connect(this.ctx.destination);
              osc.start(st);
              osc.stop(st + 0.15);
            });
            break;
          }
          case 'snake': {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(520, t);
            osc.frequency.linearRampToValueAtTime(140, t + 0.5);
            gain.gain.setValueAtTime(0.18, t);
            gain.gain.exponentialRampToValueAtTime(0.001, t + 0.5);
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start(t);
            osc.stop(t + 0.5);
            break;
          }
          case 'shield': {
            [880, 1320].forEach(f => {
              const osc = this.ctx.createOscillator();
              const gain = this.ctx.createGain();
              osc.frequency.setValueAtTime(f, t);
              gain.gain.setValueAtTime(0.15, t);
              gain.gain.exponentialRampToValueAtTime(0.001, t + 0.45);
              osc.connect(gain);
              gain.connect(this.ctx.destination);
              osc.start(t);
              osc.stop(t + 0.45);
            });
            break;
          }
          case 'ai': {
            [660, 990].forEach((f, i) => {
              const st = t + i * 0.1;
              const osc = this.ctx.createOscillator();
              const gain = this.ctx.createGain();
              osc.frequency.setValueAtTime(f, st);
              gain.gain.setValueAtTime(0.15, st);
              gain.gain.exponentialRampToValueAtTime(0.001, st + 0.12);
              osc.connect(gain);
              gain.connect(this.ctx.destination);
              osc.start(st);
              osc.stop(st + 0.12);
            });
            break;
          }
          case 'victory': {
            [523, 659, 784, 1046, 784, 1046, 1318].forEach((f, idx) => {
              const st = t + idx * 0.13;
              const osc = this.ctx.createOscillator();
              const gain = this.ctx.createGain();
              osc.type = 'triangle';
              osc.frequency.setValueAtTime(f, st);
              gain.gain.setValueAtTime(0.2, st);
              gain.gain.exponentialRampToValueAtTime(0.001, st + 0.3);
              osc.connect(gain);
              gain.connect(this.ctx.destination);
              osc.start(st);
              osc.stop(st + 0.3);
            });
            break;
          }
        }
      } catch (e) {
        console.warn('Audio error:', e);
      }
    }

    toggle() {
      this.enabled = !this.enabled;
      return this.enabled;
    }
  }

  const audio = new SoundManager();

  // --- Ambient Particle Field (ui/particles.py) ---
  class AmbientField {
    constructor(canvas) {
      this.canvas = canvas;
      this.ctx = canvas.getContext('2d');
      this.particles = [];
      this.resize();
      window.addEventListener('resize', () => this.resize());
      for (let i = 0; i < 45; i++) {
        this.particles.push({
          x: Math.random() * this.w,
          y: Math.random() * this.h,
          vx: (Math.random() - 0.5) * 0.3,
          vy: -0.2 - Math.random() * 0.25,
          r: 1 + Math.random() * 2,
          a: 0.15 + Math.random() * 0.3,
          hue: Math.random() > 0.5 ? 190 : 280
        });
      }
      this.draw = this.draw.bind(this);
      requestAnimationFrame(this.draw);
    }

    resize() {
      this.w = this.canvas.width = window.innerWidth;
      this.h = this.canvas.height = window.innerHeight;
    }

    draw() {
      this.ctx.clearRect(0, 0, this.w, this.h);
      for (const p of this.particles) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.y < -10) { p.y = this.h + 10; p.x = Math.random() * this.w; }
        if (p.x < -10) p.x = this.w + 10;
        if (p.x > this.w + 10) p.x = -10;

        this.ctx.beginPath();
        this.ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        this.ctx.fillStyle = `hsla(${p.hue}, 85%, 70%, ${p.a})`;
        this.ctx.fill();
      }
      requestAnimationFrame(this.draw);
    }
  }

  // --- Board Coordinate Helpers (game/board.py) ---
  function cellToGrid(cell) {
    const idx = cell - 1;
    let row = Math.floor(idx / BOARD_SIZE);
    let col = idx % BOARD_SIZE;
    if (row % 2 === 1) {
      col = BOARD_SIZE - 1 - col;
    }
    return { row, col };
  }

  function gridToCell(row, col) {
    const actualCol = (row % 2 === 0) ? col : (BOARD_SIZE - 1 - col);
    return row * BOARD_SIZE + actualCol + 1;
  }

  // --- Main Application Manager (Matches App in ui/app.py) ---
  class AppManager {
    constructor() {
      // Screen references
      this.screens = {
        home: document.getElementById('screen-home'),
        game: document.getElementById('screen-game'),
        lab: document.getElementById('screen-lab'),
        how: document.getElementById('screen-how')
      };
      this.currentScreen = 'home';

      // Game state
      this.humanPos = START_CELL;
      this.aiPos = START_CELL;
      this.humanShields = 2;
      this.aiShields = 2;
      this.currentTurn = 'HUMAN'; // 'HUMAN' | 'AI'
      this.phase = 'WAIT_ROLL'; // 'WAIT_ROLL' | 'ROLLING' | 'CHOOSE' | 'AI_THINK' | 'MOVING' | 'SHIELD' | 'VICTORY'
      this.currentDice = [1, 6];
      this.hoverCandidate = null;

      // Overlays
      this.showHeatmap = false;
      this.showBFS = false;

      // Board Canvas
      this.boardCanvas = document.getElementById('board-canvas');
      this.ctx = this.boardCanvas.getContext('2d');
      this.canvasSize = 630;

      // Animated Token positions
      this.tokenPos = {
        human: { ...this.getCellFraction(START_CELL), lift: 0 },
        ai: { ...this.getCellFraction(START_CELL), lift: 0 }
      };
      this.activeAnimation = null;

      // Build curved snakes and ladder lines
      this.buildBoardCurves();

      // Setup DOM and Event Handlers
      this.initDom();
      this.setupEvents();
      this.resizeCanvas();
      window.addEventListener('resize', () => this.resizeCanvas());

      // Start Render Loop
      this.render = this.render.bind(this);
      requestAnimationFrame(this.render);
    }

    goto(name) {
      audio.play('click');
      for (const s of Object.values(this.screens)) {
        s.classList.remove('active');
      }
      this.screens[name].classList.add('active');
      this.currentScreen = name;
      window.scrollTo(0, 0);

      if (name === 'game') {
        this.resizeCanvas();
      }
    }

    resizeCanvas() {
      const rect = this.boardCanvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      this.canvasSize = Math.min(rect.width, rect.height) || 600;
      this.boardCanvas.width = this.canvasSize * dpr;
      this.boardCanvas.height = this.canvasSize * dpr;
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    getCellFraction(cell) {
      const { row, col } = cellToGrid(cell);
      return {
        x: (col + 0.5) / BOARD_SIZE,
        y: (BOARD_SIZE - 1 - row + 0.5) / BOARD_SIZE
      };
    }

    buildBoardCurves() {
      this.snakePaths = {};
      let i = 0;
      for (const [headStr, tail] of Object.entries(SNAKES)) {
        const head = parseInt(headStr, 10);
        const p1 = this.getCellFraction(head);
        const p2 = this.getCellFraction(tail);
        const dx = p2.x - p1.x;
        const dy = p2.y - p1.y;
        const dist = Math.hypot(dx, dy);
        const nx = -dy / dist;
        const ny = dx / dist;

        const pts = [];
        const count = 30;
        const waves = 2.5;
        const amp = 0.04;
        for (let step = 0; step <= count; step++) {
          const t = step / count;
          const env = Math.pow(Math.sin(Math.PI * t), 0.7);
          const off = amp * env * Math.sin(t * waves * Math.PI);
          pts.push({
            x: p1.x + dx * t + nx * off,
            y: p1.y + dy * t + ny * off
          });
        }
        this.snakePaths[head] = {
          pts,
          colors: SNAKE_PALETTES[i % SNAKE_PALETTES.length]
        };
        i++;
      }

      this.ladderPaths = {};
      for (const [bottomStr, top] of Object.entries(LADDERS)) {
        const bottom = parseInt(bottomStr, 10);
        this.ladderPaths[bottom] = {
          p1: this.getCellFraction(bottom),
          p2: this.getCellFraction(top)
        };
      }
    }

    initDom() {
      // Home Screen Buttons
      document.getElementById('btn-home-start').addEventListener('click', () => this.goto('game'));
      document.getElementById('btn-home-lab').addEventListener('click', () => this.goto('lab'));
      document.getElementById('btn-home-how').addEventListener('click', () => this.goto('how'));

      // Header Navigation Buttons
      document.getElementById('btn-game-menu').addEventListener('click', () => this.goto('home'));
      document.getElementById('btn-lab-back').addEventListener('click', () => this.goto('home'));
      document.getElementById('btn-how-back').addEventListener('click', () => this.goto('home'));

      // Sound Toggle
      const soundBtn = document.getElementById('btn-game-sound');
      soundBtn.addEventListener('click', () => {
        const on = audio.toggle();
        soundBtn.textContent = on ? 'SOUND ON [M]' : 'SOUND OFF [M]';
        audio.play('click');
      });

      // Fullscreen Toggle
      document.getElementById('btn-game-fs').addEventListener('click', () => {
        if (!document.fullscreenElement) {
          document.documentElement.requestFullscreen().catch(() => {});
        } else {
          document.exitFullscreen().catch(() => {});
        }
      });

      // Board Overlays
      const btnHeat = document.getElementById('btn-board-heat');
      btnHeat.addEventListener('click', () => {
        this.showHeatmap = !this.showHeatmap;
        btnHeat.classList.toggle('active', this.showHeatmap);
        audio.play('click');
      });

      const btnRoute = document.getElementById('btn-board-route');
      btnRoute.addEventListener('click', () => {
        this.showBFS = !this.showBFS;
        btnRoute.classList.toggle('active', this.showBFS);
        audio.play('click');
      });

      // Roll Button
      this.rollBtn = document.getElementById('btn-roll-dice');
      this.rollBtn.addEventListener('click', () => this.onRollClicked());

      // Candidate Choice Cards
      this.candGrid = document.getElementById('cand-choice-grid');
      this.candCards = [document.getElementById('card-choice-0'), document.getElementById('card-choice-1')];
      this.candCards[0].addEventListener('click', () => this.chooseDie(0));
      this.candCards[1].addEventListener('click', () => this.chooseDie(1));
      this.candCards[0].addEventListener('mouseenter', () => this.setHoverDie(0));
      this.candCards[0].addEventListener('mouseleave', () => this.clearHoverDie());
      this.candCards[1].addEventListener('mouseenter', () => this.setHoverDie(1));
      this.candCards[1].addEventListener('mouseleave', () => this.clearHoverDie());

      // Status Display elements
      this.posTextHuman = document.getElementById('pos-text-human');
      this.posTextAi = document.getElementById('pos-text-ai');
      this.winprobTextHuman = document.getElementById('winprob-text-human');
      this.winprobTextAi = document.getElementById('winprob-text-ai');
      this.barFillHuman = document.getElementById('bar-fill-human');
      this.barFillAi = document.getElementById('bar-fill-ai');
      this.cardHuman = document.getElementById('status-card-human');
      this.cardAi = document.getElementById('status-card-ai');
      this.badgeAiTurn = document.getElementById('badge-ai-turn');

      this.shieldH1 = document.getElementById('shield-h-1');
      this.shieldH2 = document.getElementById('shield-h-2');
      this.shieldA1 = document.getElementById('shield-a-1');
      this.shieldA2 = document.getElementById('shield-a-2');

      // AI Panel elements
      this.aiStatusBadge = document.getElementById('ai-status-badge');
      this.aiVerdictBanner = document.getElementById('ai-verdict-banner');

      // Log Feed
      this.logFeed = document.getElementById('event-log-feed');
      document.getElementById('btn-clear-log').addEventListener('click', () => {
        this.logFeed.innerHTML = '';
      });

      // Modals
      this.shieldModal = document.getElementById('modal-shield');
      document.getElementById('btn-shield-accept').addEventListener('click', () => this.resolveShield(true));
      document.getElementById('btn-shield-decline').addEventListener('click', () => this.resolveShield(false));

      this.victoryModal = document.getElementById('modal-victory');
      document.getElementById('btn-victory-again').addEventListener('click', () => this.resetMatch());
      document.getElementById('btn-victory-menu').addEventListener('click', () => {
        this.victoryModal.classList.remove('show');
        this.goto('home');
      });

      // AI Lab Tabs
      const labTabs = document.querySelectorAll('.tab-nav-btn');
      labTabs.forEach(btn => {
        btn.addEventListener('click', () => {
          labTabs.forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          const tabId = btn.getAttribute('data-tab');
          document.querySelectorAll('.tab-content-area').forEach(p => p.classList.remove('active'));
          document.getElementById(tabId).classList.add('active');
          audio.play('click');
        });
      });

      // BFS Slider in AI Lab
      const bfsSlider = document.getElementById('bfs-cell-slider');
      const bfsDisp = document.getElementById('bfs-slider-display');
      const bfsRoute = document.getElementById('bfs-route-display');
      const updateBfsInfo = (cell) => {
        bfsDisp.textContent = `Cell ${cell}`;
        const path = GAME_AI_DATA.bfs_paths[cell] || [cell];
        const rolls = GAME_AI_DATA.bfs_rolls[cell] || 0;
        bfsRoute.innerHTML = `<strong>Minimum Rolls:</strong> ${rolls} rolls<br><strong>Shortest Path to 100:</strong> ${path.join(' &rarr; ')}`;
      };
      bfsSlider.addEventListener('input', (e) => updateBfsInfo(parseInt(e.target.value, 10)));
      updateBfsInfo(1);

      // Tooltip
      this.tooltip = document.getElementById('game-tooltip');
      this.boardCanvas.addEventListener('mousemove', (e) => this.handleBoardHover(e));
      this.boardCanvas.addEventListener('mouseleave', () => { this.tooltip.style.display = 'none'; });
    }

    setupEvents() {
      window.addEventListener('keydown', (e) => {
        if (this.currentScreen !== 'game') return;
        const key = e.key.toUpperCase();

        if (key === 'ESCAPE') {
          this.goto('home');
        } else if (key === ' ' || key === 'ENTER') {
          if (this.phase === 'WAIT_ROLL' && this.currentTurn === 'HUMAN') {
            e.preventDefault();
            this.onRollClicked();
          }
        } else if (key === '1') {
          if (this.phase === 'CHOOSE') this.chooseDie(0);
        } else if (key === '2') {
          if (this.phase === 'CHOOSE') this.chooseDie(1);
        } else if (key === 'H') {
          document.getElementById('btn-board-heat').click();
        } else if (key === 'P') {
          document.getElementById('btn-board-route').click();
        } else if (key === 'M') {
          document.getElementById('btn-game-sound').click();
        } else if (key === 'Y' && this.phase === 'SHIELD') {
          this.resolveShield(true);
        } else if (key === 'N' && this.phase === 'SHIELD') {
          this.resolveShield(false);
        }
      });
    }

    logEvent(msg, badgeText = 'TURN', badgeColor = 'var(--cyan)') {
      const item = document.createElement('div');
      item.className = 'log-item';
      item.innerHTML = `<span class="log-badge" style="background: rgba(255,255,255,0.1); color: ${badgeColor};">${badgeText}</span><span>${msg}</span>`;
      this.logFeed.appendChild(item);
      this.logFeed.scrollTop = this.logFeed.scrollHeight;
    }

    handleBoardHover(e) {
      const rect = this.boardCanvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const cs = this.canvasSize / BOARD_SIZE;

      const col = Math.floor(x / cs);
      const rowFromTop = Math.floor(y / cs);
      if (col < 0 || col >= BOARD_SIZE || rowFromTop < 0 || rowFromTop >= BOARD_SIZE) {
        this.tooltip.style.display = 'none';
        return;
      }

      const row = BOARD_SIZE - 1 - rowFromTop;
      const cell = gridToCell(row, col);

      const zone = GAME_AI_DATA.zones[cell] || 'SAFE';
      const bfs = GAME_AI_DATA.bfs_rolls[cell] || 0;
      const astar = GAME_AI_DATA.astar_scores[cell] || 0;
      const prob = ((GAME_AI_DATA.win_prob[cell] || 0) * 100).toFixed(1);

      let extra = '';
      if (SNAKES[cell]) extra = `<div style="color:var(--red);">🐍 Snake head &rarr; Drops to ${SNAKES[cell]}</div>`;
      if (LADDERS[cell]) extra = `<div style="color:var(--green);">🪜 Ladder base &rarr; Climbs to ${LADDERS[cell]}</div>`;

      this.tooltip.innerHTML = `
        <div style="display:flex; justify-content:space-between; gap:12px; margin-bottom:4px;">
          <strong style="color:var(--cyan);">Cell ${cell}</strong>
          <span style="color:${zone === 'DANGER' ? 'var(--red)' : zone === 'ADVANTAGE' ? 'var(--green)' : 'var(--blue)'}; font-weight:700;">${zone}</span>
        </div>
        ${extra}
        <div style="color:var(--text-dim); font-size:0.72rem; display:grid; grid-template-columns:auto auto; gap:2px 8px;">
          <span>BFS Min Rolls:</span><strong style="color:#fff;">${bfs}</strong>
          <span>A* Safe Score:</span><strong style="color:#fff;">${astar}</strong>
          <span>Win Probability:</span><strong style="color:#fff;">${prob}%</strong>
        </div>
      `;
      this.tooltip.style.display = 'block';
      this.tooltip.style.left = `${Math.min(e.clientX + 14, window.innerWidth - 200)}px`;
      this.tooltip.style.top = `${e.clientY + 14}px`;
    }

    // --- Gameplay Turn Flow (Matches ui/game_screen.py) ---
    onRollClicked() {
      if (this.phase !== 'WAIT_ROLL') return;
      this.phase = 'ROLLING';
      this.rollBtn.disabled = true;
      audio.play('dice');

      const d1 = document.getElementById('die-widget-0');
      const d2 = document.getElementById('die-widget-1');
      d1.classList.add('rolling');
      d2.classList.add('rolling');

      let tick = 0;
      const interval = setInterval(() => {
        d1.setAttribute('data-val', Math.floor(Math.random() * 6) + 1);
        d2.setAttribute('data-val', Math.floor(Math.random() * 6) + 1);
        tick++;
        if (tick > 9) {
          clearInterval(interval);
          this.finalizeRoll();
        }
      }, 55);
    }

    finalizeRoll() {
      const d1 = document.getElementById('die-widget-0');
      const d2 = document.getElementById('die-widget-1');
      d1.classList.remove('rolling');
      d2.classList.remove('rolling');

      const val1 = Math.floor(Math.random() * 6) + 1;
      const val2 = Math.floor(Math.random() * 6) + 1;
      this.currentDice = [val1, val2];
      d1.setAttribute('data-val', val1);
      d2.setAttribute('data-val', val2);

      const pos = this.currentTurn === 'HUMAN' ? this.humanPos : this.aiPos;
      const shields = this.currentTurn === 'HUMAN' ? this.humanShields : this.aiShields;

      this.logEvent(`${this.currentTurn === 'HUMAN' ? 'You' : 'AI'} rolled [${val1}] and [${val2}]`, 'ROLL', 'var(--blue)');

      const cands = [
        this.evaluateMove(pos, 0, val1, shields),
        this.evaluateMove(pos, 1, val2, shields)
      ];

      if (this.currentTurn === 'HUMAN') {
        this.presentHumanTurn(cands);
      } else {
        this.runAiTurn(cands);
      }
    }

    evaluateMove(pos, dieIdx, dieVal, shields) {
      const landing = pos + dieVal;
      if (landing > GOAL_CELL) {
        return {
          dieIdx,
          dieVal,
          valid: false,
          landing: 0,
          dest: pos,
          special: 'NONE',
          note: 'Overshoots cell 100 — illegal',
          astar: 0,
          winProb: 0,
          zone: '-',
          score: -1
        };
      }

      let dest = landing;
      let special = 'NONE';
      let note = 'Plain move';

      if (SNAKES[landing]) {
        special = 'SNAKE';
        dest = SNAKES[landing];
        note = `Snake at ${landing} -> slides to ${dest}`;
      } else if (LADDERS[landing]) {
        special = 'LADDER';
        dest = LADDERS[landing];
        note = `Ladder at ${landing} -> climbs to ${dest}`;
      }

      if (dest === GOAL_CELL) note = 'Winning move to cell 100!';

      const astar = GAME_AI_DATA.astar_scores[dest] || 0;
      const winProb = GAME_AI_DATA.win_prob[dest] || 0;
      const zone = GAME_AI_DATA.zones[dest] || 'SAFE';
      const score = WEIGHT_ASTAR * astar + WEIGHT_LOGISTIC * winProb;

      return {
        dieIdx,
        dieVal,
        valid: true,
        landing,
        dest,
        special,
        note,
        astar,
        winProb,
        zone,
        score
      };
    }

    presentHumanTurn(cands) {
      this.phase = 'CHOOSE';
      this.candGrid.style.display = 'grid';
      document.getElementById('turn-phase-indicator').textContent = 'SELECT DIE [1] OR [2]';

      cands.forEach((c, idx) => {
        const card = this.candCards[idx];
        const valText = document.getElementById(`choice-val-${idx}`);
        const destText = document.getElementById(`choice-dest-${idx}`);
        const noteText = document.getElementById(`choice-note-${idx}`);

        valText.textContent = c.dieVal;
        if (!c.valid) {
          card.classList.add('disabled');
          destText.textContent = 'Illegal Overshoot';
          noteText.textContent = c.note;
        } else {
          card.classList.remove('disabled');
          destText.textContent = `Destination: Cell ${c.landing} (${c.zone})`;
          noteText.textContent = c.note;
        }
      });

      if (!cands[0].valid && !cands[1].valid) {
        this.logEvent('Both dice overshoot cell 100! Turn skipped.', 'SKIP', 'var(--orange)');
        setTimeout(() => this.finishTurn(), 1400);
      }
    }

    setHoverDie(idx) {
      if (this.phase !== 'CHOOSE') return;
      const c = this.evaluateMove(this.humanPos, idx, this.currentDice[idx], this.humanShields);
      if (c.valid) this.hoverCandidate = c.dest;
    }

    clearHoverDie() {
      this.hoverCandidate = null;
    }

    chooseDie(idx) {
      if (this.phase !== 'CHOOSE') return;
      const c = this.evaluateMove(this.humanPos, idx, this.currentDice[idx], this.humanShields);
      if (!c.valid) return;

      this.clearHoverDie();
      this.candGrid.style.display = 'none';
      audio.play('click');
      this.startPlayerMove('HUMAN', c);
    }

    runAiTurn(cands) {
      this.phase = 'AI_THINK';
      audio.play('ai');
      this.aiStatusBadge.textContent = 'ANALYZING';
      this.aiStatusBadge.style.color = 'var(--magenta)';

      // Update AI Transparency Panel values
      cands.forEach((c, i) => {
        document.getElementById(`ai-title-${i}`).textContent = `DICE OPTION ${'AB'[i]}: ${c.dieVal}`;
        document.getElementById(`ai-dest-${i}`).textContent = c.valid ? `Cell ${c.dest} (${c.zone})` : 'Illegal';
        document.getElementById(`ai-astar-text-${i}`).textContent = c.astar.toFixed(3);
        document.getElementById(`ai-astar-bar-${i}`).style.width = `${c.astar * 100}%`;
        document.getElementById(`ai-win-text-${i}`).textContent = `${(c.winProb * 100).toFixed(1)}%`;
        document.getElementById(`ai-win-bar-${i}`).style.width = `${c.winProb * 100}%`;
        document.getElementById(`ai-final-text-${i}`).textContent = c.score >= 0 ? c.score.toFixed(3) : 'Illegal';
        document.getElementById(`ai-final-bar-${i}`).style.width = `${Math.max(0, c.score) * 100}%`;
        document.getElementById(`ai-row-${i}`).classList.remove('chosen-verdict');
      });

      setTimeout(() => {
        const valid = cands.filter(c => c.valid);
        if (valid.length === 0) {
          this.aiStatusBadge.textContent = 'NO MOVE';
          this.aiVerdictBanner.textContent = 'Both dice overshoot cell 100. Turn skipped.';
          this.logEvent('AI cannot move: both dice overshoot cell 100.', 'AI', 'var(--magenta)');
          setTimeout(() => this.finishTurn(), 1200);
          return;
        }

        let chosen = null;
        if (valid.length === 1) {
          chosen = valid[0];
          this.aiVerdictBanner.textContent = `AI CHOOSES DICE ${chosen.dieVal} (only legal move)`;
        } else {
          valid.sort((a, b) => {
            if (a.dest === GOAL_CELL) return -1;
            if (b.dest === GOAL_CELL) return 1;
            return b.score - a.score;
          });
          chosen = valid[0];
          const other = valid[1];
          this.aiVerdictBanner.textContent = `AI CHOOSES DICE ${chosen.dieVal} (Score ${chosen.score.toFixed(3)} vs ${other.score.toFixed(3)})`;
        }

        this.aiStatusBadge.textContent = 'DECIDED';
        this.aiStatusBadge.style.color = 'var(--green)';
        this.aiVerdictBanner.classList.add('verdict-active');
        document.getElementById(`ai-row-${chosen.dieIdx}`).classList.add('chosen-verdict');

        this.logEvent(`AI decided on Die ${chosen.dieVal} (Final score: ${chosen.score.toFixed(3)})`, 'AI', 'var(--magenta)');

        setTimeout(() => {
          this.startPlayerMove('AI', chosen);
        }, 900);
      }, 900);
    }

    startPlayerMove(player, plan) {
      this.phase = 'MOVING';
      const fromCell = player === 'HUMAN' ? this.humanPos : this.aiPos;
      const landing = plan.landing;

      this.logEvent(`${player === 'HUMAN' ? 'You' : 'AI'} advances to cell ${landing}`, 'MOVE', 'var(--text)');

      // Hop sequence
      this.animateHops(player, fromCell, landing, () => {
        if (plan.special === 'SNAKE') {
          this.handleSnake(player, landing, plan.dest);
        } else if (plan.special === 'LADDER') {
          this.handleLadder(player, landing, plan.dest);
        } else {
          this.completeMove(player, landing);
        }
      });
    }

    animateHops(player, start, end, callback) {
      const steps = [];
      for (let c = start + 1; c <= end; c++) steps.push(c);

      let i = 0;
      const hopStep = () => {
        if (i >= steps.length) {
          callback();
          return;
        }
        const target = steps[i];
        audio.play('move');
        this.hopTo(player, target, () => {
          i++;
          hopStep();
        });
      };
      hopStep();
    }

    hopTo(player, targetCell, onHopDone) {
      const target = this.getCellFraction(targetCell);
      const tok = this.tokenPos[player.toLowerCase()];
      const sx = tok.x, sy = tok.y;
      const ex = target.x, ey = target.y;

      const duration = 120;
      const t0 = performance.now();

      this.activeAnimation = (now) => {
        const p = Math.min(1, (now - t0) / duration);
        const arc = Math.sin(p * Math.PI) * 0.04;
        tok.x = sx + (ex - sx) * p;
        tok.y = sy + (ey - sy) * p - arc;

        if (p >= 1) {
          tok.x = ex;
          tok.y = ey;
          this.activeAnimation = null;
          onHopDone();
          return false;
        }
        return true;
      };
    }

    handleSnake(player, head, tail) {
      const shields = player === 'HUMAN' ? this.humanShields : this.aiShields;

      if (player === 'HUMAN') {
        if (shields > 0) {
          this.phase = 'SHIELD';
          this.pendingSnake = { player, head, tail };

          const keepScore = WEIGHT_ASTAR * (GAME_AI_DATA.astar_scores[head] || 0) + WEIGHT_LOGISTIC * (GAME_AI_DATA.win_prob[head] || 0);
          const dropScore = WEIGHT_ASTAR * (GAME_AI_DATA.astar_scores[tail] || 0) + WEIGHT_LOGISTIC * (GAME_AI_DATA.win_prob[tail] || 0);
          const benefit = keepScore - dropScore;
          let threshold = SHIELD_THRESHOLD[shields] || 0.16;
          if (head >= ENDGAME_CELL) threshold *= ENDGAME_FACTOR;

          const rec = benefit >= threshold;
          document.getElementById('modal-shield-loss').textContent = `Snake at cell ${head} -> drops to ${tail} (loss of ${head - tail} cells)`;
          document.getElementById('modal-shield-advisor').innerHTML = `<strong>AI Advisor:</strong> Benefit ${benefit > 0 ? '+' : ''}${benefit.toFixed(3)} vs threshold ${threshold.toFixed(3)}. Recommendation: <strong>${rec ? 'USE SHIELD' : 'KEEP IN RESERVE'}</strong>.`;
          this.shieldModal.classList.add('show');
          return;
        }
        this.slideSnake(player, head, tail);
      } else {
        // AI Autonomous Shield Evaluation
        const keepScore = WEIGHT_ASTAR * (GAME_AI_DATA.astar_scores[head] || 0) + WEIGHT_LOGISTIC * (GAME_AI_DATA.win_prob[head] || 0);
        const dropScore = WEIGHT_ASTAR * (GAME_AI_DATA.astar_scores[tail] || 0) + WEIGHT_LOGISTIC * (GAME_AI_DATA.win_prob[tail] || 0);
        const benefit = keepScore - dropScore;
        let threshold = SHIELD_THRESHOLD[shields] || 0.16;
        if (head >= ENDGAME_CELL) threshold *= ENDGAME_FACTOR;

        if (shields > 0 && benefit >= threshold) {
          this.aiShields--;
          this.updateShieldIcons();
          audio.play('shield');
          this.logEvent(`AI spent shield 🛡️ to block snake at cell ${head}!`, 'SHIELD', 'var(--gold)');
          this.completeMove(player, head);
        } else {
          this.logEvent(`AI saved shield (benefit ${benefit.toFixed(2)} < threshold ${threshold.toFixed(2)})`, 'AI', 'var(--magenta)');
          this.slideSnake(player, head, tail);
        }
      }
    }

    resolveShield(use) {
      this.shieldModal.classList.remove('show');
      const { player, head, tail } = this.pendingSnake;
      this.pendingSnake = null;

      if (use && this.humanShields > 0) {
        this.humanShields--;
        this.updateShieldIcons();
        audio.play('shield');
        this.logEvent(`You deployed a shield 🛡️! Maintained cell ${head}.`, 'SHIELD', 'var(--gold)');
        this.completeMove(player, head);
      } else {
        this.slideSnake(player, head, tail);
      }
    }

    slideSnake(player, head, tail) {
      audio.play('snake');
      this.logEvent(`${player === 'HUMAN' ? 'You' : 'AI'} caught by snake at ${head} -> slid to ${tail}!`, 'SNAKE', 'var(--red)');

      const curve = this.snakePaths[head];
      if (!curve) {
        this.completeMove(player, tail);
        return;
      }

      const pts = curve.pts;
      const duration = 650;
      const t0 = performance.now();
      const tok = this.tokenPos[player.toLowerCase()];

      this.activeAnimation = (now) => {
        const p = Math.min(1, (now - t0) / duration);
        const idx = Math.min(pts.length - 1, Math.floor(p * (pts.length - 1)));
        tok.x = pts[idx].x;
        tok.y = pts[idx].y;

        if (p >= 1) {
          const final = this.getCellFraction(tail);
          tok.x = final.x;
          tok.y = final.y;
          this.activeAnimation = null;
          this.completeMove(player, tail);
          return false;
        }
        return true;
      };
    }

    handleLadder(player, bottom, top) {
      audio.play('ladder');
      this.logEvent(`${player === 'HUMAN' ? 'You' : 'AI'} found a ladder at ${bottom} -> climbed to ${top}!`, 'LADDER', 'var(--green)');

      const p1 = this.getCellFraction(bottom);
      const p2 = this.getCellFraction(top);
      const duration = 600;
      const t0 = performance.now();
      const tok = this.tokenPos[player.toLowerCase()];

      this.activeAnimation = (now) => {
        const p = Math.min(1, (now - t0) / duration);
        tok.x = p1.x + (p2.x - p1.x) * p;
        tok.y = p1.y + (p2.y - p1.y) * p;

        if (p >= 1) {
          tok.x = p2.x;
          tok.y = p2.y;
          this.activeAnimation = null;
          this.completeMove(player, top);
          return false;
        }
        return true;
      };
    }

    completeMove(player, cell) {
      if (player === 'HUMAN') {
        this.humanPos = cell;
        this.posTextHuman.textContent = `Cell ${cell}`;
        this.winprobTextHuman.textContent = `Win: ${((GAME_AI_DATA.win_prob[cell] || 0) * 100).toFixed(0)}%`;
        this.barFillHuman.style.width = `${(GAME_AI_DATA.win_prob[cell] || 0) * 100}%`;
      } else {
        this.aiPos = cell;
        this.posTextAi.textContent = `Cell ${cell}`;
        this.winprobTextAi.textContent = `Win: ${((GAME_AI_DATA.win_prob[cell] || 0) * 100).toFixed(0)}%`;
        this.barFillAi.style.width = `${(GAME_AI_DATA.win_prob[cell] || 0) * 100}%`;
      }

      if (cell === GOAL_CELL) {
        this.showVictory(player);
        return;
      }

      this.finishTurn();
    }

    updateShieldIcons() {
      this.shieldH1.className = `shield-unit ${this.humanShields < 1 ? 'spent' : ''}`;
      this.shieldH2.className = `shield-unit ${this.humanShields < 2 ? 'spent' : ''}`;
      this.shieldA1.className = `shield-unit ${this.aiShields < 1 ? 'spent' : ''}`;
      this.shieldA2.className = `shield-unit ${this.aiShields < 2 ? 'spent' : ''}`;
    }

    finishTurn() {
      this.currentTurn = this.currentTurn === 'HUMAN' ? 'AI' : 'HUMAN';
      this.phase = 'WAIT_ROLL';

      if (this.currentTurn === 'HUMAN') {
        this.cardHuman.classList.add('turn-active');
        this.cardAi.classList.remove('turn-active');
        this.badgeAiTurn.style.display = 'none';
        this.rollBtn.disabled = false;
        document.getElementById('turn-phase-indicator').textContent = 'ROLL DICE [SPACE]';
      } else {
        this.cardAi.classList.add('turn-active');
        this.cardHuman.classList.remove('turn-active');
        this.badgeAiTurn.style.display = 'inline-block';
        this.rollBtn.disabled = true;
        document.getElementById('turn-phase-indicator').textContent = 'AI CALCULATING...';

        setTimeout(() => this.onRollClicked(), 600);
      }
    }

    showVictory(winner) {
      this.phase = 'VICTORY';
      audio.play('victory');

      const isHuman = winner === 'HUMAN';
      document.getElementById('victory-winner').textContent = `${winner} WINS`;
      document.getElementById('victory-winner').style.color = isHuman ? 'var(--cyan)' : 'var(--magenta)';
      document.getElementById('victory-tagline').textContent = isHuman
        ? 'Your strategy and shield choices conquered the board!'
        : 'Strategic intelligence conquered the board!';
      document.getElementById('victory-stats').innerHTML = `Winner: ${winner}<br>Final Position: Cell 100`;

      this.victoryModal.classList.add('show');
      this.logEvent(`Match concluded: ${winner} reached cell 100!`, 'WIN', 'var(--gold)');
    }

    resetMatch() {
      this.victoryModal.classList.remove('show');
      this.humanPos = START_CELL;
      this.aiPos = START_CELL;
      this.humanShields = 2;
      this.aiShields = 2;
      this.currentTurn = 'HUMAN';
      this.phase = 'WAIT_ROLL';

      this.posTextHuman.textContent = 'Cell 1';
      this.posTextAi.textContent = 'Cell 1';
      this.winprobTextHuman.textContent = 'Win: 35%';
      this.winprobTextAi.textContent = 'Win: 35%';
      this.barFillHuman.style.width = '35%';
      this.barFillAi.style.width = '35%';
      this.updateShieldIcons();

      this.cardHuman.classList.add('turn-active');
      this.cardAi.classList.remove('turn-active');
      this.rollBtn.disabled = false;
      this.candGrid.style.display = 'none';

      this.tokenPos.human = { ...this.getCellFraction(START_CELL), lift: 0 };
      this.tokenPos.ai = { ...this.getCellFraction(START_CELL), lift: 0 };

      this.logEvent('New game initialized.', 'SYSTEM', 'var(--cyan)');
    }

    // --- HTML5 Canvas Board Rendering (Matches ui/board_renderer.py) ---
    render(now) {
      if (this.activeAnimation) {
        this.activeAnimation(now);
      }

      this.ctx.clearRect(0, 0, this.canvasSize, this.canvasSize);
      const cs = this.canvasSize / BOARD_SIZE;

      // 1. Draw 100 Cells
      for (let cell = 1; cell <= NUM_CELLS; cell++) {
        const { row, col } = cellToGrid(cell);
        const x = col * cs;
        const y = (BOARD_SIZE - 1 - row) * cs;

        let bg = (row + col) % 2 === 0 ? THEME.cellEven : THEME.cellOdd;
        if (SNAKES[cell]) bg = THEME.cellHead;
        else if (Object.values(SNAKES).includes(cell)) bg = THEME.cellTail;
        else if (LADDERS[cell]) bg = THEME.cellBottom;
        else if (Object.values(LADDERS).includes(cell)) bg = THEME.cellTop;
        if (cell === 100) bg = THEME.cellGoal;
        if (cell === 1) bg = THEME.cellStart;

        // Heatmap overlay
        if (this.showHeatmap) {
          const zone = GAME_AI_DATA.zones[cell];
          if (zone === 'DANGER') bg = this.blend(bg, '#ff3b5c', 0.42);
          else if (zone === 'ADVANTAGE') bg = this.blend(bg, '#10b981', 0.42);
          else bg = this.blend(bg, '#3b82f6', 0.28);
        }

        // Cell Box
        this.ctx.fillStyle = bg;
        this.ctx.beginPath();
        this.ctx.roundRect(x + 2, y + 2, cs - 4, cs - 4, 6);
        this.ctx.fill();

        // Border stroke
        this.ctx.strokeStyle = (SNAKES[cell] || LADDERS[cell] || cell === 1 || cell === 100)
          ? 'rgba(255, 255, 255, 0.4)'
          : 'rgba(255, 255, 255, 0.08)';
        this.ctx.lineWidth = 1;
        this.ctx.stroke();

        // Cell Number
        this.ctx.fillStyle = 'rgba(234, 240, 255, 0.9)';
        this.ctx.font = `bold ${Math.max(10, Math.floor(cs * 0.23))}px Outfit, sans-serif`;
        this.ctx.textAlign = 'left';
        this.ctx.textBaseline = 'top';
        this.ctx.fillText(cell.toString(), x + 6, y + 5);

        // Special Markers
        if (cell === 100) {
          this.ctx.fillStyle = THEME.gold;
          this.ctx.font = `bold ${Math.max(9, Math.floor(cs * 0.18))}px Outfit, sans-serif`;
          this.ctx.textAlign = 'center';
          this.ctx.fillText('★ GOAL', x + cs / 2, y + cs - 14);
        } else if (cell === 1) {
          this.ctx.fillStyle = THEME.green;
          this.ctx.font = `bold ${Math.max(9, Math.floor(cs * 0.18))}px Outfit, sans-serif`;
          this.ctx.textAlign = 'center';
          this.ctx.fillText('START', x + cs / 2, y + cs - 14);
        }
      }

      // 2. Draw Ladders
      for (const [bottom, { p1, p2 }] of Object.entries(this.ladderPaths)) {
        const x1 = p1.x * this.canvasSize, y1 = p1.y * this.canvasSize;
        const x2 = p2.x * this.canvasSize, y2 = p2.y * this.canvasSize;
        const dx = x2 - x1, dy = y2 - y1;
        const dist = Math.hypot(dx, dy);
        const nx = -dy / dist * 7;
        const ny = dx / dist * 7;

        this.ctx.strokeStyle = '#f59e0b';
        this.ctx.lineWidth = 3.5;
        this.ctx.shadowColor = 'rgba(245, 158, 11, 0.5)';
        this.ctx.shadowBlur = 6;

        this.ctx.beginPath();
        this.ctx.moveTo(x1 + nx, y1 + ny);
        this.ctx.lineTo(x2 + nx, y2 + ny);
        this.ctx.moveTo(x1 - nx, y1 - ny);
        this.ctx.lineTo(x2 - nx, y2 - ny);
        this.ctx.stroke();

        const rungs = Math.max(3, Math.floor(dist / 22));
        this.ctx.lineWidth = 2.5;
        this.ctx.strokeStyle = '#fde68a';
        for (let r = 1; r < rungs; r++) {
          const t = r / rungs;
          this.ctx.beginPath();
          this.ctx.moveTo(x1 + dx * t + nx, y1 + dy * t + ny);
          this.ctx.lineTo(x1 + dx * t - nx, y1 + dy * t - ny);
          this.ctx.stroke();
        }
        this.ctx.shadowBlur = 0;
      }

      // 3. Draw Curved Snakes
      for (const [head, { pts, colors }] of Object.entries(this.snakePaths)) {
        this.ctx.lineWidth = Math.max(6, cs * 0.14);
        this.ctx.lineCap = 'round';
        this.ctx.lineJoin = 'round';

        const grad = this.ctx.createLinearGradient(
          pts[0].x * this.canvasSize, pts[0].y * this.canvasSize,
          pts[pts.length - 1].x * this.canvasSize, pts[pts.length - 1].y * this.canvasSize
        );
        grad.addColorStop(0, colors[0]);
        grad.addColorStop(1, colors[1]);
        this.ctx.strokeStyle = grad;
        this.ctx.shadowColor = colors[0];
        this.ctx.shadowBlur = 8;

        this.ctx.beginPath();
        this.ctx.moveTo(pts[0].x * this.canvasSize, pts[0].y * this.canvasSize);
        for (let s = 1; s < pts.length; s++) {
          this.ctx.lineTo(pts[s].x * this.canvasSize, pts[s].y * this.canvasSize);
        }
        this.ctx.stroke();
        this.ctx.shadowBlur = 0;

        // Head
        const hx = pts[0].x * this.canvasSize;
        const hy = pts[0].y * this.canvasSize;
        this.ctx.fillStyle = colors[0];
        this.ctx.beginPath();
        this.ctx.arc(hx, hy, cs * 0.17, 0, Math.PI * 2);
        this.ctx.fill();

        // Eyes
        this.ctx.fillStyle = '#fff';
        this.ctx.beginPath();
        this.ctx.arc(hx - 3, hy - 2, 2.2, 0, Math.PI * 2);
        this.ctx.arc(hx + 3, hy - 2, 2.2, 0, Math.PI * 2);
        this.ctx.fill();
        this.ctx.fillStyle = '#000';
        this.ctx.beginPath();
        this.ctx.arc(hx - 3, hy - 2, 1.2, 0, Math.PI * 2);
        this.ctx.arc(hx + 3, hy - 2, 1.2, 0, Math.PI * 2);
        this.ctx.fill();
      }

      // 4. BFS Route Path
      if (this.showBFS) {
        const curCell = this.currentTurn === 'HUMAN' ? this.humanPos : this.aiPos;
        const path = GAME_AI_DATA.bfs_paths[curCell];
        if (path && path.length > 1) {
          this.ctx.strokeStyle = THEME.gold;
          this.ctx.lineWidth = 3;
          this.ctx.setLineDash([6, 6]);
          this.ctx.lineDashOffset = -now / 30;
          this.ctx.beginPath();
          for (let p = 0; p < path.length; p++) {
            const coord = this.getCellFraction(path[p]);
            const px = coord.x * this.canvasSize, py = coord.y * this.canvasSize;
            if (p === 0) this.ctx.moveTo(px, py);
            else this.ctx.lineTo(px, py);
          }
          this.ctx.stroke();
          this.ctx.setLineDash([]);
        }
      }

      // 5. Hover Destination Preview
      if (this.hoverCandidate) {
        const gc = this.getCellFraction(this.hoverCandidate);
        this.ctx.strokeStyle = THEME.cyan;
        this.ctx.lineWidth = 2.5;
        this.ctx.shadowColor = THEME.cyan;
        this.ctx.shadowBlur = 10;
        this.ctx.beginPath();
        this.ctx.arc(gc.x * this.canvasSize, gc.y * this.canvasSize, cs * 0.3, 0, Math.PI * 2);
        this.ctx.stroke();
        this.ctx.shadowBlur = 0;
      }

      // 6. Tokens
      this.drawPawn(this.tokenPos.human.x * this.canvasSize, this.tokenPos.human.y * this.canvasSize, THEME.cyan, 'P', now);
      this.drawPawn(this.tokenPos.ai.x * this.canvasSize, this.tokenPos.ai.y * this.canvasSize, THEME.magenta, 'AI', now);

      requestAnimationFrame(this.render);
    }

    drawPawn(x, y, color, label, now) {
      const cs = this.canvasSize / BOARD_SIZE;
      const radius = cs * 0.25;

      // Glow halo
      const pulse = Math.sin(now / 200) * 3;
      this.ctx.beginPath();
      this.ctx.arc(x, y, radius + 4 + pulse, 0, Math.PI * 2);
      this.ctx.fillStyle = color === THEME.cyan ? 'rgba(72, 222, 255, 0.2)' : 'rgba(218, 96, 255, 0.2)';
      this.ctx.fill();

      // Pawn Body
      const grad = this.ctx.createRadialGradient(x - 3, y - 3, 2, x, y, radius);
      grad.addColorStop(0, '#ffffff');
      grad.addColorStop(0.3, color);
      grad.addColorStop(1, '#070a18');
      this.ctx.fillStyle = grad;
      this.ctx.beginPath();
      this.ctx.arc(x, y, radius, 0, Math.PI * 2);
      this.ctx.fill();

      // Border
      this.ctx.strokeStyle = color;
      this.ctx.lineWidth = 2.5;
      this.ctx.stroke();

      // Text
      this.ctx.fillStyle = '#ffffff';
      this.ctx.font = `bold ${Math.max(9, Math.floor(radius * 0.95))}px Outfit, sans-serif`;
      this.ctx.textAlign = 'center';
      this.ctx.textBaseline = 'middle';
      this.ctx.fillText(label, x, y + 1);
    }

    blend(c1, c2, w) {
      return c2;
    }
  }

  // Initialize
  window.addEventListener('DOMContentLoaded', () => {
    new AmbientField(document.getElementById('ambient-canvas'));
    new AppManager();
  });
})();
