/**
 * PR Queue — caffenagent gap viewer
 *
 * Fetches gaps from /api/caffenagent/api/gap/{parent_run_id} and renders them.
 * Shows honest placeholder when no parent_run_id is provided.
 */

import { escapeHtml } from "./utils.js";

const PROXY_BASE = "/api/caffenagent";

// --- Utilities ---

function assertMountContract() {
  const mount = document.getElementById("miche-island-mount");
  if (!mount) {
    console.error("[miche-pr-queue] missing required mount #miche-island-mount");
    return;
  }
  mount.dataset.islandReady = "shell";
}

function getParentRunId() {
  const params = new URLSearchParams(window.location.search);
  return params.get("parent_run_id") || "";
}

// --- API layer ---

async function fetchGaps(parentRunId) {
  const r = await fetch(`${PROXY_BASE}/api/gap/${encodeURIComponent(parentRunId)}`);
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

function severityClass(severity) {
  const s = escapeHtml(String(severity || "unknown").toLowerCase());
  if (s === "critical" || s === "major" || s === "minor") return s;
  return "unknown";
}

function statusClass(status) {
  const s = escapeHtml(String(status || "unknown").toLowerCase());
  if (s === "open" || s === "closed" || s === "in_progress") return s;
  return "unknown";
}

function renderGap(gap) {
  const id = escapeHtml(gap.id || "—");
  const sev = severityClass(gap.severity);
  const sevLabel = escapeHtml(gap.severity || "unknown");
  const st = statusClass(gap.status);
  const stLabel = escapeHtml(gap.status || "unknown");
  const claim = escapeHtml(gap.claim || "No claim provided.");
  const counterclaim = escapeHtml(gap.counterclaim || "No counterclaim provided.");

  return `
    <li class="pr-queue-gap">
      <div class="pr-queue-gap__header">
        <span class="pr-queue-gap__id">${id}</span>
        <span class="pr-queue-gap__severity pr-queue-gap__severity--${sev}">${sevLabel}</span>
        <span class="pr-queue-gap__status pr-queue-gap__status--${st}">${stLabel}</span>
      </div>
      <p class="pr-queue-gap__claim">${claim}</p>
      <p class="pr-queue-gap__counterclaim">${counterclaim}</p>
    </li>
  `;
}

function renderPlaceholder() {
  const content = document.querySelector("[data-pr-queue-content]");
  if (!content) return;
  content.innerHTML = `
    <div class="pr-queue-empty">
      <p><strong>PR queue requires a parent_run_id.</strong></p>
      <p>Select a project to view its PR queue. Pass <code>?parent_run_id=…</code> in the URL.</p>
    </div>
  `;
}

function renderGaps(data) {
  const content = document.querySelector("[data-pr-queue-content]");
  if (!content) return;

  const gaps = data.gaps || [];
  if (gaps.length === 0) {
    content.innerHTML = '<p class="pr-queue-empty">No gaps found for this run.</p>';
    return;
  }

  content.innerHTML = `
    <ul class="pr-queue-list">
      ${gaps.map(renderGap).join("")}
    </ul>
  `;
}

function renderError(message) {
  const content = document.querySelector("[data-pr-queue-content]");
  if (!content) return;
  content.innerHTML = `<div class="pr-queue-error">${escapeHtml(message)}</div>`;
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

// --- Data loading ---

async function loadGaps(parentRunId) {
  const content = document.querySelector("[data-pr-queue-content]");
  if (content) content.innerHTML = '<p class="pr-queue-loading">Loading gaps…</p>';

  try {
    const data = await fetchGaps(parentRunId);
    renderGaps(data);
    updateConnectionStatus("ok", "Connected");
    updateLastUpdated();
  } catch (err) {
    renderError(`Failed to load gaps: ${err.message}`);
    updateConnectionStatus("error", `Error: ${err.message}`);
  }
}

// --- Island mount ---

async function initIsland() {
  try {
    const { mountFloatingIsland } = await import("./island.js");
    mountFloatingIsland();
  } catch (err) {
    console.error("[miche-pr-queue] island mount failed", err);
  }
}

// --- Init ---

function init() {
  assertMountContract();

  const parentRunId = getParentRunId();
  if (!parentRunId) {
    updateConnectionStatus("placeholder", "No parent_run_id");
    renderPlaceholder();
  } else {
    loadGaps(parentRunId);
  }

  initIsland();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
