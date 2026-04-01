/**
 * Shared navigation bar for xlight-analyze.
 * Auto-injects a <nav> at the top of <body> on DOMContentLoaded.
 */
(function () {
  'use strict';

  const NAV_ITEMS = [
    { label: 'Song Library', href: '/', icon: '&#9836;' },
    { label: 'Theme Editor', href: '/themes/', icon: '&#9672;' },
    { label: 'Layout Grouping', href: '/grouper', icon: '&#9638;' },
  ];

  // Song-specific tool pages that should show a breadcrumb
  const SONG_TOOL_PAGES = {
    '/timeline': 'Timeline',
    '/story-review': 'Story Review',
    '/phonemes-view': 'Phonemes',
    '/sweep-view': 'Sweep Results',
  };

  function getActivePath() {
    return window.location.pathname;
  }

  function isSongToolPage(path) {
    return SONG_TOOL_PAGES.hasOwnProperty(path);
  }

  function buildNav() {
    const nav = document.createElement('nav');
    nav.id = 'xlight-navbar';
    nav.className = 'xlight-navbar';

    // Brand
    const brand = document.createElement('a');
    brand.href = '/';
    brand.className = 'navbar-brand';
    brand.textContent = 'xLight';
    nav.appendChild(brand);

    // Nav links
    const linksWrap = document.createElement('div');
    linksWrap.className = 'navbar-links';

    const currentPath = getActivePath();

    NAV_ITEMS.forEach(function (item) {
      const a = document.createElement('a');
      a.href = item.href;
      a.className = 'navbar-link';
      a.innerHTML = '<span class="navbar-icon">' + item.icon + '</span> ' + item.label;

      // Active state: exact match or song tool pages highlight Song Library
      if (item.href === currentPath) {
        a.classList.add('active');
      } else if (item.href === '/' && isSongToolPage(currentPath)) {
        a.classList.add('active-parent');
      }

      linksWrap.appendChild(a);
    });

    nav.appendChild(linksWrap);

    // Breadcrumb for song tool pages
    if (isSongToolPage(currentPath)) {
      const breadcrumb = document.createElement('div');
      breadcrumb.className = 'navbar-breadcrumb';
      breadcrumb.id = 'navbar-breadcrumb';

      const homeLink = document.createElement('a');
      homeLink.href = '/';
      homeLink.textContent = 'Song Library';
      breadcrumb.appendChild(homeLink);

      const sep1 = document.createElement('span');
      sep1.className = 'breadcrumb-sep';
      sep1.textContent = ' \u203A ';
      breadcrumb.appendChild(sep1);

      const songName = document.createElement('span');
      songName.className = 'breadcrumb-song';
      songName.id = 'breadcrumb-song-name';
      songName.textContent = 'Song';
      breadcrumb.appendChild(songName);

      const sep2 = document.createElement('span');
      sep2.className = 'breadcrumb-sep';
      sep2.textContent = ' \u203A ';
      breadcrumb.appendChild(sep2);

      const toolName = document.createElement('span');
      toolName.className = 'breadcrumb-tool';
      toolName.textContent = SONG_TOOL_PAGES[currentPath];
      breadcrumb.appendChild(toolName);

      nav.appendChild(breadcrumb);
    }

    return nav;
  }

  function inject() {
    var nav = buildNav();
    document.body.insertBefore(nav, document.body.firstChild);
    document.body.classList.add('has-navbar');
  }

  /**
   * Update the breadcrumb song name (call from page JS once the title is known).
   */
  window.xlightNavbar = {
    setSongName: function (name) {
      var el = document.getElementById('breadcrumb-song-name');
      if (el) el.textContent = name;
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inject);
  } else {
    inject();
  }
})();
