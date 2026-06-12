/**
 * Gap analysis dashboard — fetches and renders gap reports from caffenagent.
 */
import { escapeHtml } from "./utils.js";

const PROXY_BASE = "/api/caffenagent";

function severityColor(sev) {
  const s = String(sev || "").toLowerCase();
  if (s === "blocker") return "danger";
  if (s === "major") return "warning";
  if (s === "minor") return "info";
  return "muted";
}

function renderGap(gap) {
  const id = escapeHtml(gap.id || "?");
  const sev = escapeHtml(gap.severity || "unknown");
  const claim = escapeHtml(gap.claim || "");
  const counter = escapeHtml(gap.counterclaim || "");
  const status = escapeHtml(gap.status || "open");
  const color = severityColor(gap.severity);

  return `
    <div class="orchestrate-card" data-gap-id="${id}">
      <div class="orchestrate-card__header">
        <span class="tag tag--${color}">${id}</span>
        <span class="orchestrate-card__counts">${status}</span>
      </div>
      <div class="orchestrate-card__body">
        <p><strong>Claim:</strong> ${claim}</p>
        ${counter ? `<p><strong>Counterclaim:</strong> ${counter}</p>` : ""}
      </div>
    </div>
  `;
}

async function loadGaps() {
  const input = document.querySelector("[data-parent-run-id]");
  const runId = input?.value?.trim();
  if (!runId) return;

  const grid = document.querySelector("[data-gaps-grid]");
  grid.innerHTML = '<p class="orchestrate-empty">Loading…</p>';

  try {
    const r = await fetch(`/api/caffenagent/api/gap/${encodeURIComponent(runId)}`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    const gaps = data.gaps || [];
    if (!gaps.length) {
      grid.innerHTML = '<p class="orchestrate-empty">No gaps found for this run.</p>';
      return;
    }
    grid.innerHTML = gaps.map(renderGap).join("");
  } catch (err) {
    grid.innerHTML = `<p class="orchestrate-empty">Error: ${escapeHtml(err.message)}</p>`;
  }
}

function init() {
  document.querySelector("[data-action='load-gaps']")?.addEventListener("click", loadGaps);
  document.querySelector("[data-parent-run-id]")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") loadGaps();
  });
  try {
    const { mountFloatingIsland } = import("./island.js");
    mountFloatingIsland();
  } catch {}
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
