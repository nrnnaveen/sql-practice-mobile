/**
 * visualizer_engine.js – Main animation orchestrator.
 *
 * Exposes a single public API:
 *   VisualizerEngine.run(queryType, sql, animationData, containerEl, statusEl)
 *
 * Plays the appropriate animation sequence in the DB visualization panel and
 * updates the status bar while the animation runs.
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = factory(require('./animations'), require('./query_parser'));
  } else {
    root.VisualizerEngine = factory(root.SQLAnimations, root.QueryParser);
  }
}(typeof self !== 'undefined' ? self : this, function (Animations, QueryParser) {
  'use strict';

  /**
   * Run an animation for the given SQL query.
   *
   * @param {string}      queryType    - One of SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, OTHER
   * @param {string}      sql          - The raw SQL string (used for table name detection)
   * @param {Object}      animationData - JSON from the server (/api/visualizer/animation-data)
   * @param {HTMLElement} containerEl  - The .db-viz-container element
   * @param {HTMLElement} [statusEl]   - Optional .anim-status-bar element
   * @param {Function}    [onDone]     - Callback when animation completes
   */
  function run(queryType, sql, animationData, containerEl, statusEl, onDone) {
    if (!containerEl) return;

    var data  = animationData || {};
    var color = data.color || '#607D8B';
    var desc  = data.description || 'Executing query…';

    // Show status bar
    if (statusEl) {
      statusEl.classList.add('visible');
      var dot = statusEl.querySelector('.anim-status-dot');
      var txt = statusEl.querySelector('.anim-status-text');
      if (dot) dot.style.background = color;
      if (txt) txt.textContent = desc;
    }

    // Run the animation
    if (Animations && typeof Animations.play === 'function') {
      Animations.play(queryType, containerEl, data, sql, function () {
        if (statusEl) statusEl.classList.remove('visible');
        if (typeof onDone === 'function') onDone();
      });
    } else {
      // Fallback: just hide the status bar after the duration
      setTimeout(function () {
        if (statusEl) statusEl.classList.remove('visible');
        if (typeof onDone === 'function') onDone();
      }, data.duration_ms || 2000);
    }
  }

  /**
   * Build a default DB schema visualization inside containerEl from
   * a list of table descriptors.
   *
   * @param {HTMLElement} containerEl
   * @param {Array}       tables  - [{name, columns:[{name,type,pk,fk,idx}], row_count}]
   */
  function renderSchema(containerEl, tables) {
    if (!containerEl) return;
    containerEl.innerHTML = '';

    if (!tables || !tables.length) {
      containerEl.innerHTML = '<span class="dbviz-empty">No table schema available.</span>';
      return;
    }

    tables.forEach(function (tbl) {
      var box = document.createElement('div');
      box.className = 'dbviz-table';
      box.dataset.tableName = tbl.name || '';

      // Header
      var head = document.createElement('div');
      head.className = 'dbviz-table-head';
      head.innerHTML = '<span class="dbviz-table-icon">📋</span>' +
        _esc(tbl.name || 'table');
      box.appendChild(head);

      // Columns
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

      // Row count
      if (tbl.row_count !== undefined) {
        var rc = document.createElement('div');
        rc.className = 'dbviz-row-count';
        rc.textContent = tbl.row_count + ' row' + (tbl.row_count === 1 ? '' : 's');
        box.appendChild(rc);
      }

      containerEl.appendChild(box);
    });
  }

  /** Default tables shown when no schema information is available */
  var DEFAULT_MYSQL_TABLES = [
    {
      name: 'employees',
      columns: [
        {name: 'id',         type: 'INT',          pk: true},
        {name: 'name',       type: 'VARCHAR(100)'},
        {name: 'department', type: 'VARCHAR(50)'},
        {name: 'salary',     type: 'DECIMAL(10,2)'},
        {name: 'hire_date',  type: 'DATE'}
      ],
      row_count: 10
    },
    {
      name: 'orders',
      columns: [
        {name: 'id',          type: 'INT',           pk: true},
        {name: 'employee_id', type: 'INT',           fk: true},
        {name: 'product_id',  type: 'INT',           fk: true},
        {name: 'quantity',    type: 'INT'},
        {name: 'total_price', type: 'DECIMAL(10,2)'},
        {name: 'order_date',  type: 'DATE'}
      ],
      row_count: 25
    },
    {
      name: 'products',
      columns: [
        {name: 'id',       type: 'INT',          pk: true},
        {name: 'name',     type: 'VARCHAR(100)'},
        {name: 'category', type: 'VARCHAR(50)'},
        {name: 'price',    type: 'DECIMAL(10,2)'}
      ],
      row_count: 8
    }
  ];

  var DEFAULT_POSTGRES_TABLES = DEFAULT_MYSQL_TABLES; // same structure

  function _esc(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  return {
    run          : run,
    renderSchema : renderSchema,
    DEFAULT_MYSQL_TABLES    : DEFAULT_MYSQL_TABLES,
    DEFAULT_POSTGRES_TABLES : DEFAULT_POSTGRES_TABLES
  };
}));
