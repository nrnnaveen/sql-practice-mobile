/**
 * animations.js – Per-query-type animation functions.
 *
 * Each exported function receives:
 *   container  - HTMLElement  The .db-viz-container element
 *   data       - Object       The animation_data dict from the server
 *   onComplete - Function     Called when the animation finishes
 *
 * Animations use CSS class transitions + vanilla JS timing (no external
 * dependency) so they work even if GSAP is not loaded.  When GSAP is
 * present on the page it is used for smoother physics-based easing.
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = factory();
  } else {
    root.SQLAnimations = factory();
  }
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  /* ── Helpers ── */
  function qs(sel, ctx) { return (ctx || document).querySelector(sel); }
  function qsa(sel, ctx) { return Array.from((ctx || document).querySelectorAll(sel)); }

  function addCls(el, cls) { if (el) el.classList.add(cls); }
  function rmCls(el, cls)  { if (el) el.classList.remove(cls); }

  function after(ms, fn) { return setTimeout(fn, ms); }

  /* Remove highlight classes added during an animation */
  function clearHighlights(container) {
    var hlCls = [
      'hl-select','hl-insert','hl-update','hl-delete','hl-create','hl-alter',
      'hl-col', 'new-row-highlight', 'anim-cell-flash', 'anim-row-delete',
      'anim-bounce-in', 'anim-scale-pop'
    ];
    qsa('.dbviz-table', container).forEach(function (t) {
      hlCls.forEach(function (c) { rmCls(t, c); });
    });
    qsa('.dbviz-col-row', container).forEach(function (c) {
      rmCls(c, 'hl-col');
    });
    // Remove any ephemeral elements (new-row indicators etc.)
    qsa('.dbviz-new-row-indicator, .dbviz-deleted-row-indicator, .flying-row', container)
      .forEach(function (el) { el.parentNode && el.parentNode.removeChild(el); });
  }

  /* Find the first table element in container or the one whose name matches
     the first word in the SQL FROM clause */
  function findTargetTable(container, sql) {
    var tables = qsa('.dbviz-table', container);
    if (!tables.length) return null;
    if (sql) {
      var m = sql.match(/(?:FROM|INTO|UPDATE|TABLE)\s+`?(\w+)`?/i);
      if (m) {
        var name = m[1].toLowerCase();
        var found = tables.filter(function (t) {
          return (t.dataset.tableName || '').toLowerCase() === name;
        })[0];
        if (found) return found;
      }
    }
    return tables[0];
  }

  /* ── SELECT animation ── */
  function animateSelect(container, data, sql, onComplete) {
    clearHighlights(container);
    var table = findTargetTable(container, sql);
    if (!table) { after(100, onComplete); return; }

    // 0s – blue glow on table
    addCls(table, 'hl-select');

    // 0.5s – highlight column headers
    after(500, function () {
      qsa('.dbviz-col-row', table).forEach(function (col) {
        addCls(col, 'hl-col');
      });
    });

    // 1.5s – create a flying-row element that moves toward the result area
    after(1500, function () {
      var rect = table.getBoundingClientRect();
      var vizRect = container.getBoundingClientRect();
      var flyEl = document.createElement('div');
      flyEl.className = 'flying-row';
      flyEl.textContent = '📋 rows →';
      flyEl.style.left = (rect.left - vizRect.left + 10) + 'px';
      flyEl.style.top  = (rect.top  - vizRect.top  + rect.height / 2) + 'px';
      container.style.position = 'relative';
      container.appendChild(flyEl);

      // Slide it to the right
      flyEl.style.transition = 'transform 0.8s ease, opacity 0.8s ease';
      after(30, function () {
        flyEl.style.transform = 'translateX(120px)';
        flyEl.style.opacity = '0';
      });
      after(900, function () {
        flyEl.parentNode && flyEl.parentNode.removeChild(flyEl);
      });
    });

    // 2.5s – fade highlights
    after(2500, function () {
      rmCls(table, 'hl-select');
      qsa('.dbviz-col-row', table).forEach(function (col) { rmCls(col, 'hl-col'); });
    });

    after(data.duration_ms || 3000, onComplete);
  }

  /* ── INSERT animation ── */
  function animateInsert(container, data, sql, onComplete) {
    clearHighlights(container);
    var table = findTargetTable(container, sql);
    if (!table) { after(100, onComplete); return; }

    // 0s – green glow
    addCls(table, 'hl-insert');

    // 1s – new row indicator slides in
    after(1000, function () {
      var indicator = document.createElement('div');
      indicator.className = 'dbviz-new-row-indicator anim-bounce-in';
      indicator.innerHTML = '➕ new row inserted';
      var colList = qs('.dbviz-col-list', table);
      if (colList) {
        colList.parentNode.insertBefore(indicator, colList.nextSibling);
      } else {
        table.appendChild(indicator);
      }
    });

    // 3s – fade highlights
    after(3000, function () {
      rmCls(table, 'hl-insert');
    });

    after(data.duration_ms || 3500, onComplete);
  }

  /* ── UPDATE animation ── */
  function animateUpdate(container, data, sql, onComplete) {
    clearHighlights(container);
    var table = findTargetTable(container, sql);
    if (!table) { after(100, onComplete); return; }

    // 0s – orange glow
    addCls(table, 'hl-update');

    // 1s – flash individual columns
    after(1000, function () {
      qsa('.dbviz-col-row', table).forEach(function (col, i) {
        after(i * 120, function () { addCls(col, 'anim-cell-flash'); });
      });
    });

    // 3s – fade
    after(3000, function () {
      rmCls(table, 'hl-update');
      qsa('.dbviz-col-row', table).forEach(function (col) {
        rmCls(col, 'anim-cell-flash');
      });
    });

    after(data.duration_ms || 3500, onComplete);
  }

  /* ── DELETE animation ── */
  function animateDelete(container, data, sql, onComplete) {
    clearHighlights(container);
    var table = findTargetTable(container, sql);
    if (!table) { after(100, onComplete); return; }

    // 0s – red border
    addCls(table, 'hl-delete');

    // 1s – deleted row indicator
    after(1000, function () {
      var indicator = document.createElement('div');
      indicator.className = 'dbviz-deleted-row-indicator';
      indicator.innerHTML = '🗑️ row removed';
      var colList = qs('.dbviz-col-list', table);
      if (colList) {
        colList.parentNode.insertBefore(indicator, colList.nextSibling);
      } else {
        table.appendChild(indicator);
      }
    });

    // 2s – slide table slightly
    after(2000, function () {
      table.style.transition = 'transform 0.3s ease';
      table.style.transform = 'translateX(4px)';
      after(300, function () { table.style.transform = ''; });
    });

    // 3.5s – fade highlights
    after(3500, function () {
      rmCls(table, 'hl-delete');
    });

    after(data.duration_ms || 3500, onComplete);
  }

  /* ── CREATE animation ── */
  function animateCreate(container, data, sql, onComplete) {
    clearHighlights(container);

    // Try to find an existing table first
    var table = findTargetTable(container, sql);

    if (table) {
      // Animate the existing placeholder table
      addCls(table, 'hl-create');
      addCls(table, 'anim-scale-pop');

      // Stagger columns sliding in
      after(1000, function () {
        qsa('.dbviz-col-row', table).forEach(function (col, i) {
          col.style.opacity = '0';
          col.style.transform = 'translateX(-20px)';
          after(i * 200, function () {
            col.style.transition = 'transform 0.4s ease, opacity 0.4s ease';
            col.style.transform = '';
            col.style.opacity = '';
          });
        });
      });

      // 3s – fade highlight
      after(3000, function () { rmCls(table, 'hl-create'); });
    }
    // If no existing table, the WorkbenchVisualizer handles adding it via
    // createTableManager.addTable() which applies the entering CSS class.

    after(data.duration_ms || 3500, onComplete);
  }

  /* ── DROP animation ── */
  function animateDrop(container, data, sql, onComplete) {
    clearHighlights(container);
    var table = findTargetTable(container, sql);
    if (!table) { after(100, onComplete); return; }

    // Apply red glow + slide-out-left animation via CSS class
    addCls(table, 'hl-drop');

    // Remove from DOM after animation completes
    after(600, function () {
      if (table.parentNode) table.parentNode.removeChild(table);
    });

    after(data.duration_ms || 2000, onComplete);
  }

  /* ── ALTER animation ── */
  function animateAlter(container, data, sql, onComplete) {
    clearHighlights(container);
    var table = findTargetTable(container, sql);
    if (!table) { after(100, onComplete); return; }

    addCls(table, 'hl-alter');
    after(1000, function () {
      table.style.transition = 'transform 0.2s ease';
      table.style.transform = 'scale(1.03)';
      after(300, function () { table.style.transform = ''; });
    });
    after(2500, function () { rmCls(table, 'hl-alter'); });
    after(data.duration_ms || 3000, onComplete);
  }

  /* ── Default / OTHER ── */
  function animateOther(container, data, sql, onComplete) {
    clearHighlights(container);
    var tables = qsa('.dbviz-table', container);
    tables.forEach(function (t) {
      t.style.transition = 'box-shadow 0.3s';
      t.style.boxShadow = '0 0 12px rgba(96,125,139,0.4)';
    });
    after(1500, function () {
      tables.forEach(function (t) { t.style.boxShadow = ''; });
    });
    after(data.duration_ms || 2000, onComplete);
  }

  /* ── Public dispatcher ── */
  function play(queryType, container, data, sql, onComplete) {
    var cb = typeof onComplete === 'function' ? onComplete : function () {};
    var fn = {
      SELECT: animateSelect,
      INSERT: animateInsert,
      UPDATE: animateUpdate,
      DELETE: animateDelete,
      CREATE: animateCreate,
      ALTER : animateAlter,
      DROP  : animateDrop
    }[queryType] || animateOther;

    fn(container, data || {}, sql || '', cb);
  }

  return { play: play, clearHighlights: clearHighlights };
}));
