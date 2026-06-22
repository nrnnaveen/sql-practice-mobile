/**
 * clear_button.js – Shared "Clear" button logic for all SQL editors.
 *
 * Exported function: initClearButton(editor, options)
 *   editor   - Monaco editor instance (or null)
 *   options  - optional config:
 *     resultsPanelId   - id of the results panel element (default 'results-panel')
 *     historyListId    - id of the history list element (default 'historyList')
 *     toastFn          - function(message, type) to show a toast notification
 *     onClear          - optional callback called after clearing
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = factory();
  } else {
    root.ClearButton = factory();
  }
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  function initClearButton(editor, options) {
    var opts = options || {};
    var resultsPanelId    = opts.resultsPanelId    || 'results-panel';
    var historyListId     = opts.historyListId      || 'historyList';
    var historyEmptyHtml  = opts.historyEmptyHtml   || '<p class="history-empty">No history yet.</p>';

    function doToast(msg, type) {
      if (typeof opts.toastFn === 'function') {
        opts.toastFn(msg, type);
      } else if (typeof window.showToast === 'function') {
        window.showToast(msg, type, 2000);
      }
    }

    function clearAll() {
      // 1. Clear Monaco editor text ONLY
      if (editor && typeof editor.setValue === 'function') {
        editor.setValue('');
      }

      // 2. Clear database visualization highlights (visual state only, not content)
      document.querySelectorAll('.hl-select,.hl-insert,.hl-update,.hl-delete,.hl-create,.hl-alter').forEach(function (el) {
        el.classList.remove('hl-select','hl-insert','hl-update','hl-delete','hl-create','hl-alter');
      });

      // 3. Show toast feedback
      doToast('✅ Editor cleared!', 'success');

      // 4. Focus back to editor
      if (editor && typeof editor.focus === 'function') {
        editor.focus();
      }

      // 5. Call optional callback
      if (typeof opts.onClear === 'function') {
        opts.onClear();
      }
    }

    // Wire up any element with id="clear-button" or class="clear-btn"
    var clearBtns = document.querySelectorAll('#clear-button, .clear-btn');
    clearBtns.forEach(function (btn) {
      btn.addEventListener('click', clearAll);
    });

    // Keyboard shortcut: Ctrl+Alt+C / Cmd+Alt+C
    document.addEventListener('keydown', function (e) {
      if ((e.ctrlKey || e.metaKey) && e.altKey && e.code === 'KeyC') {
        e.preventDefault();
        clearAll();
      }
    });

    // Return clearAll so callers can invoke it programmatically
    return clearAll;
  }

  return { initClearButton: initClearButton };
}));
