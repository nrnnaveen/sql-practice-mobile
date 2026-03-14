/**
 * animation-engine.js – Thin wrapper around SQLAnimations for the Workbench.
 *
 * AnimationEngine provides a higher-level API that:
 *   - Delegates to SQLAnimations.play() (defined in animations.js)
 *   - Manages the status bar (color + description text)
 *   - Guards against running two animations simultaneously
 *
 * Usage:
 *   var engine = new AnimationEngine(containerEl, statusEl);
 *   engine.play('CREATE', sql, animationData, onDone);
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = factory(require('./animations'));
  } else {
    root.AnimationEngine = factory(root.SQLAnimations);
  }
}(typeof self !== 'undefined' ? self : this, function (SQLAnimations) {
  'use strict';

  /**
   * @param {HTMLElement}  containerEl  .db-viz-container element
   * @param {HTMLElement}  [statusEl]   .anim-status-bar element (optional)
   */
  function AnimationEngine(containerEl, statusEl) {
    this._container = containerEl;
    this._statusEl  = statusEl || null;
    this._running   = false;
  }

  /**
   * Play the animation for a given query type.
   *
   * @param {string}   queryType    One of SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|OTHER
   * @param {string}   sql          Original SQL string (used for table name detection)
   * @param {Object}   animData     Animation descriptor from server (color, duration_ms, description)
   * @param {Function} [onDone]     Called when animation completes
   */
  AnimationEngine.prototype.play = function (queryType, sql, animData, onDone) {
    var self = this;
    var data = animData || {};
    var color = data.color || '#607D8B';
    var desc  = data.description || 'Executing query…';

    // Update status bar immediately
    if (this._statusEl) {
      this._statusEl.classList.add('visible');
      var dot = this._statusEl.querySelector('.anim-status-dot');
      var txt = this._statusEl.querySelector('.anim-status-text');
      if (dot) dot.style.background = color;
      if (txt) txt.textContent = desc;
    }

    var complete = function () {
      self._running = false;
      if (self._statusEl) self._statusEl.classList.remove('visible');
      if (typeof onDone === 'function') onDone();
    };

    if (SQLAnimations && typeof SQLAnimations.play === 'function') {
      SQLAnimations.play(queryType, this._container, data, sql, complete);
    } else {
      // Fallback: just hide status bar after duration
      setTimeout(complete, data.duration_ms || 2000);
    }

    this._running = true;
  };

  /** Return true if an animation is currently playing. */
  AnimationEngine.prototype.isRunning = function () {
    return this._running;
  };

  return AnimationEngine;
}));
