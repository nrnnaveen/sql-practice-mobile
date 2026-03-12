/**
 * progress_tracker.js – Client-side progress persistence helper.
 *
 * Wraps the /api/progress REST endpoints so that practice_mode.js can
 * save / load progress without knowing about fetch details.
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = factory();
  } else {
    root.ProgressTracker = factory();
  }
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  /**
   * Load progress for a db_type / difficulty.
   *
   * @param  {string}   dbType
   * @param  {string}   difficulty
   * @param  {Function} callback  fn(err, progressObj)
   */
  function load(dbType, difficulty, callback) {
    fetch('/api/progress/' + dbType + '/' + difficulty, {
      credentials: 'same-origin'
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.error) { callback(new Error(data.error), null); return; }
      callback(null, data);
    })
    .catch(function (err) { callback(err, null); });
  }

  /**
   * Save progress for a db_type / difficulty.
   *
   * @param  {string}   dbType
   * @param  {string}   difficulty
   * @param  {Object}   progress  { current_question, completed_ids }
   * @param  {Function} [callback]
   */
  function save(dbType, difficulty, progress, callback) {
    fetch('/api/progress/' + dbType + '/' + difficulty, {
      method : 'POST',
      credentials : 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(progress)
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (typeof callback === 'function') {
        callback(data.error ? new Error(data.error) : null, data);
      }
    })
    .catch(function (err) {
      if (typeof callback === 'function') callback(err, null);
    });
  }

  /**
   * Load all progress rows for the current user.
   *
   * @param  {Function} callback fn(err, progressArray)
   */
  function loadAll(callback) {
    fetch('/api/progress', { credentials: 'same-origin' })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.error) { callback(new Error(data.error), null); return; }
      callback(null, data.progress || []);
    })
    .catch(function (err) { callback(err, null); });
  }

  /**
   * Calculate completion percentage.
   *
   * @param  {Array}  completedIds
   * @param  {number} total
   * @return {number} 0-100
   */
  function pct(completedIds, total) {
    if (!total) return 0;
    return Math.round(((completedIds || []).length / total) * 100);
  }

  return { load: load, save: save, loadAll: loadAll, pct: pct };
}));
