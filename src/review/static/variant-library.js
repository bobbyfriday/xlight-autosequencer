/**
 * Variant Library browser — xLight AutoSequencer
 * Fetches variants and coverage from /variants API, renders filterable list with detail view.
 */
(function () {
  'use strict';

  var state = {
    variants: [],
    filters: { effect: '', energy: '', tier: '', section: '', scope: '', q: '' },
    coverage: [],
    coverageMeta: { total_variants: 0, effects_with_variants: 0, effects_without_variants: 0 },
    selectedVariant: null,
    effectOptions: [],
    searchTimer: null
  };

  // ── DOM refs ────────────────────────────────────────────────────────────
  var els = {};

  function initRefs() {
    els.summaryStats = document.getElementById('summary-stats');
    els.filterEffect = document.getElementById('filter-effect');
    els.filterEnergy = document.getElementById('filter-energy');
    els.filterTier = document.getElementById('filter-tier');
    els.filterSection = document.getElementById('filter-section');
    els.filterScope = document.getElementById('filter-scope');
    els.filterSearch = document.getElementById('filter-search');
    els.btnClear = document.getElementById('btn-clear-filters');
    els.variantList = document.getElementById('variant-list');
    els.detailPanel = document.getElementById('detail-panel');
    els.detailContent = document.getElementById('detail-content');
    els.btnCloseDetail = document.getElementById('btn-close-detail');
    els.coverageToggle = document.getElementById('coverage-toggle');
    els.coverageContent = document.getElementById('coverage-content');
    els.coveragePanel = document.getElementById('coverage-panel');
  }

  // ── API helpers ─────────────────────────────────────────────────────────
  function buildQueryString() {
    var params = [];
    if (state.filters.effect) params.push('effect=' + encodeURIComponent(state.filters.effect));
    if (state.filters.energy) params.push('energy=' + encodeURIComponent(state.filters.energy));
    if (state.filters.tier) params.push('tier=' + encodeURIComponent(state.filters.tier));
    if (state.filters.section) params.push('section=' + encodeURIComponent(state.filters.section));
    if (state.filters.scope) params.push('scope=' + encodeURIComponent(state.filters.scope));
    if (state.filters.q) params.push('q=' + encodeURIComponent(state.filters.q));
    return params.length ? '?' + params.join('&') : '';
  }

  function loadVariants() {
    var url = '/variants' + buildQueryString();
    state._fetchSeq = (state._fetchSeq || 0) + 1;
    var seq = state._fetchSeq;
    fetch(url)
      .then(function (r) {
        if (!r.ok) throw new Error('Server error: ' + r.status);
        return r.json();
      })
      .then(function (data) {
        if (seq !== state._fetchSeq) return; // stale response
        state.variants = data.variants || [];
        updateSummary(data.total, data.filters_applied);
        collectEffectOptions();
        renderVariantList();
        // Close stale detail panel
        if (state.selectedVariant && !state.variants.find(function(v) { return v.name === state.selectedVariant.name; })) {
          closeDetail();
        }
      })
      .catch(function (err) {
        if (seq !== state._fetchSeq) return;
        console.error('Failed to load variants:', err);
        els.variantList.innerHTML = '<div style="padding:20px;color:#ee8e8e">Failed to load variants</div>';
      });
  }

  function loadCoverage() {
    fetch('/variants/coverage')
      .then(function (r) {
        if (!r.ok) throw new Error('Server error: ' + r.status);
        return r.json();
      })
      .then(function (data) {
        state.coverage = data.coverage || [];
        state.coverageMeta = {
          total_variants: data.total_variants,
          effects_with_variants: data.effects_with_variants,
          effects_without_variants: data.effects_without_variants
        };
        renderCoverage();
      })
      .catch(function (err) {
        console.error('Failed to load coverage:', err);
        els.coverageContent.innerHTML = '<div style="padding:20px;color:#ee8e8e">Failed to load coverage data</div>';
      });
  }

  // ── Summary stats ───────────────────────────────────────────────────────
  function updateSummary(total, filtersApplied) {
    var filterKeys = Object.keys(filtersApplied || {});
    var parts = [total + ' variant' + (total !== 1 ? 's' : '')];
    if (filterKeys.length > 0) {
      parts.push('(filtered)');
    }
    els.summaryStats.textContent = '— ' + parts.join(' ');
  }

  // ── Effect dropdown population ──────────────────────────────────────────
  function collectEffectOptions() {
    var seen = {};
    // From loaded variants
    state.variants.forEach(function(v) { seen[v.base_effect] = true; });
    // From coverage (always has all effects)
    state.coverage.forEach(function(c) { if (c.variant_count > 0) seen[c.effect] = true; });
    var names = Object.keys(seen).sort();
    if (names.length === state.effectOptions.length && names.every(function(n, i) { return n === state.effectOptions[i]; })) return;
    state.effectOptions = names;
    populateEffectDropdown();
  }

  function populateEffectDropdown() {
    var select = els.filterEffect;
    // Keep first option
    while (select.options.length > 1) select.remove(1);
    state.effectOptions.forEach(function (name) {
      var opt = document.createElement('option');
      opt.value = name;
      opt.textContent = name;
      select.appendChild(opt);
    });
  }

  // ── Render variant list ─────────────────────────────────────────────────
  function renderVariantList() {
    var container = els.variantList;
    container.innerHTML = '';

    if (state.variants.length === 0) {
      container.innerHTML = '<div class="empty-state">No variants match your filters</div>';
      return;
    }

    // Group by base_effect
    var groups = {};
    var groupOrder = [];
    state.variants.forEach(function (v) {
      if (!groups[v.base_effect]) {
        groups[v.base_effect] = [];
        groupOrder.push(v.base_effect);
      }
      groups[v.base_effect].push(v);
    });

    groupOrder.forEach(function (effectName) {
      var variants = groups[effectName];
      var groupEl = document.createElement('div');
      groupEl.className = 'variant-group';

      var header = document.createElement('div');
      header.className = 'variant-group-header';
      header.innerHTML =
        '<span class="variant-group-chevron">&#9660;</span>' +
        '<span>' + escapeHtml(effectName) + '</span>' +
        '<span class="variant-group-count">(' + variants.length + ')</span>';
      header.addEventListener('click', function () {
        groupEl.classList.toggle('collapsed');
      });
      groupEl.appendChild(header);

      var items = document.createElement('div');
      items.className = 'variant-group-items';

      variants.forEach(function (v) {
        var card = document.createElement('div');
        card.className = 'variant-card';
        if (state.selectedVariant && state.selectedVariant.name === v.name) {
          card.classList.add('selected');
        }

        var name = document.createElement('div');
        name.className = 'variant-card-name';
        name.textContent = v.name;

        var desc = document.createElement('div');
        desc.className = 'variant-card-desc';
        desc.textContent = v.description || '';

        var tags = document.createElement('div');
        tags.className = 'variant-card-tags';
        if (v.tags.energy_level) tags.appendChild(makeBadge(v.tags.energy_level, 'energy'));
        if (v.tags.tier_affinity) tags.appendChild(makeBadge(v.tags.tier_affinity, 'tier'));
        if (v.tags.scope) tags.appendChild(makeBadge(v.tags.scope, 'scope'));
        if (v.tags.speed_feel) tags.appendChild(makeBadge(v.tags.speed_feel, 'speed'));

        card.appendChild(name);
        card.appendChild(desc);
        card.appendChild(tags);

        card.addEventListener('click', function () { selectVariant(v); });
        items.appendChild(card);
      });

      groupEl.appendChild(items);
      container.appendChild(groupEl);
    });
  }

  function makeBadge(text, type) {
    var span = document.createElement('span');
    span.className = 'badge badge-' + type;
    span.textContent = text;
    return span;
  }

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  // ── Select variant and render detail ────────────────────────────────────
  function selectVariant(v) {
    state.selectedVariant = v;
    renderVariantList(); // update selected highlight
    renderDetail(v);
    els.detailPanel.style.display = '';
  }

  function closeDetail() {
    state.selectedVariant = null;
    els.detailPanel.style.display = 'none';
    renderVariantList();
  }

  function renderDetail(v) {
    var html = '';

    // Name
    html += '<h2 class="detail-name">' + escapeHtml(v.name) + '</h2>';

    // Description
    html += '<p class="detail-description">' + escapeHtml(v.description || 'No description') + '</p>';

    // Badges row
    html += '<div class="detail-badges">';
    html += badgeHtml(v.base_effect, 'category');
    if (v.inherited) html += badgeHtml(v.inherited.category, 'category');
    if (v.is_builtin) {
      html += badgeHtml('built-in', 'builtin');
    } else {
      html += badgeHtml('custom', 'custom');
    }
    html += '</div>';

    // Tags section
    html += '<div class="detail-section"><h3>Tags</h3><div class="detail-badges">';
    if (v.tags.energy_level) html += badgeHtml(v.tags.energy_level, 'energy');
    if (v.tags.tier_affinity) html += badgeHtml(v.tags.tier_affinity, 'tier');
    if (v.tags.scope) html += badgeHtml(v.tags.scope, 'scope');
    if (v.tags.speed_feel) html += badgeHtml(v.tags.speed_feel, 'speed');
    if (v.tags.direction) html += badgeHtml(v.tags.direction, 'direction');
    if (v.tags.section_roles && v.tags.section_roles.length) {
      v.tags.section_roles.forEach(function (r) {
        html += badgeHtml(r, 'section');
      });
    }
    if (v.tags.genre_affinity) html += badgeHtml(v.tags.genre_affinity, 'category');
    html += '</div></div>';

    // Direction cycle
    if (v.direction_cycle && v.direction_cycle.length) {
      html += '<div class="detail-section"><h3>Direction Cycle</h3>';
      html += '<div class="direction-cycle">';
      v.direction_cycle.forEach(function (step, i) {
        html += '<span class="direction-step">' + (i + 1) + '. ' + escapeHtml(step) + '</span>';
      });
      html += '</div></div>';
    }

    // Parameter overrides
    if (v.parameter_overrides && Object.keys(v.parameter_overrides).length) {
      html += '<div class="detail-section"><h3>Parameter Overrides</h3>';
      html += '<table class="param-table"><thead><tr><th>Parameter</th><th>Value</th></tr></thead><tbody>';
      Object.keys(v.parameter_overrides).sort().forEach(function (key) {
        html += '<tr><td>' + escapeHtml(key) + '</td><td>' + escapeHtml(String(v.parameter_overrides[key])) + '</td></tr>';
      });
      html += '</tbody></table></div>';
    }

    // Inherited metadata
    if (v.inherited) {
      html += '<div class="detail-section"><h3>Inherited from Base Effect</h3>';
      html += '<div class="detail-badges">';
      if (v.inherited.layer_role) html += badgeHtml(v.inherited.layer_role, 'layer-role');
      if (v.inherited.duration_type) html += badgeHtml(v.inherited.duration_type, 'category');
      html += '</div>';

      // Prop suitability
      if (v.inherited.prop_suitability && Object.keys(v.inherited.prop_suitability).length) {
        html += '<div style="margin-top: 8px"><h3 style="margin:0 0 4px;font-size:11px;text-transform:uppercase;color:var(--text-dim)">Prop Suitability</h3>';
        html += '<div class="suitability-list">';
        Object.keys(v.inherited.prop_suitability).sort().forEach(function (propType) {
          var rating = v.inherited.prop_suitability[propType];
          var scoreClass = 'ok';
          if (rating === 'ideal') scoreClass = 'ideal';
          else if (rating === 'good') scoreClass = 'good';
          else if (rating === 'poor' || rating === 'avoid') scoreClass = 'poor';
          html += '<span class="suitability-item">' +
            escapeHtml(propType) +
            ' <span class="suitability-score ' + scoreClass + '">' + escapeHtml(String(rating)) + '</span>' +
            '</span>';
        });
        html += '</div></div>';
      }
      html += '</div>';
    }

    els.detailContent.innerHTML = html;
  }

  function badgeHtml(text, type) {
    return '<span class="badge badge-' + type + '">' + escapeHtml(text) + '</span>';
  }

  // ── Coverage rendering ──────────────────────────────────────────────────
  function renderCoverage() {
    var meta = state.coverageMeta;
    var coverage = state.coverage;

    var html = '';
    html += '<div class="coverage-summary">';
    html += '<strong>' + meta.total_variants + '</strong> total variants<br>';
    html += '<strong>' + meta.effects_with_variants + '</strong> effects with variants<br>';
    html += '<strong>' + meta.effects_without_variants + '</strong> effects without variants';
    html += '</div>';

    var maxCount = 1;
    coverage.forEach(function (c) { if (c.variant_count > maxCount) maxCount = c.variant_count; });

    coverage.forEach(function (c) {
      var pct = Math.round((c.variant_count / maxCount) * 100);
      var dim = c.variant_count === 0;
      html += '<div class="coverage-bar-row">';
      html += '<span class="coverage-bar-label' + (dim ? ' dim' : '') + '">' + escapeHtml(c.effect) + '</span>';
      html += '<span class="coverage-bar-track"><span class="coverage-bar-fill' + (dim ? ' empty' : '') + '" style="width:' + pct + '%"></span></span>';
      html += '<span class="coverage-bar-count">' + c.variant_count + '</span>';
      html += '</div>';
    });

    els.coverageContent.innerHTML = html;

    // Also populate effect dropdown from coverage (more complete than from variants)
    if (state.effectOptions.length === 0 && coverage.length > 0) {
      coverage.forEach(function (c) {
        if (c.variant_count > 0 && state.effectOptions.indexOf(c.effect) === -1) {
          state.effectOptions.push(c.effect);
        }
      });
      state.effectOptions.sort();
      populateEffectDropdown();
    }
  }

  // ── Filter event binding ────────────────────────────────────────────────
  function bindFilterEvents() {
    // Effect dropdown
    els.filterEffect.addEventListener('change', function () {
      state.filters.effect = this.value;
      loadVariants();
    });

    // Toggle groups (energy, tier, scope)
    bindToggleGroup(els.filterEnergy, 'energy');
    bindToggleGroup(els.filterTier, 'tier');
    bindToggleGroup(els.filterScope, 'scope');

    // Section checkboxes — single selection (radio-like behavior)
    els.filterSection.querySelectorAll('input[type="checkbox"]').forEach(function(cb) {
      cb.addEventListener('change', function() {
        if (this.checked) {
          // Uncheck others — single selection behavior
          els.filterSection.querySelectorAll('input[type="checkbox"]').forEach(function(other) {
            if (other !== cb) other.checked = false;
          });
          state.filters.section = cb.value;
        } else {
          state.filters.section = '';
        }
        loadVariants();
      });
    });

    // Text search with debounce
    els.filterSearch.addEventListener('input', function () {
      var val = this.value.trim();
      clearTimeout(state.searchTimer);
      state.searchTimer = setTimeout(function () {
        state.filters.q = val;
        loadVariants();
      }, 200);
    });

    // Clear filters
    els.btnClear.addEventListener('click', clearFilters);

    // Close detail
    els.btnCloseDetail.addEventListener('click', closeDetail);

    // Coverage toggle
    els.coverageToggle.addEventListener('click', function () {
      els.coveragePanel.classList.toggle('collapsed');
    });
  }

  function bindToggleGroup(container, filterKey) {
    var buttons = container.querySelectorAll('button');
    buttons.forEach(function (btn) {
      btn.addEventListener('click', function () {
        var val = btn.getAttribute('data-value');
        if (btn.classList.contains('active')) {
          btn.classList.remove('active');
          state.filters[filterKey] = '';
        } else {
          buttons.forEach(function (b) { b.classList.remove('active'); });
          btn.classList.add('active');
          state.filters[filterKey] = val;
        }
        loadVariants();
      });
    });
  }

  function clearFilters() {
    state.filters = { effect: '', energy: '', tier: '', section: '', scope: '', q: '' };
    els.filterEffect.value = '';
    els.filterSearch.value = '';
    els.filterEnergy.querySelectorAll('button').forEach(function (b) { b.classList.remove('active'); });
    els.filterTier.querySelectorAll('button').forEach(function (b) { b.classList.remove('active'); });
    els.filterScope.querySelectorAll('button').forEach(function (b) { b.classList.remove('active'); });
    els.filterSection.querySelectorAll('input').forEach(function (cb) { cb.checked = false; });
    closeDetail();
    loadVariants();
  }

  // ── Init ────────────────────────────────────────────────────────────────
  function init() {
    initRefs();
    bindFilterEvents();
    loadVariants();
    loadCoverage();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
