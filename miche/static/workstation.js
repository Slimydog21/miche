/**
 * Workstation pane viewer — browse caffenagent PTY pane bindings and live output.
 */

import { escapeHtml } from "./utils.js";

const PROXY_BASE = "/api/caffenagent";
const BINDINGS_PATH = "/api/workstation/bindings";
const REFRESH_INTERVAL = 2000;

// --- State ---

let bindings = [];
let selectedPaneId = null;
let outputTimer = null;

// --- API ---

async function fetchJson(path) {
  const r = await fetch(`${PROXY_BASE}${path}`);
  const text = await r.text();
  if (!r.ok) throw new Error(`HTTP ${r.status}: ${text.slice(0, 200)}`);
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`Non-JSON response from ${path}: ${text.slice(0, 100)}`);
  }
}

async function fetchBindings() {
  return fetchJson(BINDINGS_PATH);
}

async function fetchPaneOutput(paneId) {
  return fetchJson(`/api/workstation/panes/${encodeURIComponent(paneId)}/output`);
}

// --- Island ---

function assertMountContract() {
  const mount = document.getElementById("miche-island-mount");
  if (!mount) {
    console.error("[miche-workstation] missing required mount #miche-island-mount");
    return;
  }
  mount.dataset.islandReady = "shell";
}

async function initIsland() {
  try {
    const { mountFloatingIsland } = await import("./island.js");
    mountFloatingIsland();
  } catch (err) {
    console.error("[miche-workstation] island mount failed", err);
  }
}

// --- Connection status ---

function updateConnectionStatus(state, message) {
  const el = document.querySelector("[data-connection-status]");
  if (!el) return;
  el.dataset.state = state;
  el.textContent = message;
}

// --- Rendering ---

function ptyBadge(state) {
  const s = escapeHtml(String(state || "unknown").toLowerCase());
  return `<span class="ws-pty ws-pty--${s}">${s}</span>`;
}

function renderPaneItem(binding) {
  const paneId = binding.pane_id || "—";
  const sessionId = binding.session_id || "—";
  const profile = binding.cli_profile || "—";
  const pty = ptyBadge(binding.pty_state);
  const isActive = paneId === selectedPaneId;
  return `<button class="ws-pane-item${isActive ? " ws-pane-item--active" : ""}" data-pane-id="${escapeHtml(paneId)}" type="button">
    <span class="ws-pane-item__id">${escapeHtml(paneId)}</span>
    <span class="ws-pane-item__session">${escapeHtml(sessionId)}</span>
    <span class="ws-pane-item__profile">${escapeHtml(profile)}</span>
    ${pty}
  </button>`;
}

function renderPaneList(list) {
  const el = document.querySelector("[data-pane-list]");
  if (!el) return;
  if (!list || list.length === 0) {
    el.innerHTML = '<p class="ws-empty">No pane bindings found.</p>';
    return;
  }
  el.innerHTML = list.map(renderPaneItem).join("");
}

function renderOutput(text) {
  const el = document.querySelector("[data-output-area]");
  if (!el) return;
  if (text == null) {
    el.innerHTML = '<p class="ws-empty">No output available.</p>';
    return;
  }
  el.innerHTML = `<pre class="ws-output-pre">${escapeHtml(text)}</pre>`;
}

function renderOutputError(message) {
  const el = document.querySelector("[data-output-area]");
  if (!el) return;
  el.innerHTML = `<p class="ws-empty ws-empty--error">Failed to load output: ${escapeHtml(message)}</p>`;
}

// --- Data loading ---

async function loadBindings() {
  try {
    const data = await fetchBindings();
    bindings = Array.isArray(data) ? data : data.bindings || data.panes || [];
    renderPaneList(bindings);
    updateConnectionStatus("ok", "Connected");
  } catch (err) {
    console.error("[miche-workstation] bindings error", err);
    updateConnectionStatus("error", `Error: ${err.message}`);
    const el = document.querySelector("[data-pane-list]");
    if (el) el.innerHTML = `<p class="ws-empty ws-empty--error">Failed to load panes: ${escapeHtml(err.message)}</p>`;
  }
}

async function loadPaneOutput(paneId) {
  try {
    const data = await fetchPaneOutput(paneId);
    const text = typeof data === "string" ? data : data.output ?? data.text ?? JSON.stringify(data, null, 2);
    renderOutput(text);
  } catch (err) {
    console.error("[miche-workstation] output error", err);
    renderOutputError(err.message);
  }
}

// --- Auto-refresh ---

function startOutputRefresh(paneId) {
  stopOutputRefresh();
  loadPaneOutput(paneId);
  outputTimer = setInterval(() => loadPaneOutput(paneId), REFRESH_INTERVAL);
}

function stopOutputRefresh() {
  if (outputTimer != null) {
    clearInterval(outputTimer);
    outputTimer = null;
  }
}

// --- Event handlers ---

function initPaneClick() {
  document.addEventListener("click", (e) => {
    const item = e.target.closest("[data-pane-id]");
    if (!item) return;
    const paneId = item.dataset.paneId;
    if (!paneId || paneId === selectedPaneId) return;

    selectedPaneId = paneId;
    renderPaneList(bindings);
    startOutputRefresh(paneId);
  });
}

function initRefreshButton() {
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-action='refresh-bindings']");
    if (!btn) return;
    e.preventDefault();
    loadBindings();
  });
}

// --- Init ---

function init() {
  assertMountContract();
  initPaneClick();
  initRefreshButton();
  loadBindings();
  initIsland();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
