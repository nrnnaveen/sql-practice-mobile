/**
 * SQL Practice Mobile – Enhanced editor script
 *
 * Features:
 *  - Theme toggle (dark / light)
 *  - Toast notifications
 *  - Query bookmarks (save / list / delete)
 *  - Query templates
 *  - History search
 *  - Run-button loading state
 *  - Result export (CSV / JSON)
 *  - Keyboard shortcuts (Ctrl+S, Ctrl+K, Ctrl+T, Esc)
 *  - Pagination helper
 */

// ── Utility helpers ──────────────────────────────────────────────────────────

function saveQuery() {
  document.getElementById("query").value = window.editor ? window.editor.getValue() : "";
}

function loadQuery(q) {
  if (window.editor) { window.editor.setValue(q); }
}

function goToPage(page) {
  document.getElementById("page-input").value = page;
  saveQuery();
  document.getElementById("query-form").submit();
}

// ── Toast notifications ───────────────────────────────────────────────────────

function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  // Trigger fade-in on next frame
  requestAnimationFrame(() => toast.classList.add("toast-visible"));
  setTimeout(() => {
    toast.classList.remove("toast-visible");
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// ── Modal helpers ─────────────────────────────────────────────────────────────

function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.remove("hidden");
    modal.setAttribute("aria-hidden", "false");
  }
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.add("hidden");
    modal.setAttribute("aria-hidden", "true");
  }
}

function closeAllModals() {
  document.querySelectorAll(".modal").forEach(m => {
    m.classList.add("hidden");
    m.setAttribute("aria-hidden", "true");
  });
}

// Close modal when clicking the backdrop
document.addEventListener("click", function (e) {
  if (e.target.classList.contains("modal")) {
    closeAllModals();
  }
});

// ── Theme toggle ──────────────────────────────────────────────────────────────

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const icon = document.getElementById("theme-icon");
  if (icon) icon.textContent = theme === "dark" ? "☀" : "☽";
  // Update Monaco editor theme if loaded
  if (window.monaco) {
    monaco.editor.setTheme(theme === "light" ? "vs" : "vs-dark");
  }
  localStorage.setItem("sqlp_theme", theme);
  // Persist to server (best-effort)
  fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ theme }),
  }).catch(() => {/* silently ignore */});
}

document.addEventListener("DOMContentLoaded", function () {
  const toggleBtn = document.getElementById("theme-toggle");
  if (toggleBtn) {
    toggleBtn.addEventListener("click", function () {
      const current = document.documentElement.dataset.theme || "dark";
      applyTheme(current === "dark" ? "light" : "dark");
    });
  }

  // Apply persisted theme from localStorage (client-side, instant)
  const saved = localStorage.getItem("sqlp_theme");
  if (saved && saved !== document.documentElement.dataset.theme) {
    applyTheme(saved);
  }

  // ── Run button loading state ───────────────────────────────────────────────
  const form = document.getElementById("query-form");
  const runBtn = document.getElementById("run-btn");
  const runSpinner = document.getElementById("run-spinner");
  if (form && runBtn) {
    form.addEventListener("submit", function () {
      saveQuery();
      runBtn.disabled = true;
      if (runSpinner) runSpinner.classList.remove("hidden");
    });
  }

  // ── Keyboard shortcuts ────────────────────────────────────────────────────
  document.addEventListener("keydown", function (e) {
    const ctrlOrMeta = e.ctrlKey || e.metaKey;

    // Ctrl+S → save bookmark
    if (ctrlOrMeta && e.key === "s") {
      e.preventDefault();
      openModal("bookmark-modal");
    }
    // Ctrl+K → focus history search
    if (ctrlOrMeta && e.key === "k") {
      e.preventDefault();
      const hs = document.getElementById("history-search");
      if (hs) hs.focus();
    }
    // Ctrl+T → open templates
    if (ctrlOrMeta && e.key === "t") {
      e.preventDefault();
      openTemplatesModal();
    }
    // Esc → close all modals
    if (e.key === "Escape") {
      closeAllModals();
    }
  });

  // ── Shortcuts help modal ──────────────────────────────────────────────────
  const helpBtn = document.getElementById("shortcuts-help-btn");
  if (helpBtn) {
    helpBtn.addEventListener("click", () => openModal("shortcuts-modal"));
  }
  const closeShortcuts = document.getElementById("close-shortcuts");
  if (closeShortcuts) {
    closeShortcuts.addEventListener("click", () => closeModal("shortcuts-modal"));
  }

  // ── History search ────────────────────────────────────────────────────────
  const historySearch = document.getElementById("history-search");
  if (historySearch) {
    historySearch.addEventListener("input", function () {
      const term = this.value.toLowerCase();
      document.querySelectorAll(".history-item").forEach(item => {
        const text = (item.dataset.query || "").toLowerCase();
        item.style.display = text.includes(term) ? "" : "none";
      });
    });
  }

  // ── Bookmark modal ────────────────────────────────────────────────────────
  const bookmarkBtn = document.getElementById("bookmark-query-btn");
  if (bookmarkBtn) {
    bookmarkBtn.addEventListener("click", () => openModal("bookmark-modal"));
  }
  const closeBookmark = document.getElementById("close-bookmark");
  if (closeBookmark) {
    closeBookmark.addEventListener("click", () => closeModal("bookmark-modal"));
  }
  const saveBookmarkBtn = document.getElementById("save-bookmark-btn");
  if (saveBookmarkBtn) {
    saveBookmarkBtn.addEventListener("click", saveBookmark);
  }

  // ── Open bookmarks list ───────────────────────────────────────────────────
  const openBookmarksBtn = document.getElementById("open-bookmarks-btn");
  if (openBookmarksBtn) {
    openBookmarksBtn.addEventListener("click", openBookmarksModal);
  }
  const closeBookmarks = document.getElementById("close-bookmarks");
  if (closeBookmarks) {
    closeBookmarks.addEventListener("click", () => closeModal("bookmarks-modal"));
  }

  // ── Templates modal ───────────────────────────────────────────────────────
  const openTemplatesBtn = document.getElementById("open-templates-btn");
  if (openTemplatesBtn) {
    openTemplatesBtn.addEventListener("click", openTemplatesModal);
  }
  const closeTemplates = document.getElementById("close-templates");
  if (closeTemplates) {
    closeTemplates.addEventListener("click", () => closeModal("templates-modal"));
  }
});

// ── Bookmarks ─────────────────────────────────────────────────────────────────

async function saveBookmark() {
  const name = (document.getElementById("bookmark-name").value || "").trim();
  const desc = (document.getElementById("bookmark-desc").value || "").trim();
  const tags = (document.getElementById("bookmark-tags").value || "").trim();
  const query = window.editor ? window.editor.getValue().trim() : "";
  const dbType = document.getElementById("db-select").value;

  if (!name) {
    showToast("Please enter a bookmark name.", "error");
    return;
  }
  if (!query) {
    showToast("Write a query first.", "error");
    return;
  }

  try {
    const resp = await fetch("/api/bookmarks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, query, description: desc, database_type: dbType, tags }),
    });
    const data = await resp.json();
    if (resp.ok && data.success) {
      closeModal("bookmark-modal");
      showToast("Bookmark saved!", "success");
      document.getElementById("bookmark-name").value = "";
      document.getElementById("bookmark-desc").value = "";
      document.getElementById("bookmark-tags").value = "";
    } else {
      showToast(data.error || "Failed to save bookmark.", "error");
    }
  } catch {
    showToast("Network error. Please try again.", "error");
  }
}

async function openBookmarksModal() {
  openModal("bookmarks-modal");
  const container = document.getElementById("bookmarks-list");
  if (!container) return;
  container.innerHTML = "<p class='loading-text'>Loading…</p>";

  try {
    const resp = await fetch("/api/bookmarks");
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || "Failed");

    const bms = data.bookmarks || [];
    if (!bms.length) {
      container.innerHTML = "<p class='loading-text'>No bookmarks yet. Save a query with Ctrl+S.</p>";
      return;
    }

  container.innerHTML = bms.map(b => `
      <div class="template-item" id="bm-${b.id}">
        <div class="template-header">
          <strong>${escHtml(b.name)}</strong>
          <span class="history-db history-db-${escHtml(b.database_type)}">${escHtml(b.database_type)}</span>
        </div>
        ${b.description ? `<p class="template-desc">${escHtml(b.description)}</p>` : ""}
        <pre class="template-query">${escHtml(b.query)}</pre>
        <div class="template-actions">
          <button class="btn btn-primary btn-sm bm-load-btn"
            data-query="${escHtml(b.query)}"
            data-db="${escHtml(b.database_type)}">
            &#9654; Load
          </button>
          <button class="btn btn-danger btn-sm bm-del-btn" data-id="${b.id}">
            &#x2715; Delete
          </button>
        </div>
      </div>
    `).join("");

  // Use event delegation to avoid inline onclick XSS vectors
  container.addEventListener("click", function bmClickHandler(e) {
    const loadBtn = e.target.closest(".bm-load-btn");
    const delBtn  = e.target.closest(".bm-del-btn");
    if (loadBtn) {
      loadBookmark(loadBtn.dataset.query, loadBtn.dataset.db);
    } else if (delBtn) {
      deleteBookmark(Number(delBtn.dataset.id));
    }
  });
  } catch (err) {
    container.innerHTML = `<p class="error">Failed to load bookmarks.</p>`;
  }
}

function loadBookmark(query, dbType) {
  loadQuery(query);
  const sel = document.getElementById("db-select");
  if (sel) sel.value = dbType;
  closeModal("bookmarks-modal");
  showToast("Bookmark loaded.", "info");
}

async function deleteBookmark(id) {
  if (!confirm("Delete this bookmark?")) return;
  try {
    const resp = await fetch(`/api/bookmarks/${id}`, { method: "DELETE" });
    const data = await resp.json();
    if (resp.ok && data.success) {
      const el = document.getElementById(`bm-${id}`);
      if (el) el.remove();
      showToast("Bookmark deleted.", "info");
    } else {
      showToast(data.error || "Failed to delete.", "error");
    }
  } catch {
    showToast("Network error.", "error");
  }
}

// ── Templates ─────────────────────────────────────────────────────────────────

async function openTemplatesModal() {
  openModal("templates-modal");
  const container = document.getElementById("templates-list");
  if (!container) return;
  container.innerHTML = "<p class='loading-text'>Loading…</p>";

  try {
    const resp = await fetch("/api/templates");
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || "Failed");

    const tpls = data.templates || [];
    if (!tpls.length) {
      container.innerHTML = "<p class='loading-text'>No templates available.</p>";
      return;
    }

    const categories = [...new Set(tpls.map(t => t.category))];
    container.innerHTML = categories.map(cat => `
      <div class="template-category">
        <h4 class="template-cat-title">${escHtml(cat)}</h4>
        ${tpls.filter(t => t.category === cat).map(t => `
          <div class="template-item">
            <div class="template-header">
              <strong>${escHtml(t.name)}</strong>
            </div>
            <p class="template-desc">${escHtml(t.description)}</p>
            <pre class="template-query">${escHtml(t.query)}</pre>
            <button class="btn btn-primary btn-sm tpl-use-btn"
              data-query="${escHtml(t.query)}">
              &#9654; Use template
            </button>
          </div>
        `).join("")}
      </div>
    `).join("");

    // Event delegation avoids inline onclick XSS
    container.addEventListener("click", function tplClickHandler(e) {
      const btn = e.target.closest(".tpl-use-btn");
      if (btn) useTemplate(btn.dataset.query);
    });
  } catch {
    container.innerHTML = "<p class='error'>Failed to load templates.</p>";
  }
}

function useTemplate(query) {
  loadQuery(query);
  closeModal("templates-modal");
  showToast("Template loaded.", "info");
}

// ── Export results ────────────────────────────────────────────────────────────

function exportResults(format) {
  const query = window.editor ? window.editor.getValue().trim() : "";
  const db = document.getElementById("db-select").value;
  if (!query) {
    showToast("No query to export.", "error");
    return;
  }
  document.getElementById("export-query").value = query;
  document.getElementById("export-db").value = db;
  document.getElementById("export-format").value = format;
  document.getElementById("export-form").submit();
}

// ── Utility ───────────────────────────────────────────────────────────────────

function escHtml(str) {
  if (typeof str !== "string") str = String(str);
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
