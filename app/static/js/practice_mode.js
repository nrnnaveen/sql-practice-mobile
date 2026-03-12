/**
 * practice_mode.js – Main controller for the Practice Question page.
 *
 * Responsibilities:
 *  - Wire up the Run Query button to the /practice/.../run endpoint
 *  - Parse the returned query_type and trigger the appropriate animation
 *  - Update the progress bar and congratulations UI
 *  - Load the database schema visualization on page load
 *
 * This script is loaded at the bottom of practice_question.html and
 * relies on globals set there:
 *   DB_TYPE, DIFFICULTY, Q_ID, TOTAL_Q, IS_COMPLETED
 *
 * It expects the following elements in the DOM:
 *   #vizContainer       – .db-viz-container
 *   #animStatusBar      – .anim-status-bar
 *   #animStatusDot      – .anim-status-dot inside the bar
 *   #animStatusText     – .anim-status-text inside the bar
 *   #resultArea         – where query results are rendered
 *   #congratsCard       – congratulations banner
 *   #nextBtnWrap        – container for "Next Question" button
 *   #progressFill       – progress bar fill element
 */
(function () {
  'use strict';

  /* ── Initialise visualizer ── */
  var vizContainer = document.getElementById('vizContainer');
  var animStatusBar = document.getElementById('animStatusBar');

  if (vizContainer && window.VisualizerEngine) {
    var tables = DB_TYPE === 'postgres'
      ? VisualizerEngine.DEFAULT_POSTGRES_TABLES
      : VisualizerEngine.DEFAULT_MYSQL_TABLES;
    VisualizerEngine.renderSchema(vizContainer, tables);
  }

  /* ── HTML escaping ── */
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  /* ── Result rendering ── */
  function renderResult(data) {
    var area = document.getElementById('resultArea');
    var html = '';

    if (data.error) {
      html = '<div class="result-card"><p class="error-msg">&#10006; ' + esc(data.error) + '</p></div>';
      area.innerHTML = html;
      return;
    }

    var meta = '';
    if (data.execution_time !== undefined) {
      meta = '<div class="result-meta">Execution time: ' + data.execution_time.toFixed(3) + 's</div>';
    }

    if (data.columns && data.rows) {
      var tbl = '<div class="table-scroll"><table><thead><tr>';
      data.columns.forEach(function (c) { tbl += '<th>' + esc(c) + '</th>'; });
      tbl += '</tr></thead><tbody>';
      data.rows.forEach(function (row) {
        tbl += '<tr>';
        row.forEach(function (cell) { tbl += '<td>' + esc(cell) + '</td>'; });
        tbl += '</tr>';
      });
      tbl += '</tbody></table></div>';
      html = '<div class="result-card">' + meta +
        '<p class="result-meta">' + data.rows.length + ' row(s) returned</p>' + tbl + '</div>';
    } else if (data.message) {
      html = '<div class="result-card">' + meta +
        '<p class="success-msg">&#10003; ' + esc(data.message) + '</p></div>';
    }

    area.innerHTML = html;

    /* Congratulations */
    if (data.congratulations) {
      var card = document.getElementById('congratsCard');
      card.style.display = 'block';
      card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

      // Show sample answer button
      var sampleBtn = document.querySelector('.sample-btn');
      if (!sampleBtn) {
        var runBar = document.querySelector('.run-bar');
        sampleBtn = document.createElement('button');
        sampleBtn.className = 'sample-btn';
        sampleBtn.textContent = '📖 Sample Answer';
        sampleBtn.onclick = window.toggleSampleAnswer;
        runBar.appendChild(sampleBtn);
      }

      var wrap = document.getElementById('nextBtnWrap');
      if (data.all_complete) {
        wrap.innerHTML = '<a href="/practice/' + DB_TYPE + '/' + DIFFICULTY + '/complete" class="btn-next">🏆 View Certificate!</a>';
      } else {
        var nextQ = data.next_question || (Q_ID + 1);
        wrap.innerHTML = '<a href="/practice/' + DB_TYPE + '/' + DIFFICULTY + '/' + nextQ + '" class="btn-next">Next Question →</a>';
      }

      if (data.completed_ids) {
        var pct = Math.round((data.completed_ids.length / TOTAL_Q) * 100);
        document.getElementById('progressFill').style.width = pct + '%';
      }
    }

    /* History */
    if (data.history) {
      renderHistory(data.history);
    }
  }

  /* ── History rendering ── */
  function renderHistory(items) {
    var list = document.getElementById('historyList');
    if (!list) return;
    var html = '';
    items.forEach(function (item) {
      html += '<div class="history-item" onclick="loadHistoryQuery(' + JSON.stringify(item.query) + ')">';
      html += '<span class="history-query">' + esc(item.query) + '</span>';
      html += '<span style="font-size:.75rem;color:' + (item.success ? '#4ade80' : '#f87171') + ';">';
      html += (item.success ? '✓ ' : '✗ ');
      if (item.execution_time != null) html += item.execution_time.toFixed(3) + 's';
      html += '</span></div>';
    });
    list.innerHTML = html || '<p class="history-empty">No history yet.</p>';
  }

  /* ── Run query ── */
  window.practiceRunQuery = function (query) {
    if (!query) return;

    var runBtn  = document.getElementById('runBtn');
    var spinner = document.getElementById('runSpinner');
    if (runBtn)  runBtn.disabled = true;
    if (spinner) spinner.classList.remove('hidden');

    // Optimistically play animation before server responds
    var localType = window.QueryParser
      ? window.QueryParser.parseQueryType(query)
      : 'OTHER';

    if (vizContainer && window.VisualizerEngine && window.SQLAnimations) {
      var localData = { duration_ms: 1500, color: '#607D8B', description: 'Executing…' };
      VisualizerEngine.run(localType, query, localData, vizContainer, animStatusBar);
    }

    fetch('/practice/' + DB_TYPE + '/' + DIFFICULTY + '/' + Q_ID + '/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query })
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (runBtn)  runBtn.disabled = false;
      if (spinner) spinner.classList.add('hidden');

      // Play server-driven animation if we got animation_data back
      if (data.animation_data && vizContainer && window.VisualizerEngine) {
        VisualizerEngine.run(
          data.query_type || localType,
          query,
          data.animation_data,
          vizContainer,
          animStatusBar
        );
      }

      renderResult(data);
    })
    .catch(function (err) {
      if (runBtn)  runBtn.disabled = false;
      if (spinner) spinner.classList.add('hidden');
      renderResult({ error: 'Network error: ' + err.message });
    });
  };

}());
