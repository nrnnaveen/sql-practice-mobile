/**
 * workbench-visualizer.js – DOM rendering for the Workbench schema panel.
 *
 * WorkbenchVisualizer owns a container element and keeps it in sync with a
 * WorkbenchState instance.  It exposes methods to add / remove / refresh
 * individual table cards with optional CSS animations.
 *
 * Usage:
 *   var vis = new WorkbenchVisualizer(containerEl, state);
 *   vis.renderAll();                          // full re-render from state
 *   vis.addTableCard(tbl, animate);           // add or refresh one card
 *   vis.removeTableCard(name, animate);       // remove one card
 *   vis.updateRotationIndicator();            // refresh "Showing N/M" label
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = factory();
  } else {
    root.WorkbenchVisualizer = factory();
  }
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var KNOWN_COLORS = { employees: true, orders: true, products: true };

  /* ── HTML helpers ──────────────────────────────────────────────────── */

  function _esc(s) {
    return String(s)
      .replace(/&/g,  '&amp;')
      .replace(/</g,  '&lt;')
      .replace(/>/g,  '&gt;')
      .replace(/"/g,  '&quot;');
  }

  function _buildTableCard(tbl) {
    var box = document.createElement('div');
    box.className = 'dbviz-table';
    box.dataset.tableName = tbl.name || '';
    if (!KNOWN_COLORS[tbl.name]) {
      box.dataset.tableColor = 'user';
    }

    var icon = tbl.name === 'employees' ? '👥' :
               tbl.name === 'orders'    ? '📦' :
               tbl.name === 'products'  ? '🏷️' : '📋';

    var head = document.createElement('div');
    head.className = 'dbviz-table-head';
    head.innerHTML = '<span class="dbviz-table-icon">' + icon + '</span>' +
      _esc(tbl.name || 'table');
    box.appendChild(head);

    var colList = document.createElement('div');
    colList.className = 'dbviz-col-list';
    (tbl.columns || []).forEach(function (col) {
      var row = document.createElement('div');
      row.className = 'dbviz-col-row';
      var badges = '';
      if (col.pk)  badges += '<span class="dbviz-col-badge pk">PK</span>';
      if (col.fk)  badges += '<span class="dbviz-col-badge fk">FK</span>';
      if (col.idx) badges += '<span class="dbviz-col-badge idx">IDX</span>';
      row.innerHTML = badges +
        '<span class="dbviz-col-name">' + _esc(col.name || '') + '</span>' +
        '<span class="dbviz-col-type">' + _esc(col.type || '') + '</span>';
      colList.appendChild(row);
    });
    box.appendChild(colList);

    if (tbl.row_count !== undefined) {
      var rc = document.createElement('div');
      rc.className = 'dbviz-row-count';
      rc.textContent = tbl.row_count + ' row' + (tbl.row_count === 1 ? '' : 's');
      box.appendChild(rc);
    }

    return box;
  }

  /* ── WorkbenchVisualizer constructor ────────────────────────────────── */

  /**
   * @param {HTMLElement}   containerEl  .db-viz-container element
   * @param {WorkbenchState} state
   * @param {HTMLElement}   [indicatorEl]  Optional element to show "Showing N/M" text
   */
  function WorkbenchVisualizer(containerEl, state, indicatorEl) {
    this._container  = containerEl;
    this._state      = state;
    this._indicator  = indicatorEl || null;
    this.renderAll();
  }

  /* ── Public API ─────────────────────────────────────────────────────── */

  /** Re-render all table cards from state (full refresh). */
  WorkbenchVisualizer.prototype.renderAll = function () {
    if (!this._container) return;
    // Remove all existing table cards (keep non-table elements)
    var existing = this._container.querySelectorAll('.dbviz-table');
    existing.forEach(function (el) { el.parentNode.removeChild(el); });

    var tables = this._state.getTables();
    var self = this;
    tables.forEach(function (tbl) {
      self._container.appendChild(_buildTableCard(tbl));
    });

    this._updateEmpty();
    this.updateRotationIndicator();
  };

  /**
   * Add or refresh one table card.
   *
   * @param {Object}  tbl      { name, columns, row_count }
   * @param {boolean} animate  If true, apply slide-in CSS class
   * @return {string|null}     Name of evicted table (if rotation occurred) or null
   */
  WorkbenchVisualizer.prototype.addTableCard = function (tbl, animate) {
    if (!this._container) return null;

    // Persist to state first (may evict oldest)
    var evicted = this._state.addTable(tbl);

    // If a table was rotated out, remove its card from DOM
    if (evicted) {
      this._animateOut(evicted);
    }

    // Check if the card already exists (update case)
    var existing = this._getCard(tbl.name);
    if (existing) {
      var fresh = _buildTableCard(this._state.getTables().filter(function (t) {
        return t.name === tbl.name;
      })[0] || tbl);
      existing.parentNode.replaceChild(fresh, existing);
    } else {
      var card = _buildTableCard(tbl);
      if (animate) {
        card.classList.add('entering');
      }
      this._container.appendChild(card);
    }

    this._updateEmpty();
    this.updateRotationIndicator();
    return evicted;
  };

  /**
   * Remove a table card from the DOM (and state).
   *
   * @param {string}  name
   * @param {boolean} animate  If true, slide-out animation before removal
   */
  WorkbenchVisualizer.prototype.removeTableCard = function (name, animate) {
    this._state.removeTable(name);
    this._animateOut(name, animate);
    this._updateEmpty();
    this.updateRotationIndicator();
  };

  /**
   * Synchronise the visualizer from a full server schema snapshot.
   * Newly created tables slide in; dropped tables slide out.
   *
   * @param {Array}   serverTables  [{name, columns, row_count}]
   */
  WorkbenchVisualizer.prototype.syncFromSchema = function (serverTables) {
    if (!Array.isArray(serverTables)) return;

    var currentNames = this._state.getTables().map(function (t) { return t.name; });
    var serverNames  = serverTables.map(function (t) { return t.name; });

    // Tables that were dropped
    var self = this;
    currentNames.forEach(function (name) {
      if (serverNames.indexOf(name) === -1) {
        self._state.removeTable(name);
        self._animateOut(name, true);
      }
    });

    // Sync state from server (updates row counts, columns, adds new tables)
    this._state.syncFromSchema(serverTables);

    // Tables that are new (not in current DOM)
    serverTables.forEach(function (st) {
      var card = self._getCard(st.name);
      if (!card) {
        // New table – add with animation
        var newCard = _buildTableCard(st);
        newCard.classList.add('entering');
        self._container.appendChild(newCard);
      } else {
        // Existing table – refresh card (row count may have changed)
        var fresh = _buildTableCard(st);
        card.parentNode.replaceChild(fresh, card);
      }
    });

    this._updateEmpty();
    this.updateRotationIndicator();
  };

  /** Refresh the rotation indicator label (e.g. "Showing 5 / 8 tables"). */
  WorkbenchVisualizer.prototype.updateRotationIndicator = function () {
    if (!this._indicator) return;
    var count = this._state.getTableCount();
    var max   = this._state.getMaxTables();
    if (count === 0) {
      this._indicator.textContent = '';
      this._indicator.style.display = 'none';
    } else {
      this._indicator.style.display = '';
      this._indicator.textContent = count > max
        ? 'Showing ' + max + ' / ' + count + ' tables'
        : count + ' table' + (count === 1 ? '' : 's');
    }
  };

  /* ── Private helpers ─────────────────────────────────────────────────── */

  WorkbenchVisualizer.prototype._getCard = function (name) {
    return this._container
      ? this._container.querySelector('[data-table-name="' + name + '"]')
      : null;
  };

  WorkbenchVisualizer.prototype._animateOut = function (name, animate) {
    var card = this._getCard(name);
    if (!card) return;
    if (animate) {
      card.classList.add('leaving');
      setTimeout(function () {
        if (card.parentNode) card.parentNode.removeChild(card);
      }, 550);
    } else {
      if (card.parentNode) card.parentNode.removeChild(card);
    }
  };

  WorkbenchVisualizer.prototype._updateEmpty = function () {
    if (!this._container) return;
    var tables = this._container.querySelectorAll('.dbviz-table');
    var empty  = this._container.querySelector('.dbviz-empty');
    if (tables.length === 0) {
      if (!empty) {
        var span = document.createElement('span');
        span.className = 'dbviz-empty';
        span.textContent = 'No tables yet. Create a table to see it here.';
        this._container.appendChild(span);
      }
    } else if (empty) {
      empty.parentNode.removeChild(empty);
    }
  };

  return WorkbenchVisualizer;
}));
