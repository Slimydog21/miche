/**
 * Memory query — search caffenagent memory via proxy.
 */

import { escapeHtml } from "./utils.js";

const PROXY_BASE = "/api/caffenagent";
const MEMORY_QUERY_PATH = "/api/memory/query";

const PRESETS = {
  what_did_i_want: "what did I want",
};

// --- API ---

async function searchMemory(query) {
  const params = new URLSearchParams({ q: query, limit: "20" });
  const url = `${PROXY_BASE}${MEMORY_QUERY_PATH}?${params}`;
  const r = await fetch(url);
  const text = await r.text();
  if (!r.ok) throw new Error(`HTTP ${r.status}: ${text.slice(0, 200)}`);
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`Non-JSON response: ${text.slice(0, 100)}`);
  }
}

// --- Island ---

function assertMountContract() {
  const mount = document.getElementById("miche-island-mount");
  if (!mount) {
    console.error("[miche-memory] missing required mount #miche-island-mount");
    return;
  }
  mount.dataset.islandReady = "shell";
}

async function initIsland() {
  try {
    const { mountFloatingIsland } = await import("./island.js");
    mountFloatingIsland();
  } catch (err) {
    console.error("[miche-memory] island mount failed", err);
  }
}

// --- Rendering ---

function renderResultCard(entry) {
  const path = escapeHtml(entry.path || "—");
  const timestamp = escapeHtml(entry.timestamp || "");
  const project = escapeHtml(entry.project || "");
  const preview = escapeHtml(entry.preview || entry.body || "");
  return `
    <div class="memory-card">
      <div class="memory-card__header">
        <code class="memory-card__path">${path}</code>
        <span class="memory-card__timestamp">${timestamp}</span>
      </div>
      ${project ? `<span class="memory-card__project">${project}</span>` : ""}
      <p class="memory-card__preview">${preview}</p>
    </div>`;
}

function renderResults(results) {
  const el = document.querySelector("[data-results]");
  if (!el) return;
  if (!results || results.length === 0) {
    el.innerHTML = '<p class="memory-empty">No results found.</p>';
    return;
  }
  el.innerHTML = results.map(renderResultCard).join("");
}

function updateResultCount(count) {
  const el = document.querySelector("[data-result-count]");
  if (!el) return;
  el.textContent = count !== null ? `${count} result${count !== 1 ? "s" : ""}` : "";
}

function updateConnectionStatus(state, message) {
  const el = document.querySelector("[data-connection-status]");
  if (!el) return;
  el.dataset.state = state;
  el.textContent = message;
}

// --- Search ---

let searching = false;

async function doSearch(query) {
  if (searching || !query.trim()) return;
  searching = true;
  updateConnectionStatus("loading", "Searching…");
  updateResultCount(null);

  const el = document.querySelector("[data-results]");
  if (el) el.innerHTML = '<p class="memory-loading">Searching memory…</p>';

  try {
    const data = await searchMemory(query.trim());
    const results = data.results || data.memories || (Array.isArray(data) ? data : []);
    renderResults(results);
    updateResultCount(results.length);
    updateConnectionStatus("ok", "Done");
  } catch (err) {
    console.error("[miche-memory] search error", err);
    updateConnectionStatus("error", `Error: ${err.message}`);
    if (el) {
      el.innerHTML = `<p class="memory-empty memory-empty--error">Search failed: ${escapeHtml(err.message)}</p>`;
    }
    updateResultCount(null);
  } finally {
    searching = false;
  }
}

// --- Events ---

function initForm() {
  const form = document.querySelector("[data-search-form]");
  const input = document.querySelector("[data-search-input]");
  if (!form || !input) return;

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    doSearch(input.value);
  });
}

function initPresets() {
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-preset]");
    if (!btn) return;
    const key = btn.dataset.preset;
    const query = PRESETS[key];
    if (!query) return;
    const input = document.querySelector("[data-search-input]");
    if (input) input.value = query;
    doSearch(query);
  });
}

// --- Init ---

function init() {
  assertMountContract();
  initForm();
  initPresets();
  initIsland();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
