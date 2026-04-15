'use strict';

// brief-presets.js — Preset → raw config mapping for the Creative Brief (spec 047).
// Authoritative source: specs/047-creative-brief/research.md §1.
//
// This module attaches BRIEF_PRESETS and resolveBriefToPost(brief) to window.
// Phase 4 (spec 048) will consume this map server-side, at which point the
// client-side smart-default ruleset in brief-tab.js can be deleted.

(function () {
  window.BRIEF_PRESETS = {};
  window.resolveBriefToPost = function resolveBriefToPost(_brief) {
    return {};
  };
})();
