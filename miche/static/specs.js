/**
 * Specs browser — renders htmlspec specs list via caffenagent proxy.
 * Imports shared utilities from utils.js.
 */

import { escapeHtml } from "./utils.js";

const PROXY_BASE = "/api/caffenagent";
const SPECS_PATH = "/api/miche/specs";

// --- Utilities ---

function assertMountContract() {
  const mount = document.getElementById("miche-island-mount");
  if (!mount) {
    console.error("[miche-specs] missing required mount #miche-island-mount");
    return;
  }
  mount.dataset.islandReady = "shell";
}

// --- API layer ---

async function fetchSpecs() {
  const r = await fetch(`${PROXY_BASE}${SPECS_PATH}`);
  if (r.status === 404) {
    return null;
  }
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

function statusClass(status) {
  const s = escapeHtml(String(status || "").toLowerCase());
  return `spec-card__status spec-card__status--${s}`;
}

function renderPlaceholder() {
  const el = document.querySelector("[data-specs]");
  if (!el) return;
  el.innerHTML = `
    <div class="specs-placeholder">
      <span class="specs-placeholder__icon" aria-hidden="true">📄</span>
      <p class="specs-placeholder__title">No specs endpoint available</p>
      <p class="specs-placeholder__body">Use the <code>htmlspec</code> skill to generate specs, then they will appear here.</p>
    </div>`;
}

function renderSpecs(specs) {
  const el = document.querySelector("[data-specs]");
  if (!el) return;
  if (!specs || specs.length === 0) {
    el.innerHTML = '<p class="specs-empty">No specs found.</p>';
    return;
  }
  el.innerHTML = specs
    .map((spec) => {
      const title = escapeHtml(String(spec.title || spec.name || "Untitled spec"));
      const status = String(spec.status || "draft").toLowerCase();
      const sprintCount = Array.isArray(spec.sprints)
        ? spec.sprints.length
        : Number(spec.sprint_count) || 0;
      const specId = escapeHtml(String(spec.id || spec.slug || "—"));
      return `
      <div class="spec-card" data-status="${escapeHtml(status)}">
        <div class="spec-card__row">
          <p class="spec-card__title">${title}</p>
          <span class="${statusClass(status)}">${escapeHtml(status)}</span>
        </div>
        <p class="spec-card__meta">
          <code>${specId}</code>
          <span>${sprintCount} sprint${sprintCount !== 1 ? "s" : ""}</span>
        </p>
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
  updateConnectionStatus("loading", "Fetching specs…");
  try {
    const data = await fetchSpecs();
    if (data === null) {
      renderPlaceholder();
      updateConnectionStatus("ok", "No specs endpoint");
    } else {
      const specs = Array.isArray(data) ? data : data.specs || [];
      renderSpecs(specs);
      updateConnectionStatus("ok", "Connected");
    }
  } catch (err) {
    console.error("[miche-specs] fetch error", err);
    updateConnectionStatus("error", `Error: ${err.message}`);
    const el = document.querySelector("[data-specs]");
    if (el) {
      el.innerHTML = `<p class="specs-empty specs-empty--error">Failed to load specs. ${escapeHtml(err.message)}</p>`;
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
    console.error("[miche-specs] island mount failed", err);
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
