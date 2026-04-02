/**
 * Dashboard logic for x-onset unified homepage.
 * Handles: song library table, sort/filter, upload, detail panel, delete.
 */
(function () {
  'use strict';

  // ── State ──────────────────────────────────────────────────────────────────
  let _entries = [];
  let _sortCol = 'analyzed_at';
  let _sortAsc = false;
  let _filterText = '';
  let _expandedHash = null;
  let _selectedFile = null;
  let _deleteHash = null;
  let _lastResultHash = null;

  // ── DOM refs ───────────────────────────────────────────────────────────────
  const tbody = () => document.getElementById('library-tbody');
  const searchInput = () => document.getElementById('search-input');
  const songCount = () => document.getElementById('song-count');
  const emptyState = () => document.getElementById('empty-state');
  const tableWrap = () => document.getElementById('library-table-wrap');
  const filterBar = () => document.querySelector('.filter-bar');

  // ── Formatting helpers ─────────────────────────────────────────────────────
  function fmtDuration(ms) {
    var s = Math.round(ms / 1000);
    var m = Math.floor(s / 60);
    s = s % 60;
    return m + ':' + (s < 10 ? '0' : '') + s;
  }

  function fmtDate(ts) {
    if (!ts) return '';
    var d = new Date(ts);
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  }

  function fmtBpm(bpm) {
    return bpm ? Math.round(bpm) : '—';
  }

  function qualityClass(score) {
    if (score == null) return '';
    if (score >= 0.7) return 'quality-good';
    if (score >= 0.4) return 'quality-mid';
    return 'quality-low';
  }

  // ── Fetch library ──────────────────────────────────────────────────────────
  function fetchLibrary() {
    fetch('/library')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        _entries = data.entries || [];
        renderTable();
      })
      .catch(function () {
        _entries = [];
        renderTable();
      });
  }

  // ── Sort & filter ──────────────────────────────────────────────────────────
  function getFiltered() {
    var q = _filterText.toLowerCase();
    var list = _entries;
    if (q) {
      list = list.filter(function (e) {
        return (e.title || '').toLowerCase().indexOf(q) >= 0 ||
               (e.artist || '').toLowerCase().indexOf(q) >= 0 ||
               (e.album || '').toLowerCase().indexOf(q) >= 0 ||
               (e.genre || '').toLowerCase().indexOf(q) >= 0;
      });
    }
    // Sort
    list = list.slice().sort(function (a, b) {
      var av = a[_sortCol], bv = b[_sortCol];
      if (av == null) av = '';
      if (bv == null) bv = '';
      if (typeof av === 'string') av = av.toLowerCase();
      if (typeof bv === 'string') bv = bv.toLowerCase();
      if (av < bv) return _sortAsc ? -1 : 1;
      if (av > bv) return _sortAsc ? 1 : -1;
      return 0;
    });
    return list;
  }

  // ── Render table ───────────────────────────────────────────────────────────
  function renderTable() {
    var filtered = getFiltered();
    var tb = tbody();
    if (!tb) return;
    tb.innerHTML = '';

    var total = _entries.length;
    var shown = filtered.length;
    var sc = songCount();
    if (sc) {
      sc.textContent = _filterText
        ? shown + ' of ' + total + ' songs'
        : total + ' song' + (total !== 1 ? 's' : '');
    }

    // Show/hide empty state vs table
    var es = emptyState();
    var tw = tableWrap();
    var fb = filterBar();
    if (total === 0) {
      if (es) es.style.display = '';
      if (tw) tw.style.display = 'none';
      if (fb) fb.style.display = 'none';
      return;
    }
    if (es) es.style.display = 'none';
    if (tw) tw.style.display = '';
    if (fb) fb.style.display = '';

    // Update sort indicators
    document.querySelectorAll('.library-table th').forEach(function (th) {
      th.classList.remove('sorted', 'sort-asc', 'sort-desc');
      if (th.dataset.sort === _sortCol) {
        th.classList.add('sorted', _sortAsc ? 'sort-asc' : 'sort-desc');
      }
    });

    filtered.forEach(function (e) {
      var tr = document.createElement('tr');
      var isMissing = e.file_exists === false || e.analysis_exists === false;
      if (isMissing) tr.classList.add('missing');
      if (_expandedHash === e.source_hash) tr.classList.add('expanded');
      tr.dataset.hash = e.source_hash;

      var coverHtml = e.has_cover
        ? '<img class="cover-thumb" src="/library/' + esc(e.source_hash) + '/cover" alt="">'
        : '<span class="cover-placeholder">&#9836;</span>';

      tr.innerHTML =
        '<td class="col-cover">' + coverHtml + '</td>' +
        '<td class="song-title-cell">' + esc(e.title || e.filename) + '</td>' +
        '<td class="song-artist-cell">' + esc(e.artist || '') + '</td>' +
        '<td class="song-album-cell">' + esc(e.album || '') + '</td>' +
        '<td class="song-genre-cell">' + esc(e.genre || '') + '</td>' +
        '<td class="col-num">' + esc(e.year || '') + '</td>' +
        '<td class="col-num">' + fmtDuration(e.duration_ms) + '</td>' +
        '<td class="col-num">' + fmtBpm(e.estimated_tempo_bpm) + '</td>' +
        '<td class="col-num">' + renderQuality(e.quality_score) + '</td>' +
        '<td class="col-badges">' + renderBadges(e) + '</td>' +
        '<td class="col-num">' + fmtDate(e.analyzed_at) + '</td>' +
        '<td class="col-actions"><button class="btn-expand" data-hash="' + esc(e.source_hash) + '">Details</button></td>';

      // Click row to go to story view (but not on buttons)
      tr.addEventListener('click', function (ev) {
        if (ev.target.tagName === 'BUTTON') return;
        openSong(e.source_hash, e.has_story ? 'story' : 'timeline', e.story_path);
      });

      tb.appendChild(tr);

      // Detail panel if expanded
      if (_expandedHash === e.source_hash) {
        renderDetail(e, tb);
      }
    });

    // Attach expand button handlers
    tb.querySelectorAll('.btn-expand').forEach(function (btn) {
      btn.addEventListener('click', function (ev) {
        ev.stopPropagation();
        var hash = btn.dataset.hash;
        _expandedHash = (_expandedHash === hash) ? null : hash;
        renderTable();
      });
    });
  }

  function esc(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function renderQuality(score) {
    if (score == null) return '<span class="quality-label">—</span>';
    var pct = Math.round(score * 100);
    var cls = qualityClass(score);
    return '<span class="quality-bar"><span class="quality-fill ' + cls + '" style="width:' + pct + '%"></span></span>' +
           '<span class="quality-label">' + pct + '%</span>';
  }

  function renderBadges(e) {
    var html = '';
    if (e.stem_separation) html += '<span class="badge badge-stems">Stems</span>';
    if (e.has_phonemes) html += '<span class="badge badge-phonemes">Phonemes</span>';
    if (e.has_story) html += '<span class="badge badge-story">Story</span>';
    if (e.file_exists === false || e.analysis_exists === false) {
      html += '<span class="badge badge-missing">Missing</span>';
    }
    return html;
  }

  // ── Detail panel ───────────────────────────────────────────────────────────
  function renderDetail(entry, tb) {
    var tmpl = document.getElementById('detail-template');
    if (!tmpl) return;
    var clone = tmpl.content.cloneNode(true);
    var tr = clone.querySelector('tr');

    // Quality bar
    var qFill = tr.querySelector('.quality-fill');
    var qLabel = tr.querySelector('.detail-quality-label');
    if (entry.quality_score != null) {
      var pct = Math.round(entry.quality_score * 100);
      qFill.style.width = pct + '%';
      qFill.className = 'quality-fill ' + qualityClass(entry.quality_score);
      qLabel.textContent = pct + '% overall';
    } else {
      qLabel.textContent = 'No quality data';
    }

    // Info
    var info = tr.querySelector('.detail-info');
    var lines = [];
    lines.push('Tracks: ' + (entry.track_count || '—'));
    lines.push('Stems: ' + (entry.stem_separation ? 'Yes' : 'No'));
    lines.push('File: ' + esc(entry.filename || ''));
    if (entry.file_exists === false) lines.push('<span style="color:#c44">Source file missing</span>');
    if (entry.analysis_exists === false) lines.push('<span style="color:#c44">Analysis file missing</span>');
    info.innerHTML = lines.join('<br>');

    // Action buttons
    tr.querySelectorAll('.btn-action').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var action = btn.dataset.action;
        if (action === 'timeline') openSong(entry.source_hash, 'timeline');
        else if (action === 'story') openSong(entry.source_hash, 'story', entry.story_path);
        else if (action === 'phonemes') openSong(entry.source_hash, 'phonemes');
        else if (action === 'reanalyze') reanalyzeSong(entry);
        else if (action === 'delete') showDeleteDialog(entry);
      });
    });

    tb.appendChild(tr);
  }

  // ── Navigation helpers ─────────────────────────────────────────────────────
  function openSong(hash, tool, storyPath) {
    // Set current job to this library entry, then navigate
    fetch('/open-from-library?hash=' + hash, { method: 'POST' })
      .then(function () {
        if (tool === 'story' && storyPath) {
          window.location.href = '/story-review?path=' + encodeURIComponent(storyPath);
        } else if (tool === 'phonemes') {
          window.location.href = '/phonemes-view?hash=' + hash;
        } else {
          window.location.href = '/timeline?hash=' + hash;
        }
      });
  }

  function reanalyzeSong(entry) {
    // Open upload section and pre-fill
    var section = document.getElementById('upload-section');
    section.classList.remove('collapsed');
    // Could pre-fill with source path in the future; for now just open upload
  }

  // ── Delete ─────────────────────────────────────────────────────────────────
  function showDeleteDialog(entry) {
    _deleteHash = entry.source_hash;
    var dialog = document.getElementById('delete-dialog');
    document.getElementById('delete-song-name').textContent = entry.title || entry.filename;
    document.getElementById('delete-files-check').checked = false;
    dialog.style.display = '';
  }

  function hideDeleteDialog() {
    document.getElementById('delete-dialog').style.display = 'none';
    _deleteHash = null;
  }

  function confirmDelete() {
    if (!_deleteHash) return;
    var deleteFiles = document.getElementById('delete-files-check').checked;
    fetch('/library/' + _deleteHash + '?delete_files=' + deleteFiles, { method: 'DELETE' })
      .then(function (r) { return r.json(); })
      .then(function () {
        hideDeleteDialog();
        if (_expandedHash === _deleteHash) _expandedHash = null;
        fetchLibrary();
      })
      .catch(function () { hideDeleteDialog(); });
  }

  // ── Upload ─────────────────────────────────────────────────────────────────
  function initUpload() {
    var toggle = document.getElementById('upload-toggle');
    var section = document.getElementById('upload-section');
    var dropZone = document.getElementById('drop-zone');
    var fileInput = document.getElementById('file-input');
    var btnAnalyze = document.getElementById('btn-analyze');
    var fileName = document.getElementById('file-name');

    if (toggle) {
      toggle.addEventListener('click', function () {
        section.classList.toggle('collapsed');
      });
    }

    // Empty state upload button
    var btnEmpty = document.getElementById('btn-empty-upload');
    if (btnEmpty) {
      btnEmpty.addEventListener('click', function () {
        section.classList.remove('collapsed');
        section.scrollIntoView({ behavior: 'smooth' });
      });
    }

    // Drop zone
    if (dropZone) {
      dropZone.addEventListener('dragover', function (e) {
        e.preventDefault();
        dropZone.classList.add('drag-over');
      });
      dropZone.addEventListener('dragleave', function () {
        dropZone.classList.remove('drag-over');
      });
      dropZone.addEventListener('drop', function (e) {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        if (e.dataTransfer.files.length > 0) {
          selectFile(e.dataTransfer.files[0]);
        }
      });
    }

    if (fileInput) {
      fileInput.addEventListener('change', function () {
        if (fileInput.files.length > 0) selectFile(fileInput.files[0]);
      });
    }

    if (btnAnalyze) {
      btnAnalyze.addEventListener('click', startAnalysis);
    }

    function selectFile(file) {
      if (!file.name.toLowerCase().endsWith('.mp3')) {
        alert('Only .mp3 files are accepted');
        return;
      }
      _selectedFile = file;
      if (fileName) fileName.textContent = file.name;
      if (btnAnalyze) btnAnalyze.disabled = false;

      // Check for duplicate
      var dup = document.getElementById('duplicate-warning');
      var existing = _entries.find(function (e) { return e.filename === file.name; });
      if (existing && dup) {
        dup.style.display = '';
        document.getElementById('btn-go-existing').onclick = function () {
          openSong(existing.source_hash, existing.has_story ? 'story' : 'timeline', existing.story_path);
        };
        document.getElementById('btn-reanalyze').onclick = startAnalysis;
      } else if (dup) {
        dup.style.display = 'none';
      }
    }
  }

  function startAnalysis() {
    if (!_selectedFile) return;

    var fd = new FormData();
    fd.append('mp3', _selectedFile);
    fd.append('story', document.getElementById('opt-story').checked ? 'true' : 'false');

    // Show progress section
    var progSection = document.getElementById('progress-section');
    progSection.style.display = '';
    document.getElementById('progress-bar').style.width = '0%';
    document.getElementById('progress-steps').innerHTML = '';
    document.getElementById('progress-error').style.display = 'none';
    document.getElementById('progress-done').style.display = 'none';
    document.getElementById('genius-prompt').style.display = 'none';
    document.getElementById('progress-label').textContent = 'Starting analysis...';
    document.getElementById('progress-count').textContent = '';

    // Collapse upload section
    document.getElementById('upload-section').classList.add('collapsed');

    fetch('/upload', { method: 'POST', body: fd })
      .then(function (r) {
        if (!r.ok) return r.json().then(function (d) { throw new Error(d.error || 'Upload failed'); });
        return r.json();
      })
      .then(function () {
        listenProgress();
      })
      .catch(function (err) {
        document.getElementById('progress-error').textContent = err.message;
        document.getElementById('progress-error').style.display = '';
      });
  }

  function listenProgress() {
    var es = new EventSource('/progress');
    var steps = document.getElementById('progress-steps');

    es.onmessage = function (ev) {
      var data;
      try { data = JSON.parse(ev.data); } catch (e) { return; }

      if (data.error) {
        es.close();
        document.getElementById('progress-error').textContent = data.error;
        document.getElementById('progress-error').style.display = '';
        return;
      }

      if (data.done) {
        es.close();
        document.getElementById('progress-bar').style.width = '100%';
        document.getElementById('progress-label').textContent = 'Complete';
        document.getElementById('progress-done').style.display = '';
        _lastResultHash = null;
        // Refresh library
        fetchLibrary();

        document.getElementById('btn-view-result').onclick = function () {
          if (data.story_path) {
            window.location.href = '/story-review?path=' + encodeURIComponent(data.story_path);
          } else {
            window.location.href = '/timeline';
          }
        };
        return;
      }

      if (data.genius_prompt) {
        var gp = document.getElementById('genius-prompt');
        gp.style.display = '';
        document.getElementById('genius-artist').value = data.guessed_artist || '';
        document.getElementById('genius-title').value = data.guessed_title || '';
        return;
      }

      if (data.stage) {
        document.getElementById('progress-label').textContent = data.label || data.stage;
        return;
      }

      if (data.warning) {
        var warn = document.createElement('div');
        warn.className = 'step';
        warn.style.color = '#c90';
        warn.textContent = '\u26A0 ' + data.warning;
        steps.appendChild(warn);
        return;
      }

      // Progress event
      if (data.idx != null) {
        var pct = Math.round(((data.idx + 1) / data.total) * 100);
        document.getElementById('progress-bar').style.width = pct + '%';
        document.getElementById('progress-count').textContent = (data.idx + 1) + '/' + data.total;

        var step = document.createElement('div');
        step.className = 'step done';
        step.textContent = '\u2713 ' + data.name + (data.mark_count ? ' (' + data.mark_count + ' marks)' : '');
        steps.appendChild(step);
        steps.scrollTop = steps.scrollHeight;
      }
    };
  }

  function initGenius() {
    var btnSubmit = document.getElementById('btn-genius-submit');
    var btnSkip = document.getElementById('btn-genius-skip');

    if (btnSubmit) {
      btnSubmit.addEventListener('click', function () {
        var artist = document.getElementById('genius-artist').value;
        var title = document.getElementById('genius-title').value;
        fetch('/genius-retry', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ artist: artist, title: title }),
        });
        document.getElementById('genius-prompt').style.display = 'none';
      });
    }

    if (btnSkip) {
      btnSkip.addEventListener('click', function () {
        fetch('/genius-retry', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ artist: '', title: '__skip__' }),
        });
        document.getElementById('genius-prompt').style.display = 'none';
      });
    }
  }

  // ── State persistence (US3) ────────────────────────────────────────────────
  function saveState() {
    try {
      sessionStorage.setItem('dashboard_sort_col', _sortCol);
      sessionStorage.setItem('dashboard_sort_asc', _sortAsc ? '1' : '0');
      sessionStorage.setItem('dashboard_filter', _filterText);
    } catch (e) { /* ignore */ }
  }

  function restoreState() {
    try {
      var col = sessionStorage.getItem('dashboard_sort_col');
      var asc = sessionStorage.getItem('dashboard_sort_asc');
      var filter = sessionStorage.getItem('dashboard_filter');
      if (col) _sortCol = col;
      if (asc !== null) _sortAsc = asc === '1';
      if (filter) {
        _filterText = filter;
        var si = searchInput();
        if (si) si.value = filter;
      }
    } catch (e) { /* ignore */ }
  }

  // Save state before navigating away
  window.addEventListener('beforeunload', saveState);

  // ── Init ───────────────────────────────────────────────────────────────────
  function init() {
    restoreState();

    // Sort column click
    document.querySelectorAll('.library-table th.sortable').forEach(function (th) {
      th.addEventListener('click', function () {
        var col = th.dataset.sort;
        if (_sortCol === col) {
          _sortAsc = !_sortAsc;
        } else {
          _sortCol = col;
          _sortAsc = true;
        }
        renderTable();
      });
    });

    // Search input
    var si = searchInput();
    if (si) {
      si.addEventListener('input', function () {
        _filterText = si.value;
        renderTable();
      });
    }

    // Delete dialog buttons
    var btnDelCancel = document.getElementById('btn-delete-cancel');
    var btnDelConfirm = document.getElementById('btn-delete-confirm');
    if (btnDelCancel) btnDelCancel.addEventListener('click', hideDeleteDialog);
    if (btnDelConfirm) btnDelConfirm.addEventListener('click', confirmDelete);

    initUpload();
    initGenius();
    fetchLibrary();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
