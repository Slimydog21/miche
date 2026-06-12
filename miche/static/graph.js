/**
 * Execution graph viewer — renders caffenagent execution-graph endpoint.
 * Imports shared utilities from utils.js.
 */

import { escapeHtml } from "./utils.js";

const PROXY_BASE = "/api/caffenagent";
const GRAPH_PATH = "/api/miche/execution-graph?device=mac";

// --- Utilities ---

function assertMountContract() {
  const mount = document.getElementById("miche-island-mount");
  if (!mount) {
    console.error("[miche-graph] missing required mount #miche-island-mount");
    return;
  }
  mount.dataset.islandReady = "shell";
}

// --- API layer ---

async function fetchGraph() {
  const r = await fetch(`${PROXY_BASE}${GRAPH_PATH}`);
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

function statusColorClass(status) {
  const s = escapeHtml(String(status || "").toLowerCase());
  return `graph-node__status graph-node__status--${s}`;
}

function renderWarnings(warnings) {
  const el = document.querySelector("[data-warnings]");
  if (!el) return;
  if (!warnings || warnings.length === 0) {
    el.innerHTML = "";
    return;
  }
  el.innerHTML = warnings
    .map(
      (w) =>
        `<div class="graph-callout graph-callout--warning">${escapeHtml(String(w))}</div>`
    )
    .join("");
}

function renderOverlaps(overlaps) {
  const el = document.querySelector("[data-overlaps]");
  if (!el) return;
  if (!overlaps || overlaps.length === 0) {
    el.innerHTML = "";
    return;
  }
  el.innerHTML = overlaps
    .map((o) => {
      const label = typeof o === "string" ? o : JSON.stringify(o);
      return `<div class="graph-callout graph-callout--overlap">Overlap: ${escapeHtml(label)}</div>`;
    })
    .join("");
}

function renderTimeline(nodes) {
  const el = document.querySelector("[data-timeline]");
  if (!el) return;
  if (!nodes || nodes.length === 0) {
    el.innerHTML = '<p class="graph-empty">No execution nodes found.</p>';
    return;
  }
  el.innerHTML = nodes
    .map((node, i) => {
      const sessionId = escapeHtml(String(node.session_id || "—"));
      const phase = escapeHtml(String(node.phase || "—"));
      const title = escapeHtml(String(node.title || "—"));
      const status = String(node.status || "unknown").toLowerCase();
      const filesCount = Array.isArray(node.files_touched)
        ? node.files_touched.length
        : Number(node.files_touched) || 0;
      return `
      <div class="graph-node" data-status="${escapeHtml(status)}">
        <div class="graph-node__marker ${statusColorClass(status)}"></div>
        <div class="graph-node__body">
          <div class="graph-node__row">
            <span class="graph-node__phase">${phase}</span>
            <span class="${statusColorClass(status)}">${escapeHtml(status)}</span>
          </div>
          <p class="graph-node__title">${title}</p>
          <p class="graph-node__meta">
            <code>${sessionId}</code>
            <span class="graph-node__files">${filesCount} file${filesCount !== 1 ? "s" : ""}</span>
          </p>
        </div>
      </div>`;
    })
    .join("");
}

function updateConnectionStatus(state, message) {
  const el = document.querySelector("[data-connection-status]");
  if (!el) return;
  el.dataset.state = state;
  el.textContent = message;
}

// --- Refresh ---

let loading = false;

async function refresh() {
  if (loading) return;
  loading = true;
  updateConnectionStatus("loading", "Fetching graph…");
  try {
    const data = await fetchGraph();
    const graph = data.graph || {};
    const nodes = graph.nodes || [];
    renderTimeline(nodes);
    renderOverlaps(data.overlaps);
    renderWarnings(data.intent_warnings);
    updateConnectionStatus("ok", "Connected");
  } catch (err) {
    console.error("[miche-graph] fetch error", err);
    updateConnectionStatus("error", `Error: ${err.message}`);
    const el = document.querySelector("[data-timeline]");
    if (el) {
      el.innerHTML = `<p class="graph-empty graph-empty--error">Failed to load graph. ${escapeHtml(err.message)}</p>`;
    }
  } finally {
    loading = false;
  }
}

// --- Event delegation ---

function initActionHandlers() {
  document.addEventListener("click", (e) => {
    const actionEl = e.target.closest("[data-action]");
    if (!actionEl) return;
    const action = actionEl.dataset.action;
    if (action === "refresh") {
      e.preventDefault();
      refresh();
    }
  });
}

// --- Island mount ---

async function initIsland() {
  try {
    const { mountFloatingIsland } = await import("./island.js");
    mountFloatingIsland();
  } catch (err) {
    console.error("[miche-graph] island mount failed", err);
  }
}

// --- Init ---

function init() {
  assertMountContract();
  initActionHandlers();
  refresh();
  initIsland();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
