/**
 * workbench-state.js – Persistent state management for the Workbench editor.
 *
 * WorkbenchState keeps a localStorage-backed cache of:
 *   - The tables currently displayed (up to MAX_TABLES, FIFO rotation)
 *   - A lightweight query history log
 *
 * Usage:
 *   var state = new WorkbenchState('mysql');
 *   state.syncFromSchema([{name, columns, row_count}]);
 *   state.addTable({name, columns, row_count});
 *   state.removeTable('tableName');
 *   state.getTables();     // → array of table objects
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = factory();
  } else {
    root.WorkbenchState = factory();
  }
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var MAX_TABLES = 5;
  var STORAGE_PREFIX = 'sqlp_wb_state_';

  /**
   * @param {string} dbType  'mysql' | 'postgres' – used to namespace localStorage key
   */
  function WorkbenchState(dbType) {
    this._key = STORAGE_PREFIX + (dbType || 'mysql');
    this._tables = [];   // [{name, columns, row_count, created_at}]
    this._load();
  }

  /* ── Serialization ──────────────────────────────────────────────────── */

  WorkbenchState.prototype._load = function () {
    try {
      var raw = localStorage.getItem(this._key);
      if (raw) {
        var data = JSON.parse(raw);
        this._tables = Array.isArray(data.tables) ? data.tables : [];
      }
    } catch (e) {
      this._tables = [];
    }
  };

  WorkbenchState.prototype._save = function () {
    try {
      localStorage.setItem(this._key, JSON.stringify({ tables: this._tables }));
    } catch (e) { /* ignore quota errors */ }
  };

  /* ── Table management ───────────────────────────────────────────────── */

  /**
   * Add or refresh a table in the cache.
   * If adding a new table pushes count above MAX_TABLES, the oldest is evicted.
   *
   * @param  {Object}  tbl  { name, columns, row_count }
   * @return {string|null}  Name of the table that was evicted (or null)
   */
  WorkbenchState.prototype.addTable = function (tbl) {
    if (!tbl || !tbl.name) return null;

    // Remove existing entry for same name (we'll re-add updated version)
    this._tables = this._tables.filter(function (t) { return t.name !== tbl.name; });

    // Append new/updated entry with timestamp
    this._tables.push({
      name:       tbl.name,
      columns:    tbl.columns    || [],
      row_count:  tbl.row_count  !== undefined ? tbl.row_count : 0,
      created_at: tbl.created_at || Date.now(),
    });

    var evicted = null;
    if (this._tables.length > MAX_TABLES) {
      // Sort oldest-first, evict the first one
      this._tables.sort(function (a, b) { return (a.created_at || 0) - (b.created_at || 0); });
      evicted = this._tables.shift().name;
    }

    this._save();
    return evicted;
  };

  /**
   * Remove a table from the cache by name.
   *
   * @param  {string} name
   * @return {boolean} true if the table was found and removed
   */
  WorkbenchState.prototype.removeTable = function (name) {
    var before = this._tables.length;
    this._tables = this._tables.filter(function (t) { return t.name !== name; });
    var removed = this._tables.length < before;
    if (removed) this._save();
    return removed;
  };

  /**
   * Update the row_count of a table by a delta (positive or negative).
   *
   * @param {string} tableName
   * @param {number} delta
   */
  WorkbenchState.prototype.updateRowCount = function (tableName, delta) {
    var tbl = this._findByName(tableName);
    if (tbl) {
      tbl.row_count = Math.max(0, (tbl.row_count || 0) + delta);
      this._save();
    }
  };

  /**
   * Synchronise the cache from a fresh server-side schema snapshot.
   * Tables that exist in the DB but not yet in cache are added (up to MAX_TABLES).
   * Tables no longer in the DB are removed from cache.
   * Existing tables have their row_count and column list refreshed.
   *
   * @param {Array} serverTables  [{name, columns, row_count}]
   */
  WorkbenchState.prototype.syncFromSchema = function (serverTables) {
    if (!Array.isArray(serverTables)) return;

    var serverNames = serverTables.map(function (t) { return t.name; });

    // Remove tables no longer in DB
    this._tables = this._tables.filter(function (t) {
      return serverNames.indexOf(t.name) !== -1;
    });

    // Update or add tables from server
    var self = this;
    serverTables.forEach(function (st) {
      var existing = self._findByName(st.name);
      if (existing) {
        existing.columns   = st.columns   || existing.columns;
        existing.row_count = st.row_count !== undefined ? st.row_count : existing.row_count;
      } else {
        // New table from server: add it (may evict oldest if over limit)
        self.addTable(st);
      }
    });

    this._save();
  };

  /** Return a copy of the current table list (oldest → newest). */
  WorkbenchState.prototype.getTables = function () {
    return this._tables.slice().sort(function (a, b) {
      return (a.created_at || 0) - (b.created_at || 0);
    });
  };

  /** Return number of tables currently in cache. */
  WorkbenchState.prototype.getTableCount = function () {
    return this._tables.length;
  };

  /** Return the maximum number of tables displayed simultaneously. */
  WorkbenchState.prototype.getMaxTables = function () {
    return MAX_TABLES;
  };

  /** Clear all cached state (useful when switching databases). */
  WorkbenchState.prototype.clearAll = function () {
    this._tables = [];
    this._save();
  };

  /* ── Private helpers ────────────────────────────────────────────────── */

  WorkbenchState.prototype._findByName = function (name) {
    for (var i = 0; i < this._tables.length; i++) {
      if (this._tables[i].name === name) return this._tables[i];
    }
    return null;
  };

  return WorkbenchState;
}));
