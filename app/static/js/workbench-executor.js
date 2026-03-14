/**
 * workbench-executor.js – AJAX-based query execution for the Workbench editor.
 *
 * WorkbenchExecutor intercepts the SQL form submit, sends the query to
 * /editor/execute-query via fetch(), and updates the UI immediately —
 * without a full page reload.  No loading spinner is shown; instead the
 * Run button briefly switches to "⏳ Executing…" and then returns to normal.
 *
 * Usage:
 *   var executor = new WorkbenchExecutor({
 *     form:          document.getElementById('query-form'),
 *     editorFn:      function() { return monacoEditor.getValue(); },
 *     dbType:        'mysql',
 *     executeUrl:    '/editor/execute-query',
 *     onSuccess:     function(data) { ... },
 *     onError:       function(err)  { ... },
 *   });
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = factory();
  } else {
    root.WorkbenchExecutor = factory();
  }
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  /**
   * @param {Object} opts
   * @param {HTMLFormElement} opts.form         The SQL query form element
   * @param {Function}        opts.editorFn     Returns the current query string
   * @param {string}          opts.dbType       'mysql' | 'postgres'
   * @param {string}          opts.executeUrl   Endpoint URL (default: /editor/execute-query)
   * @param {Function}        opts.onSuccess    Called with (responseData, querySql)
   * @param {Function}        opts.onError      Called with (errorMessage, querySql)
   * @param {HTMLElement}     [opts.runBtn]     The run/submit button (for state feedback)
   * @param {string}          [opts.runBtnOriginalHtml]  Original innerHTML for the button
   */
  function WorkbenchExecutor(opts) {
    this._form        = opts.form;
    this._editorFn    = opts.editorFn;
    this._dbType      = opts.dbType || 'mysql';
    this._executeUrl  = opts.executeUrl || '/editor/execute-query';
    this._onSuccess   = typeof opts.onSuccess === 'function' ? opts.onSuccess : function () {};
    this._onError     = typeof opts.onError   === 'function' ? opts.onError   : function () {};
    this._runBtn      = opts.runBtn || null;
    this._runBtnOrigHtml = opts.runBtnOriginalHtml || (this._runBtn ? this._runBtn.innerHTML : '▶ Run Query');
    this._busy        = false;

    if (this._form) {
      var self = this;
      this._form.addEventListener('submit', function (e) {
        e.preventDefault();
        var query = self._editorFn ? self._editorFn() : '';
        // Sync hidden input if present
        var queryInput = self._form.querySelector('[name="query"]');
        if (queryInput) queryInput.value = query;
        self.execute(query);
      });
    }
  }

  /**
   * Execute a SQL query via AJAX.
   *
   * @param {string} query
   */
  WorkbenchExecutor.prototype.execute = function (query) {
    if (this._busy) return;
    query = (query || '').trim();
    if (!query) {
      this._onError('No query entered.', query);
      return;
    }

    this._busy = true;
    this._setButtonState('executing');

    var body = new FormData();
    body.append('query',    query);
    body.append('database', this._dbType);

    var self = this;
    fetch(this._executeUrl, { method: 'POST', body: body })
      .then(function (resp) {
        if (!resp.ok && resp.status !== 400) {
          throw new Error('Server error ' + resp.status);
        }
        return resp.json();
      })
      .then(function (data) {
        self._busy = false;
        self._setButtonState('idle');
        if (data.error && !data.result) {
          self._onError(data.error, query);
        } else {
          self._onSuccess(data, query);
        }
      })
      .catch(function (err) {
        self._busy = false;
        self._setButtonState('idle');
        self._onError(err.message || String(err), query);
      });
  };

  /* ── Private helpers ─────────────────────────────────────────────────── */

  WorkbenchExecutor.prototype._setButtonState = function (state) {
    if (!this._runBtn) return;
    if (state === 'executing') {
      this._runBtn.disabled = true;
      this._runBtn.innerHTML = '⏳ Executing…';
    } else {
      this._runBtn.disabled = false;
      this._runBtn.innerHTML = this._runBtnOrigHtml;
    }
  };

  return WorkbenchExecutor;
}));
