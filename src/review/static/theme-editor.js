/**
 * Theme editor logic for xlight-analyze.
 * Browse, create, edit, duplicate, delete themes.
 */
(function () {
  'use strict';

  let _themes = [];
  let _selectedName = null;
  let _editing = false;
  let _creating = false;

  // ── Fetch themes ───────────────────────────────────────────────────────────
  function fetchThemes(selectName) {
    fetch('/themes/list')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        _themes = data.themes || [];
        renderList();
        if (selectName) {
          _selectedName = selectName;
          showDetail(selectName);
        }
      });
  }

  // ── Render theme list ──────────────────────────────────────────────────────
  function renderList() {
    var list = document.getElementById('theme-list');
    if (!list) return;
    list.innerHTML = '';

    var builtins = _themes.filter(function (t) { return t.is_builtin; });
    var customs = _themes.filter(function (t) { return !t.is_builtin; });

    if (customs.length > 0) {
      var hdr = document.createElement('div');
      hdr.className = 'theme-section-header';
      hdr.textContent = 'Custom Themes';
      list.appendChild(hdr);
      customs.forEach(function (t) { list.appendChild(makeCard(t)); });
    }

    if (builtins.length > 0) {
      var hdr2 = document.createElement('div');
      hdr2.className = 'theme-section-header';
      hdr2.textContent = 'Built-in Themes (' + builtins.length + ')';
      list.appendChild(hdr2);
      builtins.forEach(function (t) { list.appendChild(makeCard(t)); });
    }
  }

  function makeCard(theme) {
    var card = document.createElement('div');
    card.className = 'theme-card' + (_selectedName === theme.name ? ' selected' : '');
    card.addEventListener('click', function () {
      _selectedName = theme.name;
      _editing = false;
      _creating = false;
      renderList();
      showDetail(theme.name);
    });

    var name = document.createElement('div');
    name.className = 'theme-card-name';
    name.textContent = theme.name;
    card.appendChild(name);

    var meta = document.createElement('div');
    meta.className = 'theme-card-meta';

    var mood = document.createElement('span');
    mood.className = 'theme-card-mood mood-' + theme.mood;
    mood.textContent = theme.mood;
    meta.appendChild(mood);

    // Palette swatches
    var swatches = document.createElement('div');
    swatches.className = 'theme-card-swatches';
    (theme.palette || []).slice(0, 6).forEach(function (color) {
      var s = document.createElement('div');
      s.className = 'swatch-mini';
      s.style.background = color;
      swatches.appendChild(s);
    });
    meta.appendChild(swatches);

    if (theme.is_builtin) {
      var bi = document.createElement('span');
      bi.className = 'theme-card-builtin';
      bi.textContent = 'built-in';
      meta.appendChild(bi);
    }

    card.appendChild(meta);
    return card;
  }

  // ── Show detail ────────────────────────────────────────────────────────────
  function showDetail(name) {
    var theme = _themes.find(function (t) { return t.name === name; });
    if (!theme) return;

    document.getElementById('detail-placeholder').style.display = 'none';
    document.getElementById('theme-detail').style.display = '';
    document.getElementById('view-mode').style.display = '';
    document.getElementById('edit-mode').style.display = 'none';

    document.getElementById('detail-name').textContent = theme.name;
    document.getElementById('view-mood').textContent = theme.mood;
    document.getElementById('view-occasion').textContent = theme.occasion;
    document.getElementById('view-genre').textContent = theme.genre;
    document.getElementById('view-intent').textContent = theme.intent;

    // Palette
    renderSwatches('view-palette', theme.palette);
    renderSwatches('view-accent', theme.accent_palette);

    // Layers
    var layersList = document.getElementById('view-layers');
    layersList.innerHTML = '';
    (theme.layers || []).forEach(function (l) {
      var div = document.createElement('div');
      div.className = 'layer-item';
      div.innerHTML = '<span class="layer-effect">' + esc(l.effect) + '</span>' +
                      '<span class="layer-blend">' + esc(l.blend_mode) + '</span>';
      layersList.appendChild(div);
    });

    // Show/hide buttons based on builtin status
    var isBuiltin = theme.is_builtin;
    document.getElementById('detail-builtin-badge').style.display = isBuiltin ? '' : 'none';
    document.getElementById('btn-edit').style.display = isBuiltin ? 'none' : '';
    document.getElementById('btn-delete-theme').style.display = isBuiltin ? 'none' : '';
    document.getElementById('btn-duplicate').style.display = '';
  }

  function renderSwatches(containerId, colors) {
    var container = document.getElementById(containerId);
    container.innerHTML = '';
    (colors || []).forEach(function (color) {
      var s = document.createElement('div');
      s.className = 'color-swatch';
      s.style.background = color;
      s.title = color;
      container.appendChild(s);
    });
    if (!colors || colors.length === 0) {
      container.innerHTML = '<span style="color:#555;font-size:12px">None</span>';
    }
  }

  // ── Edit mode ──────────────────────────────────────────────────────────────
  function enterEditMode(theme) {
    _editing = true;
    document.getElementById('view-mode').style.display = 'none';
    document.getElementById('edit-mode').style.display = '';

    document.getElementById('edit-name').value = theme ? theme.name : '';
    document.getElementById('edit-name').disabled = !_creating;
    document.getElementById('edit-mood').value = theme ? theme.mood : 'ethereal';
    document.getElementById('edit-occasion').value = theme ? theme.occasion : 'general';
    document.getElementById('edit-genre').value = theme ? theme.genre : 'any';
    document.getElementById('edit-intent').value = theme ? theme.intent : '';

    renderColorEditors('edit-palette', theme ? theme.palette : ['#ffffff']);
    renderColorEditors('edit-accent', theme ? theme.accent_palette : []);
  }

  function renderColorEditors(containerId, colors) {
    var container = document.getElementById(containerId);
    container.innerHTML = '';
    (colors || []).forEach(function (color) {
      addColorInput(container, color);
    });
  }

  function addColorInput(container, color) {
    var item = document.createElement('div');
    item.className = 'color-edit-item';
    var input = document.createElement('input');
    input.type = 'color';
    input.value = color || '#ffffff';
    item.appendChild(input);
    var remove = document.createElement('button');
    remove.className = 'color-remove';
    remove.textContent = '\u00D7';
    remove.addEventListener('click', function () { item.remove(); });
    item.appendChild(remove);
    container.appendChild(item);
  }

  function collectColors(containerId) {
    var inputs = document.querySelectorAll('#' + containerId + ' input[type="color"]');
    var colors = [];
    inputs.forEach(function (inp) { colors.push(inp.value); });
    return colors;
  }

  function collectFormData() {
    return {
      name: document.getElementById('edit-name').value.trim(),
      mood: document.getElementById('edit-mood').value,
      occasion: document.getElementById('edit-occasion').value,
      genre: document.getElementById('edit-genre').value,
      intent: document.getElementById('edit-intent').value.trim(),
      palette: collectColors('edit-palette'),
      accent_palette: collectColors('edit-accent'),
      layers: [],  // Preserve existing layers if editing
      variants: [],
    };
  }

  // ── Save ───────────────────────────────────────────────────────────────────
  function saveTheme() {
    var data = collectFormData();
    if (!data.name) { alert('Theme name is required'); return; }
    if (data.palette.length === 0) { alert('At least one palette color is required'); return; }

    // Preserve layers from existing theme if editing
    if (!_creating) {
      var existing = _themes.find(function (t) { return t.name === _selectedName; });
      if (existing) {
        data.layers = existing.layers || [];
        data.variants = existing.variants || [];
      }
    }

    var url, method;
    if (_creating) {
      url = '/themes/create';
      method = 'POST';
    } else {
      url = '/themes/' + encodeURIComponent(_selectedName);
      method = 'PUT';
    }

    fetch(url, {
      method: method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
      .then(function (r) {
        if (!r.ok) return r.json().then(function (d) { throw new Error(d.error); });
        return r.json();
      })
      .then(function () {
        _editing = false;
        _creating = false;
        fetchThemes(data.name);
      })
      .catch(function (err) { alert('Error: ' + err.message); });
  }

  // ── Delete ─────────────────────────────────────────────────────────────────
  function deleteTheme() {
    if (!_selectedName) return;
    if (!confirm('Delete theme "' + _selectedName + '"?')) return;

    fetch('/themes/' + encodeURIComponent(_selectedName), { method: 'DELETE' })
      .then(function (r) {
        if (!r.ok) return r.json().then(function (d) { throw new Error(d.error); });
        return r.json();
      })
      .then(function () {
        _selectedName = null;
        document.getElementById('theme-detail').style.display = 'none';
        document.getElementById('detail-placeholder').style.display = '';
        fetchThemes();
      })
      .catch(function (err) { alert('Error: ' + err.message); });
  }

  // ── Duplicate ──────────────────────────────────────────────────────────────
  function duplicateTheme() {
    if (!_selectedName) return;
    var newName = prompt('Name for the duplicate:', _selectedName + ' (Copy)');
    if (!newName) return;

    fetch('/themes/duplicate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_name: _selectedName, new_name: newName }),
    })
      .then(function (r) {
        if (!r.ok) return r.json().then(function (d) { throw new Error(d.error); });
        return r.json();
      })
      .then(function () {
        fetchThemes(newName);
      })
      .catch(function (err) { alert('Error: ' + err.message); });
  }

  function esc(s) {
    var d = document.createElement('div');
    d.textContent = s || '';
    return d.innerHTML;
  }

  // ── Init ───────────────────────────────────────────────────────────────────
  function init() {
    document.getElementById('btn-new-theme').addEventListener('click', function () {
      _creating = true;
      _selectedName = null;
      renderList();
      document.getElementById('detail-placeholder').style.display = 'none';
      document.getElementById('theme-detail').style.display = '';
      document.getElementById('detail-name').textContent = 'New Theme';
      document.getElementById('detail-builtin-badge').style.display = 'none';
      document.getElementById('btn-edit').style.display = 'none';
      document.getElementById('btn-delete-theme').style.display = 'none';
      document.getElementById('btn-duplicate').style.display = 'none';
      enterEditMode(null);
    });

    document.getElementById('btn-edit').addEventListener('click', function () {
      var theme = _themes.find(function (t) { return t.name === _selectedName; });
      if (theme) enterEditMode(theme);
    });

    document.getElementById('btn-delete-theme').addEventListener('click', deleteTheme);
    document.getElementById('btn-duplicate').addEventListener('click', duplicateTheme);
    document.getElementById('btn-save').addEventListener('click', saveTheme);
    document.getElementById('btn-cancel').addEventListener('click', function () {
      _editing = false;
      _creating = false;
      if (_selectedName) {
        showDetail(_selectedName);
      } else {
        document.getElementById('theme-detail').style.display = 'none';
        document.getElementById('detail-placeholder').style.display = '';
      }
    });

    document.getElementById('btn-add-color').addEventListener('click', function () {
      addColorInput(document.getElementById('edit-palette'), '#ffffff');
    });
    document.getElementById('btn-add-accent').addEventListener('click', function () {
      addColorInput(document.getElementById('edit-accent'), '#ffffff');
    });

    fetchThemes();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
