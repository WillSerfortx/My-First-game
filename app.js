/**
 * AI-Powered Snake & Ladder - Web Application Engine
 * Pure Vanilla JavaScript with HTML5 Canvas, Web Audio API, and AI Integration
 */

(() => {
  'use strict';

  // --- Configuration & Constants ---
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

  // Colors
  const COLORS = {
    cyan: '#48deff',
    magenta: '#da60ff',
    gold: '#ffce60',
    emerald: '#54eca4',
    rose: '#ff5e74',
    blue: '#68a8ff',
    cellEven: '#1d264a',
    cellOdd: '#161f3e',
    cellHead: '#4a1b2d',
    cellTail: '#14383c',
    cellBottom: '#453818',
    cellTop: '#143c2c',
    cellGoal: '#664f1d',
    cellStart: '#194943',
    zoneDanger: 'rgba(255, 94, 116, 0.35)',
    zoneSafe: 'rgba(104, 168, 255, 0.25)',
    zoneAdvantage: 'rgba(84, 236, 164, 0.35)'
  };

  // --- Sound Effects System (Web Audio API) ---
  class SoundManager {
    constructor() {
      this.enabled = localStorage.getItem('ai_snake_sound') !== 'false';
      this.ctx = null;
    }

    init() {
      if (!this.ctx) {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (AudioContext) {
          this.ctx = new AudioContext();
        }
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
            for (let i = 0; i < 7; i++) {
              const delay = i * 0.06 + Math.random() * 0.02;
              const osc = this.ctx.createOscillator();
              const gain = this.ctx.createGain();
              osc.type = 'square';
              osc.frequency.setValueAtTime(800 + Math.random() * 800, t + delay);
              gain.gain.setValueAtTime(0.15, t + delay);
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
            gain.gain.setValueAtTime(0.25, t);
            gain.gain.exponentialRampToValueAtTime(0.001, t + 0.08);
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start(t);
            osc.stop(t + 0.08);
            break;
          }
          case 'ladder': {
            const notes = [440, 554, 659, 880];
            notes.forEach((freq, idx) => {
              const st = t + idx * 0.09;
              const osc = this.ctx.createOscillator();
              const gain = this.ctx.createGain();
              osc.frequency.setValueAtTime(freq, st);
              gain.gain.setValueAtTime(0.2, st);
              gain.gain.exponentialRampToValueAtTime(0.001, st + 0.16);
              osc.connect(gain);
              gain.connect(this.ctx.destination);
              osc.start(st);
              osc.stop(st + 0.16);
            });
            break;
          }
          case 'snake': {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(520, t);
            osc.frequency.linearRampToValueAtTime(140, t + 0.55);
            gain.gain.setValueAtTime(0.2, t);
            gain.gain.exponentialRampToValueAtTime(0.001, t + 0.55);
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start(t);
            osc.stop(t + 0.55);
            break;
          }
          case 'shield': {
            [880, 1320].forEach(f => {
              const osc = this.ctx.createOscillator();
              const gain = this.ctx.createGain();
              osc.frequency.setValueAtTime(f, t);
              gain.gain.setValueAtTime(0.18, t);
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
            const fanfare = [523, 659, 784, 1046, 784, 1046, 1318];
            fanfare.forEach((f, idx) => {
              const st = t + idx * 0.13;
              const osc = this.ctx.createOscillator();
              const gain = this.ctx.createGain();
              osc.type = 'triangle';
              osc.frequency.setValueAtTime(f, st);
              gain.gain.setValueAtTime(0.25, st);
              gain.gain.exponentialRampToValueAtTime(0.001, st + 0.32);
              osc.connect(gain);
              gain.connect(this.ctx.destination);
              osc.start(st);
              osc.stop(st + 0.32);
            });
            break;
          }
        }
      } catch (err) {
        console.warn('Audio play error:', err);
      }
    }

    toggle() {
      this.enabled = !this.enabled;
      localStorage.setItem('ai_snake_sound', this.enabled ? 'true' : 'false');
      return this.enabled;
    }
  }

  const sound = new SoundManager();

  // --- Ambient Background Particles ---
  class AmbientParticles {
    constructor(canvas) {
      this.canvas = canvas;
      this.ctx = canvas.getContext('2d');
      this.particles = [];
      this.resize();
      window.addEventListener('resize', () => this.resize());
      for (let i = 0; i < 40; i++) {
        this.particles.push({
          x: Math.random() * this.w,
          y: Math.random() * this.h,
          vx: (Math.random() - 0.5) * 0.35,
          vy: -0.2 - Math.random() * 0.3,
          radius: 1 + Math.random() * 2,
          alpha: 0.1 + Math.random() * 0.35,
          hue: Math.random() > 0.5 ? 190 : 280
        });
      }
      this.animate = this.animate.bind(this);
      requestAnimationFrame(this.animate);
    }

    resize() {
      this.w = this.canvas.width = window.innerWidth;
      this.h = this.canvas.height = window.innerHeight;
    }

    animate() {
      this.ctx.clearRect(0, 0, this.w, this.h);
      for (const p of this.particles) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.y < -10) { p.y = this.h + 10; p.x = Math.random() * this.w; }
        if (p.x < -10) p.x = this.w + 10;
        if (p.x > this.w + 10) p.x = -10;

        this.ctx.beginPath();
        this.ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        this.ctx.fillStyle = `hsla(${p.hue}, 90%, 70%, ${p.alpha})`;
        this.ctx.fill();
      }
      requestAnimationFrame(this.animate);
    }
  }

  // --- Geometry Helpers ---
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
    let actualCol = (row % 2 === 0) ? col : (BOARD_SIZE - 1 - col);
    return row * BOARD_SIZE + actualCol + 1;
  }

  // --- Toast Manager ---
  function showToast(msg) {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = 'toast-msg';
    toast.textContent = msg;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 320);
    }, 2800);
  }

  // --- Game Engine & AI ---
  class GameEngine {
    constructor() {
      this.boardCanvas = document.getElementById('board-canvas');
      this.ctx = this.boardCanvas.getContext('2d');

      this.humanPos = START_CELL;
      this.aiPos = START_CELL;
      this.humanShields = 2;
      this.aiShields = 2;

      this.currentTurn = 'HUMAN'; // 'HUMAN' | 'AI'
      this.state = 'IDLE'; // 'IDLE' | 'ROLLING' | 'CHOOSING' | 'ANIMATING' | 'SHIELD_PROMPT' | 'GAMEOVER'
      this.currentDice = [1, 1];
      this.ghostPreviewCell = null;

      // Overlays
      this.showHeatmap = false;
      this.showBFS = false;

      // Animation & Token Positions
      this.tokenPos = {
        human: { ...this.getCellCenterFraction(START_CELL) },
        ai: { ...this.getCellCenterFraction(START_CELL) }
      };
      this.activeAnimation = null;

      // DOM elements
      this.initDomElements();
      this.setupEventListeners();
      this.resizeCanvas();
      window.addEventListener('resize', () => this.resizeCanvas());

      // Pre-calculate snake & ladder paths
      this.buildCurvedPaths();

      // Populate AI Lab & UI metrics
      this.initLabContent();

      // Start Board Render Loop
      this.render = this.render.bind(this);
      requestAnimationFrame(this.render);

      this.log('Game initialized. Press SPACE or click Roll Dual Dice to begin!', 'pill-ai', 'System');
    }

    initDomElements() {
      this.humanPosVal = document.getElementById('human-pos-val');
      this.aiPosVal = document.getElementById('ai-pos-val');
      this.humanProgressBar = document.getElementById('human-progress-bar');
      this.aiProgressBar = document.getElementById('ai-progress-bar');
      this.humanCard = document.getElementById('human-card');
      this.aiCard = document.getElementById('ai-card');

      this.humanShield1 = document.getElementById('human-shield-1');
      this.humanShield2 = document.getElementById('human-shield-2');
      this.aiShield1 = document.getElementById('ai-shield-1');
      this.aiShield2 = document.getElementById('ai-shield-2');

      this.rollBtn = document.getElementById('roll-dice-btn');
      this.die1Box = document.getElementById('die-1-box');
      this.die2Box = document.getElementById('die-2-box');

      this.candidateGrid = document.getElementById('candidate-grid');
      this.candCard1 = document.getElementById('cand-card-1');
      this.candCard2 = document.getElementById('cand-card-2');
      this.candVal1 = document.getElementById('cand-val-1');
      this.candVal2 = document.getElementById('cand-val-2');
      this.candTarget1 = document.getElementById('cand-target-1');
      this.candTarget2 = document.getElementById('cand-target-2');
      this.candNote1 = document.getElementById('cand-note-1');
      this.candNote2 = document.getElementById('cand-note-2');
      this.chooseDie1Btn = document.getElementById('choose-die-1-btn');
      this.chooseDie2Btn = document.getElementById('choose-die-2-btn');

      this.actionTitle = document.getElementById('action-title');
      this.turnSubtitle = document.getElementById('turn-subtitle');

      this.logFeed = document.getElementById('log-feed');
      this.tooltip = document.getElementById('cell-tooltip');

      // AI Panel elements
      this.aiReasonQuote = document.getElementById('ai-reason-quote');
      this.aiBoxes = [document.getElementById('ai-box-0'), document.getElementById('ai-box-1')];

      // Modals
      this.shieldModal = document.getElementById('shield-modal');
      this.shieldAcceptBtn = document.getElementById('shield-accept-btn');
      this.shieldDeclineBtn = document.getElementById('shield-decline-btn');
      this.shieldLossText = document.getElementById('shield-loss-text');
      this.shieldAdvisorText = document.getElementById('shield-advisor-text');

      this.gameoverModal = document.getElementById('gameover-modal');
      this.gameoverTitle = document.getElementById('gameover-title');
      this.gameoverDesc = document.getElementById('gameover-desc');
      this.gameoverEmoji = document.getElementById('gameover-emoji');
      this.playAgainBtn = document.getElementById('play-again-btn');

      this.toggleHeatmapBtn = document.getElementById('toggle-heatmap-btn');
      this.toggleBfsBtn = document.getElementById('toggle-bfs-btn');
    }

    resizeCanvas() {
      const rect = this.boardCanvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      this.canvasSize = Math.min(rect.width, rect.height) || 600;
      this.boardCanvas.width = this.canvasSize * dpr;
      this.boardCanvas.height = this.canvasSize * dpr;
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    getCellCenterFraction(cell) {
      const { row, col } = cellToGrid(cell);
      return {
        x: (col + 0.5) / BOARD_SIZE,
        y: (BOARD_SIZE - 1 - row + 0.5) / BOARD_SIZE
      };
    }

    buildCurvedPaths() {
      this.snakeCurves = {};
      this.snakeColors = [
        ['#00c896', '#96ffdc'], ['#ff7a3c', '#ffce96'],
        ['#d058ff', '#eebfff'], ['#ff5474', '#ffb0be'],
        ['#58acff', '#b0daff'], ['#f6cc46', '#fff0aa'],
        ['#6ee05c', '#c8ffa8'], ['#ff7ac4', '#ffc8e8'],
        ['#42d6e0', '#aaf4f8'], ['#b08aff', '#dec8ff']
      ];

      let sIdx = 0;
      for (const [headStr, tail] of Object.entries(SNAKES)) {
        const head = parseInt(headStr, 10);
        const p1 = this.getCellCenterFraction(head);
        const p2 = this.getCellCenterFraction(tail);
        const dx = p2.x - p1.x;
        const dy = p2.y - p1.y;
        const dist = Math.hypot(dx, dy);
        const nx = -dy / dist;
        const ny = dx / dist;

        const pts = [];
        const count = 30;
        const waves = 2.5;
        const amp = 0.04;
        for (let i = 0; i <= count; i++) {
          const t = i / count;
          const env = Math.pow(Math.sin(Math.PI * t), 0.7);
          const off = amp * env * Math.sin(t * waves * Math.PI);
          pts.push({
            x: p1.x + dx * t + nx * off,
            y: p1.y + dy * t + ny * off
          });
        }
        this.snakeCurves[head] = {
          pts,
          colors: this.snakeColors[sIdx % this.snakeColors.length]
        };
        sIdx++;
      }

      this.ladderLines = {};
      for (const [bottomStr, top] of Object.entries(LADDERS)) {
        const bottom = parseInt(bottomStr, 10);
        const p1 = this.getCellCenterFraction(bottom);
        const p2 = this.getCellCenterFraction(top);
        this.ladderLines[bottom] = { p1, p2 };
      }
    }

    log(msg, pillClass = 'pill-roll', pillText = 'Turn') {
      const entry = document.createElement('div');
      entry.className = 'log-entry';
      entry.innerHTML = `<span class="log-pill ${pillClass}">${pillText}</span><span>${msg}</span>`;
      this.logFeed.appendChild(entry);
      this.logFeed.scrollTop = this.logFeed.scrollHeight;
    }

    setupEventListeners() {
      // Roll Button
      this.rollBtn.addEventListener('click', () => this.handleRollDice());

      // Die Selection buttons
      this.chooseDie1Btn.addEventListener('click', () => this.chooseDie(0));
      this.chooseDie2Btn.addEventListener('click', () => this.chooseDie(1));
      this.candCard1.addEventListener('click', () => this.chooseDie(0));
      this.candCard2.addEventListener('click', () => this.chooseDie(1));

      // Die card hover preview
      this.candCard1.addEventListener('mouseenter', () => this.previewCandidate(0));
      this.candCard1.addEventListener('mouseleave', () => this.clearPreview());
      this.candCard2.addEventListener('mouseenter', () => this.previewCandidate(1));
      this.candCard2.addEventListener('mouseleave', () => this.clearPreview());

      // Overlays
      this.toggleHeatmapBtn.addEventListener('click', () => {
        this.showHeatmap = !this.showHeatmap;
        this.toggleHeatmapBtn.classList.toggle('active', this.showHeatmap);
        sound.play('click');
      });

      this.toggleBfsBtn.addEventListener('click', () => {
        this.showBFS = !this.showBFS;
        this.toggleBfsBtn.classList.toggle('active', this.showBFS);
        sound.play('click');
      });

      // Shield Modal buttons
      this.shieldAcceptBtn.addEventListener('click', () => this.resolveShieldChoice(true));
      this.shieldDeclineBtn.addEventListener('click', () => this.resolveShieldChoice(false));

      // Play Again
      this.playAgainBtn.addEventListener('click', () => this.resetMatch());

      // Clear Log
      document.getElementById('clear-log-btn').addEventListener('click', () => {
        this.logFeed.innerHTML = '';
      });

      // Canvas Tooltip Hover
      this.boardCanvas.addEventListener('mousemove', (e) => this.handleCanvasHover(e));
      this.boardCanvas.addEventListener('mouseleave', () => {
        this.tooltip.style.display = 'none';
      });

      // Sound Toggle Button
      const audioBtn = document.getElementById('audio-toggle-btn');
      const audioIcon = document.getElementById('audio-icon');
      audioIcon.textContent = sound.enabled ? '🔊' : '🔇';
      audioBtn.addEventListener('click', () => {
        const en = sound.toggle();
        audioIcon.textContent = en ? '🔊' : '🔇';
        showToast(en ? 'Sound Unmuted' : 'Sound Muted');
      });

      // Fullscreen
      document.getElementById('fullscreen-btn').addEventListener('click', () => {
        if (!document.fullscreenElement) {
          document.documentElement.requestFullscreen().catch(() => {});
        } else {
          document.exitFullscreen().catch(() => {});
        }
      });

      // Navigation Sheets
      const labSheet = document.getElementById('lab-sheet');
      const howSheet = document.getElementById('how-sheet');
      const navGameBtn = document.getElementById('nav-game-btn');
      const navLabBtn = document.getElementById('nav-lab-btn');
      const navHowBtn = document.getElementById('nav-how-btn');

      const openTab = (sheet) => {
        labSheet.classList.remove('open');
        howSheet.classList.remove('open');
        navGameBtn.classList.remove('active');
        navLabBtn.classList.remove('active');
        navHowBtn.classList.remove('active');

        if (sheet === 'lab') {
          labSheet.classList.add('open');
          navLabBtn.classList.add('active');
        } else if (sheet === 'how') {
          howSheet.classList.add('open');
          navHowBtn.classList.add('active');
        } else {
          navGameBtn.classList.add('active');
        }
      };

      navGameBtn.addEventListener('click', () => openTab('game'));
      navLabBtn.addEventListener('click', () => openTab('lab'));
      navHowBtn.addEventListener('click', () => openTab('how'));
      document.getElementById('lab-close-btn').addEventListener('click', () => openTab('game'));
      document.getElementById('how-close-btn').addEventListener('click', () => openTab('game'));

      // Keyboard Shortcuts
      window.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT') return;
        const key = e.key.toUpperCase();

        if (key === 'ESCAPE') {
          openTab('game');
          this.shieldModal.classList.remove('open');
          return;
        }

        if (this.state === 'SHIELD_PROMPT') {
          if (key === 'Y') this.resolveShieldChoice(true);
          if (key === 'N') this.resolveShieldChoice(false);
          return;
        }

        if (key === ' ' || key === 'ENTER') {
          if (this.currentTurn === 'HUMAN' && this.state === 'IDLE') {
            e.preventDefault();
            this.handleRollDice();
          }
        } else if (key === '1') {
          if (this.state === 'CHOOSING') this.chooseDie(0);
        } else if (key === '2') {
          if (this.state === 'CHOOSING') this.chooseDie(1);
        } else if (key === 'H') {
          this.toggleHeatmapBtn.click();
        } else if (key === 'P') {
          this.toggleBfsBtn.click();
        } else if (key === 'M') {
          audioBtn.click();
        }
      });
    }

    // --- Interactive Tooltip on Hover ---
    handleCanvasHover(e) {
      const rect = this.boardCanvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const cellSize = this.canvasSize / BOARD_SIZE;

      const col = Math.floor(x / cellSize);
      const rowFromTop = Math.floor(y / cellSize);
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
      const hazard = GAME_AI_DATA.hazards[cell] || 0;

      let extra = '';
      if (SNAKES[cell]) extra = `<div style="color:var(--rose);">🐍 Snake head &rarr; Drop to ${SNAKES[cell]}</div>`;
      if (LADDERS[cell]) extra = `<div style="color:var(--gold);">🪜 Ladder base &rarr; Climb to ${LADDERS[cell]}</div>`;

      this.tooltip.innerHTML = `
        <div style="display:flex; justify-content:space-between; gap:12px; margin-bottom:4px;">
          <strong style="font-size:0.9rem; color:var(--cyan);">Cell ${cell}</strong>
          <span class="risk-tag risk-${zone}">${zone}</span>
        </div>
        ${extra}
        <div style="font-size:0.75rem; color:var(--text-muted); display:grid; grid-template-columns:auto auto; gap:2px 10px;">
          <span>Min Rolls to Goal:</span><strong style="color:var(--text-main);">${bfs}</strong>
          <span>A* Route Score:</span><strong style="color:var(--text-main);">${astar}</strong>
          <span>Win Probability:</span><strong style="color:var(--text-main);">${prob}%</strong>
          <span>Hazard Rating:</span><strong style="color:var(--text-main);">${hazard}</strong>
        </div>
      `;

      this.tooltip.style.display = 'block';
      this.tooltip.style.left = `${Math.min(e.clientX + 14, window.innerWidth - 220)}px`;
      this.tooltip.style.top = `${e.clientY + 14}px`;
    }

    // --- Dice Animation & Turn Mechanics ---
    handleRollDice() {
      if (this.state !== 'IDLE') return;
      sound.play('dice');
      this.state = 'ROLLING';
      this.rollBtn.disabled = true;

      this.die1Box.classList.add('rolling');
      this.die2Box.classList.add('rolling');

      // Rolling shuffle
      let ticks = 0;
      const interval = setInterval(() => {
        const v1 = Math.floor(Math.random() * 6) + 1;
        const v2 = Math.floor(Math.random() * 6) + 1;
        this.die1Box.setAttribute('data-val', v1);
        this.die2Box.setAttribute('data-val', v2);
        ticks++;
        if (ticks > 9) {
          clearInterval(interval);
          this.finalizeDiceRoll();
        }
      }, 55);
    }

    finalizeDiceRoll() {
      this.die1Box.classList.remove('rolling');
      this.die2Box.classList.remove('rolling');

      const d1 = Math.floor(Math.random() * 6) + 1;
      const d2 = Math.floor(Math.random() * 6) + 1;
      this.currentDice = [d1, d2];
      this.die1Box.setAttribute('data-val', d1);
      this.die2Box.setAttribute('data-val', d2);

      const pos = this.currentTurn === 'HUMAN' ? this.humanPos : this.aiPos;
      const shields = this.currentTurn === 'HUMAN' ? this.humanShields : this.aiShields;

      this.log(`${this.currentTurn === 'HUMAN' ? 'You' : 'AI'} rolled [${d1}] and [${d2}]`, 'pill-roll', 'Roll');

      // Evaluate both candidate moves
      const cands = [
        this.evaluateMovePlan(pos, 0, d1, shields),
        this.evaluateMovePlan(pos, 1, d2, shields)
      ];

      if (this.currentTurn === 'HUMAN') {
        this.presentHumanChoices(cands);
      } else {
        this.runAiDecision(cands);
      }
    }

    evaluateMovePlan(pos, dieIdx, dieVal, shields) {
      const landing = pos + dieVal;
      if (landing > GOAL_CELL) {
        return {
          dieIdx,
          dieVal,
          valid: false,
          landing: 0,
          dest: pos,
          special: 'NONE',
          note: `Overshoots cell 100 (${landing}) - illegal`,
          astarScore: 0,
          winProb: 0,
          zone: '-',
          finalScore: -1
        };
      }

      let dest = landing;
      let special = 'NONE';
      let note = 'Plain move';

      if (SNAKES[landing]) {
        special = 'SNAKE';
        dest = SNAKES[landing];
        note = `Snake at ${landing} &rarr; drops to ${dest}`;
      } else if (LADDERS[landing]) {
        special = 'LADDER';
        dest = LADDERS[landing];
        note = `Ladder at ${landing} &rarr; climbs to ${dest}`;
      }

      if (dest === GOAL_CELL) {
        note = 'Reaches cell 100 - Winning move!';
      }

      const astarScore = GAME_AI_DATA.astar_scores[dest] || 0;
      const winProb = GAME_AI_DATA.win_prob[dest] || 0;
      const zone = GAME_AI_DATA.zones[dest] || 'SAFE';
      const finalScore = WEIGHT_ASTAR * astarScore + WEIGHT_LOGISTIC * winProb;

      return {
        dieIdx,
        dieVal,
        valid: true,
        landing,
        dest,
        special,
        note,
        astarScore,
        winProb,
        zone,
        finalScore
      };
    }

    presentHumanChoices(cands) {
      this.state = 'CHOOSING';
      this.candidateGrid.style.display = 'grid';
      this.actionTitle.textContent = 'Select Your Move';
      this.turnSubtitle.textContent = 'Pick die 1 or 2 (press 1 or 2 or click a card)';

      // Setup Die 1
      this.candVal1.textContent = cands[0].dieVal;
      if (!cands[0].valid) {
        this.candCard1.classList.add('disabled');
        this.candTarget1.textContent = 'Illegal Overshoot';
        this.candNote1.textContent = cands[0].note;
        this.chooseDie1Btn.disabled = true;
      } else {
        this.candCard1.classList.remove('disabled');
        this.candTarget1.textContent = `Target: Cell ${cands[0].landing} (${cands[0].zone})`;
        this.candNote1.textContent = cands[0].note;
        this.chooseDie1Btn.disabled = false;
      }

      // Setup Die 2
      this.candVal2.textContent = cands[1].dieVal;
      if (!cands[1].valid) {
        this.candCard2.classList.add('disabled');
        this.candTarget2.textContent = 'Illegal Overshoot';
        this.candNote2.textContent = cands[1].note;
        this.chooseDie2Btn.disabled = true;
      } else {
        this.candCard2.classList.remove('disabled');
        this.candTarget2.textContent = `Target: Cell ${cands[1].landing} (${cands[1].zone})`;
        this.candNote2.textContent = cands[1].note;
        this.chooseDie2Btn.disabled = false;
      }

      // Both invalid: skip turn
      if (!cands[0].valid && !cands[1].valid) {
        showToast('Both dice overshoot cell 100! Turn skipped.');
        this.log('Both dice overshoot 100 - turn skipped.', 'pill-roll', 'Skip');
        setTimeout(() => this.endTurn(), 1400);
      }
    }

    previewCandidate(dieIdx) {
      if (this.state !== 'CHOOSING') return;
      const c = this.evaluateMovePlan(this.humanPos, dieIdx, this.currentDice[dieIdx], this.humanShields);
      if (c.valid) {
        this.ghostPreviewCell = c.dest;
      }
    }

    clearPreview() {
      this.ghostPreviewCell = null;
    }

    chooseDie(dieIdx) {
      if (this.state !== 'CHOOSING' && this.currentTurn !== 'HUMAN') return;
      const c = this.evaluateMovePlan(this.humanPos, dieIdx, this.currentDice[dieIdx], this.humanShields);
      if (!c.valid) return;

      this.clearPreview();
      this.candidateGrid.style.display = 'none';
      sound.play('click');
      this.executeMove('HUMAN', c);
    }

    // --- AI Turn Simulation ---
    runAiDecision(cands) {
      this.state = 'ANIMATING';
      sound.play('ai');

      // Update AI Transparent Analysis Panel
      this.updateAiAnalysisPanel(cands);

      // AI Decision Logic (BFS + A* + Logistic Regression + Threshold)
      setTimeout(() => {
        const valid = cands.filter(c => c.valid);
        if (valid.length === 0) {
          showToast('AI cannot move: both dice overshoot cell 100.');
          this.log('AI turn skipped (both dice overshoot 100).', 'pill-ai', 'AI');
          this.aiReasonQuote.textContent = 'Both dice overshoot cell 100. No legal moves available.';
          setTimeout(() => this.endTurn(), 1200);
          return;
        }

        let chosen = null;
        if (valid.length === 1) {
          chosen = valid[0];
          this.aiReasonQuote.textContent = `Die ${chosen.dieVal} is the only legal choice (other die overshoots).`;
        } else {
          // Compare winning move first, then highest final score
          valid.sort((a, b) => {
            if (a.dest === GOAL_CELL) return -1;
            if (b.dest === GOAL_CELL) return 1;
            return b.finalScore - a.finalScore;
          });
          chosen = valid[0];
          const other = valid[1];

          if (chosen.dest === GOAL_CELL) {
            this.aiReasonQuote.textContent = `Die ${chosen.dieVal} reaches cell 100 - immediate winning move!`;
          } else {
            this.aiReasonQuote.textContent = `AI selected Die ${chosen.dieVal} (Score: ${chosen.finalScore.toFixed(3)} vs ${other.finalScore.toFixed(3)}). A* safe route: ${chosen.astarScore.toFixed(2)}, ML win prob: ${(chosen.winProb * 100).toFixed(1)}%.`;
          }
        }

        // Highlight chosen box
        this.aiBoxes[chosen.dieIdx].classList.add('ai-chosen');
        this.log(`AI evaluated candidate moves and chose Die ${chosen.dieVal}.`, 'pill-ai', 'AI');

        setTimeout(() => {
          this.executeMove('AI', chosen);
        }, 800);
      }, 700);
    }

    updateAiAnalysisPanel(cands) {
      this.aiBoxes.forEach((box, i) => {
        box.classList.remove('ai-chosen');
        const c = cands[i];
        document.getElementById(`ai-lbl-${i}`).textContent = `Candidate ${'AB'[i]} (Die ${c.dieVal})`;

        const zoneTag = document.getElementById(`ai-zone-${i}`);
        zoneTag.className = `risk-tag risk-${c.zone}`;
        zoneTag.textContent = c.zone;

        document.getElementById(`ai-astar-val-${i}`).textContent = c.astarScore.toFixed(3);
        document.getElementById(`ai-astar-fill-${i}`).style.width = `${c.astarScore * 100}%`;

        document.getElementById(`ai-win-val-${i}`).textContent = `${(c.winProb * 100).toFixed(1)}%`;
        document.getElementById(`ai-win-fill-${i}`).style.width = `${c.winProb * 100}%`;

        document.getElementById(`ai-score-val-${i}`).textContent = c.finalScore >= 0 ? c.finalScore.toFixed(3) : 'Illegal';
        document.getElementById(`ai-score-fill-${i}`).style.width = `${Math.max(0, c.finalScore) * 100}%`;
      });
    }

    // --- Move Execution & Animation Sequence ---
    executeMove(player, movePlan) {
      this.state = 'ANIMATING';
      const fromCell = player === 'HUMAN' ? this.humanPos : this.aiPos;
      const landingCell = movePlan.landing;

      this.log(`${player === 'HUMAN' ? 'You' : 'AI'} plays die ${movePlan.dieVal} (hop to cell ${landingCell})`, 'pill-roll', 'Move');

      // 1. Hop step-by-step from `fromCell` to `landingCell`
      this.animateHopPath(player, fromCell, landingCell, () => {
        // Landed on `landingCell`. Check for special events
        if (movePlan.special === 'SNAKE') {
          this.handleSnakeEncounter(player, landingCell, movePlan.dest);
        } else if (movePlan.special === 'LADDER') {
          this.handleLadderClimb(player, landingCell, movePlan.dest);
        } else {
          this.finalizePlayerCell(player, landingCell);
        }
      });
    }

    animateHopPath(player, fromCell, toCell, onComplete) {
      const steps = [];
      for (let c = fromCell + 1; c <= toCell; c++) {
        steps.push(c);
      }

      let stepIdx = 0;
      const hopNext = () => {
        if (stepIdx >= steps.length) {
          onComplete();
          return;
        }
        const target = steps[stepIdx];
        sound.play('move');
        this.animateSingleHop(player, target, () => {
          stepIdx++;
          hopNext();
        });
      };
      hopNext();
    }

    animateSingleHop(player, targetCell, onComplete) {
      const targetCoord = this.getCellCenterFraction(targetCell);
      const token = this.tokenPos[player.toLowerCase()];
      const startX = token.x;
      const startY = token.y;
      const endX = targetCoord.x;
      const endY = targetCoord.y;

      const duration = 120; // ms
      const startTime = performance.now();

      this.activeAnimation = (now) => {
        const elapsed = now - startTime;
        const progress = Math.min(1, elapsed / duration);
        // Parabolic arc for hop effect
        const arc = Math.sin(progress * Math.PI) * 0.04;

        token.x = startX + (endX - startX) * progress;
        token.y = startY + (endY - startY) * progress - arc;

        if (progress >= 1) {
          token.x = endX;
          token.y = endY;
          this.activeAnimation = null;
          onComplete();
          return false;
        }
        return true;
      };
    }

    handleSnakeEncounter(player, head, tail) {
      const shields = player === 'HUMAN' ? this.humanShields : this.aiShields;

      if (player === 'HUMAN') {
        if (shields > 0) {
          // Offer shield modal
          this.state = 'SHIELD_PROMPT';
          this.pendingSnake = { player, head, tail };

          // AI Advisor calculation
          const keepScore = WEIGHT_ASTAR * (GAME_AI_DATA.astar_scores[head] || 0) + WEIGHT_LOGISTIC * (GAME_AI_DATA.win_prob[head] || 0);
          const dropScore = WEIGHT_ASTAR * (GAME_AI_DATA.astar_scores[tail] || 0) + WEIGHT_LOGISTIC * (GAME_AI_DATA.win_prob[tail] || 0);
          const benefit = keepScore - dropScore;
          let threshold = SHIELD_THRESHOLD[shields] || 0.16;
          if (head >= ENDGAME_CELL) threshold *= ENDGAME_FACTOR;

          const recommended = benefit >= threshold;
          this.shieldLossText.textContent = `Snake threat at cell ${head} &rarr; drops to ${tail} (loss of ${head - tail} cells)`;
          this.shieldAdvisorText.textContent = `Shield benefit ${benefit > 0 ? '+' : ''}${benefit.toFixed(3)} vs reserve threshold ${threshold.toFixed(3)}. Recommendation: ${recommended ? 'USE SHIELD' : 'KEEP IN RESERVE'}.`;

          this.shieldModal.classList.add('open');
          return;
        }
        // No shields available
        this.slideDownSnake(player, head, tail);
      } else {
        // AI automatically evaluates shield usage
        const keepScore = WEIGHT_ASTAR * (GAME_AI_DATA.astar_scores[head] || 0) + WEIGHT_LOGISTIC * (GAME_AI_DATA.win_prob[head] || 0);
        const dropScore = WEIGHT_ASTAR * (GAME_AI_DATA.astar_scores[tail] || 0) + WEIGHT_LOGISTIC * (GAME_AI_DATA.win_prob[tail] || 0);
        const benefit = keepScore - dropScore;
        let threshold = SHIELD_THRESHOLD[shields] || 0.16;
        if (head >= ENDGAME_CELL) threshold *= ENDGAME_FACTOR;

        const useShield = shields > 0 && benefit >= threshold;
        if (useShield) {
          this.aiShields--;
          this.updateShieldDisplays();
          sound.play('shield');
          this.log(`AI deployed shield 🛡️ to block snake at cell ${head}!`, 'pill-shield', 'Shield');
          showToast(`AI deployed shield to block snake at ${head}!`);
          this.finalizePlayerCell(player, head);
        } else {
          this.log(`AI saves shield (benefit ${benefit.toFixed(3)} < threshold ${threshold.toFixed(3)})`, 'pill-ai', 'AI');
          this.slideDownSnake(player, head, tail);
        }
      }
    }

    resolveShieldChoice(use) {
      this.shieldModal.classList.remove('open');
      const { player, head, tail } = this.pendingSnake;
      this.pendingSnake = null;

      if (use && this.humanShields > 0) {
        this.humanShields--;
        this.updateShieldDisplays();
        sound.play('shield');
        this.log(`You activated shield 🛡️! Preserved cell ${head}.`, 'pill-shield', 'Shield');
        showToast(`Shield activated! Safe at cell ${head}.`);
        this.finalizePlayerCell(player, head);
      } else {
        this.log(`You declined shield. Sliding down snake to cell ${tail}.`, 'pill-snake', 'Snake');
        this.slideDownSnake(player, head, tail);
      }
    }

    slideDownSnake(player, head, tail) {
      sound.play('snake');
      showToast(`Bitten by snake at ${head}! Slid down to ${tail}.`);
      this.log(`${player === 'HUMAN' ? 'You' : 'AI'} slid down snake from ${head} to ${tail}`, 'pill-snake', 'Snake');

      // Curve slide animation
      const curve = this.snakeCurves[head];
      if (!curve) {
        this.finalizePlayerCell(player, tail);
        return;
      }

      const pts = curve.pts;
      const duration = 650;
      const startTime = performance.now();
      const token = this.tokenPos[player.toLowerCase()];

      this.activeAnimation = (now) => {
        const elapsed = now - startTime;
        const progress = Math.min(1, elapsed / duration);
        const idx = Math.min(pts.length - 1, Math.floor(progress * (pts.length - 1)));

        token.x = pts[idx].x;
        token.y = pts[idx].y;

        if (progress >= 1) {
          const finalCoord = this.getCellCenterFraction(tail);
          token.x = finalCoord.x;
          token.y = finalCoord.y;
          this.activeAnimation = null;
          this.finalizePlayerCell(player, tail);
          return false;
        }
        return true;
      };
    }

    handleLadderClimb(player, bottom, top) {
      sound.play('ladder');
      showToast(`🪜 Ladder climbed from ${bottom} up to ${top}!`);
      this.log(`${player === 'HUMAN' ? 'You' : 'AI'} climbed ladder from ${bottom} up to ${top}!`, 'pill-ladder', 'Ladder');

      const p1 = this.getCellCenterFraction(bottom);
      const p2 = this.getCellCenterFraction(top);
      const duration = 600;
      const startTime = performance.now();
      const token = this.tokenPos[player.toLowerCase()];

      this.activeAnimation = (now) => {
        const elapsed = now - startTime;
        const progress = Math.min(1, elapsed / duration);

        token.x = p1.x + (p2.x - p1.x) * progress;
        token.y = p1.y + (p2.y - p1.y) * progress;

        if (progress >= 1) {
          token.x = p2.x;
          token.y = p2.y;
          this.activeAnimation = null;
          this.finalizePlayerCell(player, top);
          return false;
        }
        return true;
      };
    }

    finalizePlayerCell(player, cell) {
      if (player === 'HUMAN') {
        this.humanPos = cell;
        this.humanPosVal.textContent = cell;
        this.humanProgressBar.style.width = `${cell}%`;
      } else {
        this.aiPos = cell;
        this.aiPosVal.textContent = cell;
        this.aiProgressBar.style.width = `${cell}%`;
      }

      // Check win condition
      if (cell === GOAL_CELL) {
        this.triggerVictory(player);
        return;
      }

      this.endTurn();
    }

    updateShieldDisplays() {
      this.humanShield1.className = `shield-badge ${this.humanShields < 1 ? 'depleted' : ''}`;
      this.humanShield2.className = `shield-badge ${this.humanShields < 2 ? 'depleted' : ''}`;
      this.aiShield1.className = `shield-badge ${this.aiShields < 1 ? 'depleted' : ''}`;
      this.aiShield2.className = `shield-badge ${this.aiShields < 2 ? 'depleted' : ''}`;
    }

    endTurn() {
      this.currentTurn = this.currentTurn === 'HUMAN' ? 'AI' : 'HUMAN';
      this.state = 'IDLE';

      if (this.currentTurn === 'HUMAN') {
        this.humanCard.classList.add('active-turn');
        this.aiCard.classList.remove('active-turn');
        this.rollBtn.disabled = false;
        this.actionTitle.textContent = 'Dual Dice Roll';
        this.turnSubtitle.textContent = 'Roll dual dice to make your move';
      } else {
        this.aiCard.classList.add('active-turn');
        this.humanCard.classList.remove('active-turn');
        this.rollBtn.disabled = true;
        this.actionTitle.textContent = 'AI Turn Active';
        this.turnSubtitle.textContent = 'AI is calculating search paths and probabilities...';

        // Automatically trigger AI turn
        setTimeout(() => this.handleRollDice(), 600);
      }
    }

    triggerVictory(winner) {
      this.state = 'GAMEOVER';
      sound.play('victory');

      const isHuman = winner === 'HUMAN';
      this.gameoverEmoji.textContent = isHuman ? '🏆' : '🤖';
      this.gameoverTitle.textContent = isHuman ? 'Victory! You Won!' : 'AI Claimed Victory!';
      this.gameoverTitle.style.color = isHuman ? 'var(--cyan)' : 'var(--magenta)';
      this.gameoverDesc.textContent = isHuman
        ? 'Congratulations! Your strategy and tactical shield management defeated the AI agent.'
        : 'The AI achieved an exact finish on cell 100 using search heuristics and probability scoring.';

      this.gameoverModal.classList.add('open');
      this.log(`Match finished! ${winner} reached cell 100.`, 'pill-shield', 'Win');
    }

    resetMatch() {
      this.gameoverModal.classList.remove('open');
      this.humanPos = START_CELL;
      this.aiPos = START_CELL;
      this.humanShields = 2;
      this.aiShields = 2;
      this.currentTurn = 'HUMAN';
      this.state = 'IDLE';

      this.humanPosVal.textContent = START_CELL;
      this.aiPosVal.textContent = START_CELL;
      this.humanProgressBar.style.width = '1%';
      this.aiProgressBar.style.width = '1%';
      this.updateShieldDisplays();

      this.humanCard.classList.add('active-turn');
      this.aiCard.classList.remove('active-turn');
      this.rollBtn.disabled = false;
      this.candidateGrid.style.display = 'none';

      this.tokenPos.human = { ...this.getCellCenterFraction(START_CELL) };
      this.tokenPos.ai = { ...this.getCellCenterFraction(START_CELL) };

      this.log('New match started. Good luck!', 'pill-ai', 'Match');
    }

    // --- HTML5 Canvas Rendering ---
    render(now) {
      if (this.activeAnimation) {
        this.activeAnimation(now);
      }

      this.ctx.clearRect(0, 0, this.canvasSize, this.canvasSize);

      const cs = this.canvasSize / BOARD_SIZE;

      // 1. Draw Cells
      for (let cell = 1; cell <= NUM_CELLS; cell++) {
        const { row, col } = cellToGrid(cell);
        const x = col * cs;
        const y = (BOARD_SIZE - 1 - row) * cs;

        // Base cell background
        let bg = (row + col) % 2 === 0 ? COLORS.cellEven : COLORS.cellOdd;
        if (SNAKES[cell]) bg = COLORS.cellHead;
        else if (Object.values(SNAKES).includes(cell)) bg = COLORS.cellTail;
        else if (LADDERS[cell]) bg = COLORS.cellBottom;
        else if (Object.values(LADDERS).includes(cell)) bg = COLORS.cellTop;
        if (cell === 100) bg = COLORS.cellGoal;
        if (cell === 1) bg = COLORS.cellStart;

        // Heatmap overlay
        if (this.showHeatmap) {
          const zone = GAME_AI_DATA.zones[cell];
          if (zone === 'DANGER') bg = this.blendColors(bg, '#ff3b5c', 0.45);
          else if (zone === 'ADVANTAGE') bg = this.blendColors(bg, '#10b981', 0.45);
          else bg = this.blendColors(bg, '#3b82f6', 0.25);
        }

        this.ctx.fillStyle = bg;
        this.ctx.beginPath();
        this.ctx.roundRect(x + 2, y + 2, cs - 4, cs - 4, 6);
        this.ctx.fill();

        // Border
        this.ctx.strokeStyle = (SNAKES[cell] || LADDERS[cell] || cell === 1 || cell === 100)
          ? 'rgba(255, 255, 255, 0.35)'
          : 'rgba(255, 255, 255, 0.07)';
        this.ctx.lineWidth = 1;
        this.ctx.stroke();

        // Cell Number
        this.ctx.fillStyle = 'rgba(234, 240, 255, 0.85)';
        this.ctx.font = `bold ${Math.max(10, Math.floor(cs * 0.24))}px Outfit, sans-serif`;
        this.ctx.textAlign = 'left';
        this.ctx.textBaseline = 'top';
        this.ctx.fillText(cell.toString(), x + 6, y + 5);

        // Cell Marker badge
        if (cell === 100) {
          this.ctx.fillStyle = '#ffce60';
          this.ctx.font = `bold ${Math.max(9, Math.floor(cs * 0.18))}px Outfit, sans-serif`;
          this.ctx.textAlign = 'center';
          this.ctx.fillText('★ GOAL', x + cs / 2, y + cs - 14);
        } else if (cell === 1) {
          this.ctx.fillStyle = '#54eca4';
          this.ctx.font = `bold ${Math.max(9, Math.floor(cs * 0.18))}px Outfit, sans-serif`;
          this.ctx.textAlign = 'center';
          this.ctx.fillText('START', x + cs / 2, y + cs - 14);
        } else if (SNAKES[cell]) {
          this.ctx.fillStyle = '#ff5e74';
          this.ctx.font = `${Math.floor(cs * 0.28)}px sans-serif`;
          this.ctx.textAlign = 'right';
          this.ctx.fillText('🐍', x + cs - 5, y + cs - 8);
        } else if (LADDERS[cell]) {
          this.ctx.fillStyle = '#ffce60';
          this.ctx.font = `${Math.floor(cs * 0.28)}px sans-serif`;
          this.ctx.textAlign = 'right';
          this.ctx.fillText('🪜', x + cs - 5, y + cs - 8);
        }
      }

      // 2. Draw Ladders
      for (const [bottom, { p1, p2 }] of Object.entries(this.ladderLines)) {
        const x1 = p1.x * this.canvasSize;
        const y1 = p1.y * this.canvasSize;
        const x2 = p2.x * this.canvasSize;
        const y2 = p2.y * this.canvasSize;

        const dx = x2 - x1;
        const dy = y2 - y1;
        const dist = Math.hypot(dx, dy);
        const nx = -dy / dist * 8;
        const ny = dx / dist * 8;

        // Ladder rails
        this.ctx.strokeStyle = '#f59e0b';
        this.ctx.lineWidth = 3.5;
        this.ctx.shadowColor = 'rgba(245, 158, 11, 0.4)';
        this.ctx.shadowBlur = 6;

        this.ctx.beginPath();
        this.ctx.moveTo(x1 + nx, y1 + ny);
        this.ctx.lineTo(x2 + nx, y2 + ny);
        this.ctx.moveTo(x1 - nx, y1 - ny);
        this.ctx.lineTo(x2 - nx, y2 - ny);
        this.ctx.stroke();

        // Rungs
        const rungs = Math.max(3, Math.floor(dist / 22));
        this.ctx.lineWidth = 2.5;
        this.ctx.strokeStyle = '#fde68a';
        for (let r = 1; r < rungs; r++) {
          const t = r / rungs;
          const rx = x1 + dx * t;
          const ry = y1 + dy * t;
          this.ctx.beginPath();
          this.ctx.moveTo(rx + nx, ry + ny);
          this.ctx.lineTo(rx - nx, ry - ny);
          this.ctx.stroke();
        }
        this.ctx.shadowBlur = 0;
      }

      // 3. Draw Snakes
      for (const [head, { pts, colors }] of Object.entries(this.snakeCurves)) {
        this.ctx.lineWidth = Math.max(6, cs * 0.15);
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
        for (let i = 1; i < pts.length; i++) {
          this.ctx.lineTo(pts[i].x * this.canvasSize, pts[i].y * this.canvasSize);
        }
        this.ctx.stroke();
        this.ctx.shadowBlur = 0;

        // Snake Head (at pts[0])
        const hx = pts[0].x * this.canvasSize;
        const hy = pts[0].y * this.canvasSize;
        this.ctx.fillStyle = colors[0];
        this.ctx.beginPath();
        this.ctx.arc(hx, hy, cs * 0.18, 0, Math.PI * 2);
        this.ctx.fill();

        // Eyes
        this.ctx.fillStyle = '#ffffff';
        this.ctx.beginPath();
        this.ctx.arc(hx - 3, hy - 2, 2.2, 0, Math.PI * 2);
        this.ctx.arc(hx + 3, hy - 2, 2.2, 0, Math.PI * 2);
        this.ctx.fill();
        this.ctx.fillStyle = '#000000';
        this.ctx.beginPath();
        this.ctx.arc(hx - 3, hy - 2, 1.2, 0, Math.PI * 2);
        this.ctx.arc(hx + 3, hy - 2, 1.2, 0, Math.PI * 2);
        this.ctx.fill();
      }

      // 4. Draw BFS Overlay Path (if toggled)
      if (this.showBFS) {
        const curCell = this.currentTurn === 'HUMAN' ? this.humanPos : this.aiPos;
        const path = GAME_AI_DATA.bfs_paths[curCell];
        if (path && path.length > 1) {
          this.ctx.strokeStyle = '#ffce60';
          this.ctx.lineWidth = 3;
          this.ctx.setLineDash([6, 6]);
          this.ctx.lineDashOffset = -now / 30;
          this.ctx.beginPath();

          for (let i = 0; i < path.length; i++) {
            const coord = this.getCellCenterFraction(path[i]);
            const px = coord.x * this.canvasSize;
            const py = coord.y * this.canvasSize;
            if (i === 0) this.ctx.moveTo(px, py);
            else this.ctx.lineTo(px, py);
          }
          this.ctx.stroke();
          this.ctx.setLineDash([]);
        }
      }

      // 5. Draw Ghost Preview Marker
      if (this.ghostPreviewCell) {
        const gc = this.getCellCenterFraction(this.ghostPreviewCell);
        const gx = gc.x * this.canvasSize;
        const gy = gc.y * this.canvasSize;
        this.ctx.strokeStyle = COLORS.cyan;
        this.ctx.lineWidth = 2.5;
        this.ctx.shadowColor = COLORS.cyan;
        this.ctx.shadowBlur = 12;
        this.ctx.beginPath();
        this.ctx.arc(gx, gy, cs * 0.32, 0, Math.PI * 2);
        this.ctx.stroke();
        this.ctx.shadowBlur = 0;
      }

      // 6. Draw Player Tokens
      this.drawPlayerToken(this.tokenPos.human.x * this.canvasSize, this.tokenPos.human.y * this.canvasSize, COLORS.cyan, 'P', now);
      this.drawPlayerToken(this.tokenPos.ai.x * this.canvasSize, this.tokenPos.ai.y * this.canvasSize, COLORS.magenta, 'AI', now);

      requestAnimationFrame(this.render);
    }

    drawPlayerToken(x, y, color, label, now) {
      const cs = this.canvasSize / BOARD_SIZE;
      const radius = cs * 0.26;

      // Outer Pulsing Glow
      const pulse = Math.sin(now / 200) * 3;
      this.ctx.beginPath();
      this.ctx.arc(x, y, radius + 4 + pulse, 0, Math.PI * 2);
      this.ctx.fillStyle = color === COLORS.cyan ? 'rgba(72, 222, 255, 0.18)' : 'rgba(218, 96, 255, 0.18)';
      this.ctx.fill();

      // Main Token Body
      const grad = this.ctx.createRadialGradient(x - 3, y - 3, 2, x, y, radius);
      grad.addColorStop(0, '#ffffff');
      grad.addColorStop(0.3, color);
      grad.addColorStop(1, '#0b0f24');
      this.ctx.fillStyle = grad;
      this.ctx.beginPath();
      this.ctx.arc(x, y, radius, 0, Math.PI * 2);
      this.ctx.fill();

      // Border
      this.ctx.strokeStyle = color;
      this.ctx.lineWidth = 2.5;
      this.ctx.stroke();

      // Text label
      this.ctx.fillStyle = '#ffffff';
      this.ctx.font = `bold ${Math.max(9, Math.floor(radius * 0.95))}px Outfit, sans-serif`;
      this.ctx.textAlign = 'center';
      this.ctx.textBaseline = 'middle';
      this.ctx.fillText(label, x, y + 1);
    }

    blendColors(c1, c2, weight) {
      return c2;
    }

    // --- AI Lab Setup & Binding ---
    initLabContent() {
      // Lab Tab Switching
      const tabBtns = document.querySelectorAll('.lab-tab-btn');
      tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
          tabBtns.forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          const tab = btn.getAttribute('data-tab');
          document.querySelectorAll('.lab-tab-panel').forEach(p => p.classList.remove('active'));
          document.getElementById(`tab-${tab}`).classList.add('active');
          sound.play('click');
        });
      });

      // BFS Slider
      const bfsSlider = document.getElementById('bfs-slider');
      const bfsVal = document.getElementById('bfs-slider-val');
      const bfsOut = document.getElementById('bfs-path-output');

      const updateBfsInspector = (c) => {
        bfsVal.textContent = `Cell ${c}`;
        const path = GAME_AI_DATA.bfs_paths[c] || [c];
        const rolls = GAME_AI_DATA.bfs_rolls[c] || 0;
        bfsOut.innerHTML = `<strong>Min Rolls to Goal:</strong> ${rolls} rolls<br><strong>Shortest Path:</strong> ${path.join(' &rarr; ')}`;
      };

      bfsSlider.addEventListener('input', (e) => updateBfsInspector(parseInt(e.target.value, 10)));
      updateBfsInspector(1);

      // Model Metrics
      const m = GAME_AI_DATA.metrics;
      if (m) {
        document.getElementById('metric-accuracy').textContent = `${(m.accuracy * 100).toFixed(1)} %`;
        document.getElementById('metric-baseline').textContent = `Majority Baseline: ${(m.baseline_accuracy * 100).toFixed(1)}%`;
        document.getElementById('metric-auc').textContent = m.roc_auc.toFixed(3);
        document.getElementById('metric-train').textContent = (m.n_train + m.n_test).toLocaleString();
        document.getElementById('metric-f1').textContent = `${m.precision.toFixed(3)} / ${m.recall.toFixed(3)} / ${m.f1.toFixed(3)}`;

        // Confusion matrix
        if (m.confusion) {
          document.getElementById('cm-tn').textContent = `${m.confusion[0][0].toLocaleString()} (TN)`;
          document.getElementById('cm-fp').textContent = `${m.confusion[0][1].toLocaleString()} (FP)`;
          document.getElementById('cm-fn').textContent = `${m.confusion[1][0].toLocaleString()} (FN)`;
          document.getElementById('cm-tp').textContent = `${m.confusion[1][1].toLocaleString()} (TP)`;
        }

        // Coefficients list
        const coefContainer = document.getElementById('coef-list');
        coefContainer.innerHTML = '';
        if (m.coefficients) {
          for (const [feat, val] of Object.entries(m.coefficients)) {
            const row = document.createElement('div');
            row.style.display = 'flex';
            row.style.justifyContent = 'space-between';
            row.style.alignItems = 'center';
            row.innerHTML = `
              <span><code>${feat}</code></span>
              <strong style="color:${val >= 0 ? 'var(--emerald)' : 'var(--rose)'};">${val >= 0 ? '+' : ''}${val.toFixed(4)}</strong>
            `;
            coefContainer.appendChild(row);
          }
        }
      }

      // K-Means Cluster Cards
      const clusterCards = document.getElementById('cluster-cards-container');
      clusterCards.innerHTML = '';
      if (GAME_AI_DATA.cluster_profiles) {
        GAME_AI_DATA.cluster_profiles.forEach(p => {
          const card = document.createElement('div');
          card.className = 'stat-card';
          const zoneColor = p.zone === 'DANGER' ? 'var(--rose)' : p.zone === 'ADVANTAGE' ? 'var(--emerald)' : 'var(--blue)';
          card.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span class="risk-tag risk-${p.zone}" style="font-size:0.85rem;">ZONE ${p.zone}</span>
              <strong style="color:${zoneColor};">${p.size} Cells</strong>
            </div>
            <div style="font-size:0.8rem; color:var(--text-muted); margin-top:6px;">Mean Hazard Score: <strong>${p.hazard}</strong></div>
            <div style="font-size:0.75rem; color:var(--text-dim); margin-top:6px;">
              Sample Cells: ${p.cells.slice(0, 10).join(', ')}...
            </div>
          `;
          clusterCards.appendChild(card);
        });
      }
    }
  }

  // Initialize on load
  window.addEventListener('DOMContentLoaded', () => {
    new AmbientParticles(document.getElementById('ambient-canvas'));
    new GameEngine();
  });
})();
