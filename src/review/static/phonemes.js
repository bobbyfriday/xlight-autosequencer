'use strict';

// ── Constants ─────────────────────────────────────────────────────────────────

const PX_PER_SEC    = 100;
const AXIS_H        = 20;
const WORD_H        = 48;
const PHONEME_H     = 48;
const TRACK_H       = 36;
const MAX_TRACKS    = 14;

const PHONEME_COLORS = {
  AI:  '#e67e22',
  E:   '#f1c40f',
  O:   '#3498db',
  WQ:  '#9b59b6',
  L:   '#27ae60',
  MBP: '#e74c3c',
  FV:  '#1abc9c',
  etc: '#3a3a3a',
};

// ── DOM refs ──────────────────────────────────────────────────────────────────

const player      = document.getElementById('player');
const btnPlay     = document.getElementById('btn-play');
const btnFullMix  = document.getElementById('btn-full-mix');
const btnVocals   = document.getElementById('btn-vocals');
const timeDisplay = document.getElementById('time-display');
const lyricsWrap  = document.getElementById('lyrics-wrap');
const panel       = document.getElementById('panel');
const canvasWrap  = document.getElementById('canvas-wrap');
const bgCanvas    = document.getElementById('bg-canvas');
const fgCanvas    = document.getElementById('fg-canvas');
const bgCtx       = bgCanvas.getContext('2d');
const fgCtx       = fgCanvas.getContext('2d');
const statusEl    = document.getElementById('status');

// ── State ─────────────────────────────────────────────────────────────────────

let wordMarks    = [];
let phonemeMarks = [];
let tracks       = [];
let durationMs   = 0;
let hasVocals    = false;
let usingVocals  = false;

// ── Init ──────────────────────────────────────────────────────────────────────

async function init() {
  let phonemeData, analysisData;
  try {
    const [pr, ar] = await Promise.all([fetch('/phonemes'), fetch('/analysis')]);
    if (!pr.ok) {
      const err = await pr.json().catch(() => ({}));
      statusEl.textContent = err.error || 'No phoneme data for this song. Re-analyze with Phonemes enabled.';
      return;
    }
    phonemeData  = await pr.json();
    analysisData = ar.ok ? await ar.json() : null;
  } catch (e) {
    statusEl.textContent = `Failed to load: ${e.message}`;
    return;
  }

  wordMarks    = phonemeData.word_track?.marks    || [];
  phonemeMarks = phonemeData.phoneme_track?.marks  || [];
  durationMs   = phonemeData.duration_ms           || 0;
  hasVocals    = phonemeData.has_vocals_audio       || false;
  tracks       = (analysisData?.timing_tracks || []).slice(0, MAX_TRACKS);

  document.getElementById('song-name').textContent = phonemeData.filename || '';
  document.title = `Phonemes — ${phonemeData.filename || 'xlight-analyze'}`;

  player.src = '/audio';

  if (!hasVocals) {
    btnVocals.disabled = true;
    btnVocals.title = 'No vocals stem — re-analyze with Stem Separation enabled';
  }

  renderLyrics();
  buildPanel();
  drawBackground();
  statusEl.style.display = 'none';
}

// ── Lyrics ────────────────────────────────────────────────────────────────────

function renderLyrics() {
  lyricsWrap.innerHTML = '';
  for (const wm of wordMarks) {
    const span = document.createElement('span');
    span.className = 'word';
    span.textContent = wm.label;
    span.dataset.start = wm.start_ms;
    span.dataset.end   = wm.end_ms;
    span.addEventListener('click', () => { player.currentTime = wm.start_ms / 1000; });
    lyricsWrap.appendChild(span);
  }
}

function updateLyrics(nowMs) {
  let activeEl = null;
  for (const el of lyricsWrap.querySelectorAll('.word')) {
    const s = +el.dataset.start;
    const e = +el.dataset.end;
    if (nowMs >= s && nowMs < e) {
      el.classList.add('active');
      el.classList.remove('past');
      activeEl = el;
    } else if (nowMs >= e) {
      el.classList.remove('active');
      el.classList.add('past');
    } else {
      el.classList.remove('active', 'past');
    }
  }
  if (activeEl) {
    activeEl.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }
}

// ── Panel ─────────────────────────────────────────────────────────────────────

function buildPanel() {
  panel.innerHTML = '';
  const lanes = [
    { label: 'Words',    h: WORD_H,     color: '#2855a5' },
    { label: 'Phonemes', h: PHONEME_H,  color: '#333' },
    ...tracks.map(t => ({ label: t.name, h: TRACK_H, color: '' })),
  ];
  for (const lane of lanes) {
    const div = document.createElement('div');
    div.className = 'lane-control';
    div.style.height = lane.h + 'px';
    div.style.minHeight = lane.h + 'px';
    if (lane.color) div.style.borderLeft = `2px solid ${lane.color}`;
    const nameEl = document.createElement('div');
    nameEl.className = 'lane-name';
    nameEl.textContent = lane.label;
    div.appendChild(nameEl);
    panel.appendChild(div);
  }
}

// ── Canvas ────────────────────────────────────────────────────────────────────

function canvasW() {
  return Math.max(canvasWrap.clientWidth,
    Math.ceil((durationMs / 1000) * PX_PER_SEC));
}

function canvasH() {
  return AXIS_H + WORD_H + PHONEME_H + tracks.length * TRACK_H;
}

function drawBackground() {
  const w = canvasW();
  const h = canvasH();
  bgCanvas.width  = fgCanvas.width  = w;
  bgCanvas.height = fgCanvas.height = h;

  bgCtx.clearRect(0, 0, w, h);

  // ── Time axis ──
  bgCtx.fillStyle = '#111';
  bgCtx.fillRect(0, 0, w, AXIS_H);
  bgCtx.font = '10px monospace';
  const stepS = 5;
  for (let s = 0; s * PX_PER_SEC <= w; s += stepS) {
    const x = s * PX_PER_SEC;
    bgCtx.fillStyle = '#2a2a2a';
    bgCtx.fillRect(x, 0, 1, AXIS_H);
    bgCtx.fillStyle = '#555';
    bgCtx.textAlign = 'left';
    const m = Math.floor(s / 60), sec = s % 60;
    bgCtx.fillText(`${m}:${String(sec).padStart(2, '0')}`, x + 2, 13);
  }

  // ── Word lane ──
  let y = AXIS_H;
  bgCtx.fillStyle = '#1c1c2a';
  bgCtx.fillRect(0, y, w, WORD_H);
  for (const wm of wordMarks) {
    const x  = (wm.start_ms / 1000) * PX_PER_SEC;
    const bw = Math.max(2, ((wm.end_ms - wm.start_ms) / 1000) * PX_PER_SEC - 1);
    bgCtx.fillStyle = '#2855a5';
    bgCtx.fillRect(x, y + 5, bw, WORD_H - 10);
    if (bw > 14) {
      bgCtx.fillStyle = '#cdf';
      bgCtx.font = '10px system-ui';
      bgCtx.textAlign = 'left';
      bgCtx.save();
      bgCtx.beginPath();
      bgCtx.rect(x + 1, y + 5, bw - 2, WORD_H - 10);
      bgCtx.clip();
      bgCtx.fillText(wm.label, x + 3, y + WORD_H - 14);
      bgCtx.restore();
    }
  }

  // ── Phoneme lane ──
  y += WORD_H;
  bgCtx.fillStyle = '#191919';
  bgCtx.fillRect(0, y, w, PHONEME_H);

  // Phoneme legend (color key at top right)
  let lx = w - 10;
  const legendOrder = ['AI', 'E', 'O', 'WQ', 'L', 'MBP', 'FV'];
  bgCtx.font = '9px monospace';
  bgCtx.textAlign = 'right';
  for (const lbl of [...legendOrder].reverse()) {
    const textW = bgCtx.measureText(lbl).width + 8;
    bgCtx.fillStyle = PHONEME_COLORS[lbl];
    bgCtx.fillRect(lx - textW, y + 2, textW, 10);
    bgCtx.fillStyle = 'rgba(0,0,0,0.75)';
    bgCtx.fillText(lbl, lx - 2, y + 10);
    lx -= textW + 2;
  }

  for (const pm of phonemeMarks) {
    const x  = (pm.start_ms / 1000) * PX_PER_SEC;
    const bw = Math.max(1, ((pm.end_ms - pm.start_ms) / 1000) * PX_PER_SEC - 1);
    bgCtx.fillStyle = PHONEME_COLORS[pm.label] || PHONEME_COLORS.etc;
    bgCtx.fillRect(x, y + 14, bw, PHONEME_H - 18);
    if (bw > 18) {
      bgCtx.fillStyle = 'rgba(0,0,0,0.8)';
      bgCtx.font = 'bold 9px monospace';
      bgCtx.textAlign = 'center';
      bgCtx.fillText(pm.label, x + bw / 2, y + PHONEME_H - 8);
    }
  }

  // ── Timing tracks ──
  tracks.forEach((track, i) => {
    y = AXIS_H + WORD_H + PHONEME_H + i * TRACK_H;
    bgCtx.fillStyle = i % 2 === 0 ? '#1e1e1e' : '#1b1b1b';
    bgCtx.fillRect(0, y, w, TRACK_H);
    bgCtx.fillStyle = '#4a9eff66';
    for (const mark of track.marks) {
      const x = Math.round((mark.time_ms / 1000) * PX_PER_SEC);
      bgCtx.fillRect(x, y + 4, 2, TRACK_H - 8);
    }
  });
}

// ── Playback ──────────────────────────────────────────────────────────────────

function fmtTime(s) {
  const m = Math.floor(s / 60);
  return `${m}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
}

btnPlay.addEventListener('click', () => {
  player.paused ? player.play() : player.pause();
});
player.addEventListener('play',  () => { btnPlay.textContent = 'Pause'; });
player.addEventListener('pause', () => { btnPlay.textContent = 'Play'; });

player.addEventListener('timeupdate', () => {
  const nowMs = player.currentTime * 1000;
  const dur   = isFinite(player.duration) ? player.duration : durationMs / 1000;
  timeDisplay.textContent = `${fmtTime(player.currentTime)} / ${fmtTime(dur)}`;
  updateLyrics(nowMs);
  drawPlayhead(nowMs);
  autoScroll(nowMs);
});

function drawPlayhead(nowMs) {
  const w = fgCanvas.width, h = fgCanvas.height;
  fgCtx.clearRect(0, 0, w, h);
  const x = Math.round((nowMs / 1000) * PX_PER_SEC);
  fgCtx.strokeStyle = '#ff4444';
  fgCtx.lineWidth = 1;
  fgCtx.beginPath();
  fgCtx.moveTo(x, 0);
  fgCtx.lineTo(x, h);
  fgCtx.stroke();
}

function autoScroll(nowMs) {
  const x   = (nowMs / 1000) * PX_PER_SEC;
  const vw  = canvasWrap.clientWidth;
  const cur = canvasWrap.scrollLeft;
  if (x < cur + 60 || x > cur + vw - 60) {
    canvasWrap.scrollLeft = Math.max(0, x - vw / 2);
  }
}

// Click to seek
fgCanvas.addEventListener('click', e => {
  const rect = fgCanvas.getBoundingClientRect();
  const x = e.clientX - rect.left + canvasWrap.scrollLeft;
  player.currentTime = x / PX_PER_SEC;
});

// ── Audio toggle ──────────────────────────────────────────────────────────────

btnFullMix.addEventListener('click', () => {
  if (usingVocals) switchAudio('/audio', false);
});
btnVocals.addEventListener('click', () => {
  if (!usingVocals && hasVocals) switchAudio('/vocal-audio', true);
});

function switchAudio(src, vocals) {
  const t = player.currentTime;
  const wasPlaying = !player.paused;
  player.src = src;
  player.currentTime = t;
  if (wasPlaying) player.play();
  usingVocals = vocals;
  btnVocals.classList.toggle('active', vocals);
  btnFullMix.classList.toggle('active', !vocals);
}

// ── Resize ────────────────────────────────────────────────────────────────────

window.addEventListener('resize', () => {
  drawBackground();
});

// ── Go ────────────────────────────────────────────────────────────────────────

init();
