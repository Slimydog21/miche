/**
 * Connectors viewer — fetches and renders connector blocks from caffenagent.
 */
import { escapeHtml } from "./utils.js";

const PROXY_BASE = "/api/caffenagent";

// --- State ---

let currentProject = "";

// --- API layer ---

async function fetchBlocks(project) {
  const url = `${PROXY_BASE}/api/connectors?project=${encodeURIComponent(project)}`;
  const r = await fetch(url);
  const text = await r.text();
  if (!r.ok) {
    throw new Error(`HTTP ${r.status}: ${text.slice(0, 200)}`);
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`Non-JSON response: ${text.slice(0, 100)}`);
  }
}

async function refreshBlocks(project) {
  const url = `${PROXY_BASE}/api/connectors/refresh?project=${encodeURIComponent(project)}`;
  const r = await fetch(url, { method: "POST" });
  const text = await r.text();
  if (!r.ok) {
    throw new Error(`HTTP ${r.status}: ${text.slice(0, 200)}`);
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`Non-JSON response: ${text.slice(0, 100)}`);
  }
}

// --- Rendering ---

function truncate(text, max) {
  const s = String(text || "");
  return s.length > max ? s.slice(0, max) + "…" : s;
}

function renderBlock(block) {
  const id = escapeHtml(block.id || "—");
  const kind = escapeHtml(block.kind || "unknown");
  const preview = escapeHtml(truncate(block.text, 200));
  const provenance = escapeHtml(block.provenance || "—");

  return `
    <div class="connectors-card" data-block-id="${id}">
      <div class="connectors-card__header">
        <span class="connectors-card__id">${id}</span>
        <span class="connectors-card__kind">${kind}</span>
      </div>
      <div class="connectors-card__body">
        <p class="connectors-card__text">${preview || "(empty)"}</p>
      </div>
      <div class="connectors-card__footer">
        <span class="connectors-card__label">Provenance:</span>
        <span class="connectors-card__provenance">${provenance}</span>
      </div>
    </div>
  `;
}

function renderBlocks(data) {
  const grid = document.querySelector("[data-blocks-grid]");
  if (!grid) return;

  const blocks = data.blocks || data.items || data || [];
  if (!Array.isArray(blocks) || blocks.length === 0) {
    grid.innerHTML = '<p class="connectors-empty">No connector blocks found for this project.</p>';
    return;
  }

  grid.innerHTML = `<div class="connectors-grid">${blocks.map(renderBlock).join("")}</div>`;
}

function renderError(message) {
  const grid = document.querySelector("[data-blocks-grid]");
  if (!grid) return;
  grid.innerHTML = `<p class="connectors-empty connectors-empty--error">Error: ${escapeHtml(message)}</p>`;
}

function setLoading(isLoading) {
  const loadBtn = document.querySelector('[data-action="load-blocks"]');
  const refreshBtn = document.querySelector('[data-action="refresh-blocks"]');
  if (loadBtn) loadBtn.disabled = isLoading;
  if (refreshBtn) refreshBtn.disabled = isLoading || !currentProject;
}

function updateConnectionStatus(state, message) {
  const el = document.querySelector("[data-connection-status]");
  if (!el) return;
  el.dataset.state = state;
  el.textContent = message;
}

function updateLastUpdated() {
  const el = document.querySelector("[data-last-updated]");
  if (!el) return;
  const now = new Date();
  el.textContent = `Updated ${now.toLocaleTimeString()}`;
}

// --- Actions ---

async function loadBlocks() {
  const input = document.querySelector("[data-project-input]");
  const project = input?.value?.trim();
  if (!project) {
    updateConnectionStatus("error", "Enter a project name");
    return;
  }

  currentProject = project;
  const grid = document.querySelector("[data-blocks-grid]");
  if (grid) grid.innerHTML = '<p class="connectors-empty">Loading…</p>';
  setLoading(true);

  try {
    const data = await fetchBlocks(project);
    renderBlocks(data);
    updateConnectionStatus("ok", "Connected");
    updateLastUpdated();
  } catch (err) {
    renderError(err.message);
    updateConnectionStatus("error", `Error: ${err.message}`);
  } finally {
    setLoading(false);
  }
}

async function handleRefresh() {
  if (!currentProject) return;
  setLoading(true);

  try {
    await refreshBlocks(currentProject);
    const data = await fetchBlocks(currentProject);
    renderBlocks(data);
    updateConnectionStatus("ok", "Refreshed");
    updateLastUpdated();
  } catch (err) {
    renderError(err.message);
    updateConnectionStatus("error", `Refresh error: ${err.message}`);
  } finally {
    setLoading(false);
  }
}

// --- Island mount ---

async function initIsland() {
  try {
    const { mountFloatingIsland } = await import("./island.js");
    mountFloatingIsland();
  } catch (err) {
    console.error("[miche-connectors] island mount failed", err);
  }
}

// --- Init ---

function init() {
  const loadBtn = document.querySelector('[data-action="load-blocks"]');
  const refreshBtn = document.querySelector('[data-action="refresh-blocks"]');
  const input = document.querySelector("[data-project-input]");

  loadBtn?.addEventListener("click", loadBlocks);
  refreshBtn?.addEventListener("click", handleRefresh);
  input?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") loadBlocks();
  });

  initIsland();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
