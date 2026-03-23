'use strict';

// ── State ────────────────────────────────────────────────────────────────────

let tracks = [];       // [{name, element_type, quality_score, mark_count, avg_interval_ms, marks_ms, selected, isHighDensity}]
let durationMs = 0;
let focusIndex = null; // int | null

const player = document.getElementById('player');
const bgCanvas = document.getElementById('bg-canvas');
const fgCanvas = document.getElementById('fg-canvas');
const bgCtx = bgCanvas.getContext('2d');
const fgCtx = fgCanvas.getContext('2d');
const panel = document.getElementById('panel');
const canvasWrap = document.getElementById('canvas-wrap');
const beatFlash = document.getElementById('beat-flash');
const btnPlay = document.getElementById('btn-play');
const btnPrev = document.getElementById('btn-prev');
const btnNext = document.getElementById('btn-next');
const btnClear = document.getElementById('btn-clear');
const btnExport = document.getElementById('btn-export');
const timeDisplay = document.getElementById('time-display');
const focusLabel = document.getElementById('focus-label');
const selectedCount = document.getElementById('selected-count');
const status = document.getElementById('status');

const LANE_H = 60;
const AXIS_H = 24;
const PX_PER_SEC = 100; // default zoom; canvas width = duration_s * PX_PER_SEC

// ── Helpers ──────────────────────────────────────────────────────────────────

function fmtTime(sec) {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function canvasWidth() {
  return Math.max(canvasWrap.clientWidth, Math.ceil((durationMs / 1000) * PX_PER_SEC));
}

function canvasHeight() {
  return AXIS_H + tracks.length * LANE_H;
}

function timeToX(ms) {
  return (ms / durationMs) * canvasWidth();
}

// ── Background canvas (track marks + time axis) ───────────────────────────────

function drawBackground() {
  const w = canvasWidth();
  const h = canvasHeight();
  bgCanvas.width = w;
  bgCanvas.height = h;
  fgCanvas.width = w;
  fgCanvas.height = h;

  bgCtx.clearRect(0, 0, w, h);

  // Time axis
  bgCtx.fillStyle = '#222';
  bgCtx.fillRect(0, 0, w, AXIS_H);
  bgCtx.fillStyle = '#555';
  bgCtx.font = '10px system-ui';
  bgCtx.textBaseline = 'middle';
  const stepSec = durationMs > 120000 ? 30 : 10;
  for (let t = 0; t <= durationMs / 1000; t += stepSec) {
    const x = timeToX(t * 1000);
    bgCtx.fillStyle = '#444';
    bgCtx.fillRect(x, 0, 1, AXIS_H);
    bgCtx.fillStyle = '#888';
    bgCtx.fillText(fmtTime(t), x + 2, AXIS_H / 2);
  }

  // Track lanes
  tracks.forEach((track, i) => {
    const y = AXIS_H + i * LANE_H;
    const isEven = i % 2 === 0;
    bgCtx.fillStyle = isEven ? '#141414' : '#181818';
    bgCtx.fillRect(0, y, w, LANE_H);

    // Lane separator
    bgCtx.fillStyle = '#222';
    bgCtx.fillRect(0, y + LANE_H - 1, w, 1);

    // Marks
    const opacity = track.selected ? 1.0 : 0.4;
    bgCtx.globalAlpha = opacity;
    bgCtx.fillStyle = track.isHighDensity ? '#e44' : '#4a9';
    track.marks_ms.forEach(ms => {
      const x = timeToX(ms);
      bgCtx.fillRect(x, y + 4, 2, LANE_H - 8);
    });
    bgCtx.globalAlpha = 1.0;
  });
}

// ── Foreground canvas (playhead + focus overlay) ──────────────────────────────

function drawForeground() {
  const w = canvasWidth();
  const h = canvasHeight();
  fgCtx.clearRect(0, 0, w, h);

  // Focus dimming overlay
  if (focusIndex !== null) {
    tracks.forEach((_, i) => {
      if (i !== focusIndex) {
        const y = AXIS_H + i * LANE_H;
        fgCtx.fillStyle = 'rgba(0,0,0,0.65)';
        fgCtx.fillRect(0, y, w, LANE_H);
      }
    });
    // Focused lane highlight border
    const focusY = AXIS_H + focusIndex * LANE_H;
    fgCtx.strokeStyle = '#4af';
    fgCtx.lineWidth = 2;
    fgCtx.strokeRect(1, focusY + 1, w - 2, LANE_H - 2);
  }

  // Playhead
  if (player.duration && isFinite(player.duration)) {
    const x = (player.currentTime / player.duration) * w;
    fgCtx.fillStyle = '#f44';
    fgCtx.fillRect(x, 0, 1, h);
  }
}

// ── Panel (left lane controls) ────────────────────────────────────────────────

function buildPanel() {
  panel.innerHTML = '';
  tracks.forEach((track, i) => {
    const div = document.createElement('div');
    div.className = 'lane-control';
    div.dataset.index = i;

    const score = track.quality_score;
    const scoreClass = score >= 0.5 ? '' : score >= 0.2 ? 'mid' : 'low';

    const stemLabel = track.stem_source && track.stem_source !== 'full_mix'
      ? `<span class="stem-badge">${track.stem_source}</span>`
      : '';
    div.innerHTML = `
      <div class="lane-top">
        <span class="lane-name" title="${track.name}">${track.name}</span>
        <span class="score-badge ${scoreClass}">${score.toFixed(2)}</span>
        ${stemLabel}
      </div>
      <div class="lane-meta">
        <span class="type-tag">${track.element_type}</span>
        <span>${track.mark_count} marks</span>
        <button class="btn-solo" data-index="${i}">Solo</button>
        <input type="checkbox" class="chk-select" data-index="${i}" ${track.selected ? 'checked' : ''}>
      </div>
    `;
    panel.appendChild(div);
  });

  // Solo button clicks
  panel.querySelectorAll('.btn-solo').forEach(btn => {
    btn.addEventListener('click', e => {
      const i = parseInt(e.currentTarget.dataset.index);
      if (focusIndex === i) {
        clearFocus();
      } else {
        setFocus(i);
      }
    });
  });

  // Checkbox toggles
  panel.querySelectorAll('.chk-select').forEach(chk => {
    chk.addEventListener('change', e => {
      const i = parseInt(e.currentTarget.dataset.index);
      tracks[i].selected = e.currentTarget.checked;
      updatePanelClasses();
      updateSelectedCount();
      drawBackground();
    });
  });
}

function updatePanelClasses() {
  panel.querySelectorAll('.lane-control').forEach((div, i) => {
    div.classList.remove('focused', 'unfocused', 'deselected');
    if (!tracks[i].selected) {
      div.classList.add('deselected');
    } else if (focusIndex === null) {
      // normal
    } else if (i === focusIndex) {
      div.classList.add('focused');
    } else {
      div.classList.add('unfocused');
    }

    // Update solo button active state
    const soloBtn = div.querySelector('.btn-solo');
    if (soloBtn) {
      soloBtn.classList.toggle('active', focusIndex === i);
    }
  });
}

function updateSelectedCount() {
  const n = tracks.filter(t => t.selected).length;
  selectedCount.textContent = `${n} / ${tracks.length} selected`;
  btnExport.disabled = n === 0;
}

// ── Focus management ──────────────────────────────────────────────────────────

function setFocus(i) {
  focusIndex = i;
  focusLabel.textContent = `Focus: ${tracks[i].name}`;
  updatePanelClasses();
  drawForeground();
  scheduleFlashes();
}

function clearFocus() {
  focusIndex = null;
  focusLabel.textContent = '';
  updatePanelClasses();
  drawForeground();
  scheduleFlashes();
}

function focusNext() {
  if (tracks.length === 0) return;
  if (focusIndex === null) {
    setFocus(0);
  } else {
    setFocus((focusIndex + 1) % tracks.length);
  }
}

function focusPrev() {
  if (tracks.length === 0) return;
  if (focusIndex === null) {
    setFocus(tracks.length - 1);
  } else {
    setFocus((focusIndex - 1 + tracks.length) % tracks.length);
  }
}

// ── Playback ──────────────────────────────────────────────────────────────────

let rafId = null;
let flashTimers = [];
let flashAnim = null;

// Fire slightly early to compensate for visual processing latency (~1 frame).
// Increase this value if flashes feel late; decrease if they feel early.
const VISUAL_LEAD_MS = 20;

function triggerFlash() {
  if (flashAnim) flashAnim.cancel();
  flashAnim = beatFlash.animate([
    { background: '#fff', boxShadow: '0 0 10px #fff, 0 0 4px #adf' },
    { background: '#4af', boxShadow: '0 0 6px #4af', offset: 0.4 },
    { background: '#2a2a2a', boxShadow: 'none' },
  ], { duration: 250, easing: 'ease-out' });
}

function cancelFlashTimers() {
  flashTimers.forEach(clearTimeout);
  flashTimers = [];
}

// Schedule a setTimeout for every upcoming mark in the monitored track.
// This fires independent of the render loop, giving much tighter timing than
// per-frame currentTime polling.
function scheduleFlashes() {
  cancelFlashTimers();
  if (player.paused || player.ended || !player.duration) return;
  const monitorTrack = focusIndex !== null ? tracks[focusIndex] : tracks.find(t => t.selected);
  if (!monitorTrack) return;
  const currentMs = player.currentTime * 1000;
  for (const markMs of monitorTrack.marks_ms) {
    const delay = markMs - currentMs - VISUAL_LEAD_MS;
    if (delay < -50) continue; // already passed
    flashTimers.push(setTimeout(triggerFlash, Math.max(0, delay)));
  }
}

function rafLoop() {
  drawForeground();
  timeDisplay.textContent = `${fmtTime(player.currentTime)} / ${fmtTime(player.duration || 0)}`;

  // Auto-scroll to keep playhead in view
  if (player.duration && isFinite(player.duration)) {
    const x = (player.currentTime / player.duration) * canvasWidth();
    const viewLeft = canvasWrap.scrollLeft;
    const viewRight = viewLeft + canvasWrap.clientWidth;
    if (x > viewRight - 60) {
      canvasWrap.scrollLeft = Math.max(0, x - canvasWrap.clientWidth * 0.25);
    } else if (x < viewLeft) {
      canvasWrap.scrollLeft = Math.max(0, x - 50);
    }
  }

  if (!player.paused && !player.ended) {
    rafId = requestAnimationFrame(rafLoop);
  }
}

btnPlay.addEventListener('click', () => {
  if (player.paused) {
    player.play();
    btnPlay.textContent = 'Pause';
    rafId = requestAnimationFrame(rafLoop);
    scheduleFlashes();
  } else {
    player.pause();
    btnPlay.textContent = 'Play';
    cancelAnimationFrame(rafId);
    cancelFlashTimers();
    drawForeground();
  }
});

player.addEventListener('ended', () => {
  btnPlay.textContent = 'Play';
  cancelAnimationFrame(rafId);
  cancelFlashTimers();
  drawForeground();
});

// Timeline seek (click on canvas wrap)
canvasWrap.addEventListener('mousedown', e => {
  if (!player.duration || !isFinite(player.duration)) return;
  const rect = canvasWrap.getBoundingClientRect();
  const scrollX = canvasWrap.scrollLeft;
  const x = e.clientX - rect.left + scrollX;
  const w = canvasWidth();
  const seekTime = (x / w) * player.duration;
  player.currentTime = Math.max(0, Math.min(seekTime, player.duration));
  scheduleFlashes(); // reschedule from new position
  drawForeground();
  timeDisplay.textContent = `${fmtTime(player.currentTime)} / ${fmtTime(player.duration)}`;
});

// ── Keyboard shortcuts ────────────────────────────────────────────────────────

document.addEventListener('keydown', e => {
  switch (e.key) {
    case ' ':
      e.preventDefault();
      btnPlay.click();
      break;
    case 'ArrowRight':
    case 'n':
      e.preventDefault();
      focusNext();
      break;
    case 'ArrowLeft':
    case 'p':
      e.preventDefault();
      focusPrev();
      break;
    case 'Escape':
      clearFocus();
      break;
  }
});

// ── Focus/Nav buttons ─────────────────────────────────────────────────────────

btnNext.addEventListener('click', focusNext);
btnPrev.addEventListener('click', focusPrev);
btnClear.addEventListener('click', clearFocus);

// ── Export ───────────────────────────────────────────────────────────────────

async function doExport(overwrite = false) {
  const names = tracks.filter(t => t.selected).map(t => t.name);
  if (names.length === 0) {
    status.textContent = 'No tracks selected — nothing to export.';
    return;
  }

  const body = { selected_track_names: names };
  if (overwrite) body.overwrite = true;

  let resp;
  try {
    resp = await fetch('/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  } catch (err) {
    status.textContent = `Export failed: ${err.message}`;
    return;
  }

  const data = await resp.json();

  if (resp.status === 409) {
    if (confirm(`File already exists:\n${data.path}\n\nOverwrite?`)) {
      doExport(true);
    }
    return;
  }

  if (resp.status === 400) {
    status.textContent = `Export error: ${data.error}`;
    return;
  }

  if (resp.ok) {
    status.textContent = `Exported ${names.length} track(s) to: ${data.path}`;
  } else {
    status.textContent = `Export error: ${data.error || resp.status}`;
  }
}

btnExport.addEventListener('click', () => doExport(false));

// ── Resize handling ───────────────────────────────────────────────────────────

window.addEventListener('resize', () => {
  drawBackground();
  drawForeground();
});

// ── Initialise ────────────────────────────────────────────────────────────────

async function init() {
  try {
    const resp = await fetch('/analysis');
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();

    durationMs = data.duration_ms || 0;

    // Build track list sorted by quality_score descending
    tracks = (data.timing_tracks || [])
      .sort((a, b) => b.quality_score - a.quality_score)
      .map(t => ({
        name: t.name,
        element_type: t.element_type,
        quality_score: t.quality_score,
        mark_count: t.mark_count,
        avg_interval_ms: t.avg_interval_ms,
        marks_ms: (t.marks || []).map(m => m.time_ms),
        stem_source: t.stem_source || 'full_mix',
        selected: true,
        isHighDensity: t.quality_score === 0 || (t.avg_interval_ms > 0 && t.avg_interval_ms < 200),
      }));

    buildPanel();
    updateSelectedCount();
    drawBackground();
    drawForeground();

    status.textContent = `Loaded ${tracks.length} tracks | ${fmtTime(durationMs / 1000)} | ${data.filename || ''}`;

    // Update time display when audio metadata loads
    player.addEventListener('loadedmetadata', () => {
      timeDisplay.textContent = `0:00 / ${fmtTime(player.duration)}`;
    });

  } catch (err) {
    status.textContent = `Error loading analysis: ${err.message}`;
  }
}

init();
