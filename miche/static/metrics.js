/**
 * Agent Metrics — performance overview across all projects.
 */

import { escapeHtml, timeAgo } from "./utils.js";

const PROXY_BASE = "/api/caffenagent";

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

async function fetchProjects() {
  return fetchJson("/api/miche/studio/projects");
}

async function fetchAgents(projectId) {
  return fetchJson(`/api/miche/studio/projects/${encodeURIComponent(projectId)}/agents`);
}

// --- Island ---

function assertMountContract() {
  const mount = document.getElementById("miche-island-mount");
  if (!mount) {
    console.error("[miche-metrics] missing required mount #miche-island-mount");
    return;
  }
  mount.dataset.islandReady = "shell";
}

async function initIsland() {
  try {
    const { mountFloatingIsland } = await import("./island.js");
    mountFloatingIsland();
  } catch (err) {
    console.error("[miche-metrics] island mount failed", err);
  }
}

// --- Metrics computation ---

function computeMetrics(agents) {
  const total = agents.length;
  const byStatus = {};
  const byProfile = {};
  let completedDurations = [];

  for (const a of agents) {
    const status = (a.status || "unknown").toLowerCase();
    byStatus[status] = (byStatus[status] || 0) + 1;

    const profile = a.cli_profile || "unknown";
    byProfile[profile] = (byProfile[profile] || 0) + 1;

    if (status === "done" && a.created_at && a.updated_at) {
      const start = new Date(a.created_at).getTime();
      const end = new Date(a.updated_at).getTime();
      if (!Number.isNaN(start) && !Number.isNaN(end) && end > start) {
        completedDurations.push(end - start);
      }
    }
  }

  let avgCompletionMs = null;
  if (completedDurations.length > 0) {
    avgCompletionMs = completedDurations.reduce((s, d) => s + d, 0) / completedDurations.length;
  }

  return { total, byStatus, byProfile, avgCompletionMs, completedCount: completedDurations.length };
}

function formatDuration(ms) {
  if (ms == null) return "—";
  if (ms < 60_000) return `${Math.round(ms / 1000)}s`;
  if (ms < 3_600_000) return `${Math.round(ms / 60_000)}m`;
  const hours = Math.floor(ms / 3_600_000);
  const mins = Math.round((ms % 3_600_000) / 60_000);
  return `${hours}h ${mins}m`;
}

// --- Rendering ---

function statusBadge(status) {
  const s = escapeHtml(String(status || "unknown").toLowerCase());
  const cls = ["running", "done", "aborted"].includes(s) ? s : "idle";
  return `<span class="metrics-status metrics-status--${cls}">${s}</span>`;
}

function profileTag(profile) {
  if (!profile) return "";
  return `<span class="metrics-profile">${escapeHtml(profile)}</span>`;
}

function renderCards(metrics) {
  const statusEntries = Object.entries(metrics.byStatus).sort((a, b) => b[1] - a[1]);
  const statusBreakdown = statusEntries
    .map(([s, n]) => `${escapeHtml(s)}: ${n}`)
    .join(" &middot; ");

  const profileEntries = Object.entries(metrics.byProfile).sort((a, b) => b[1] - a[1]);
  const profileBreakdown = profileEntries
    .map(([p, n]) => `${escapeHtml(p)}: ${n}`)
    .join(" &middot; ");

  return `
    <div class="metrics-card">
      <p class="metrics-card__label">Total Agents</p>
      <p class="metrics-card__value">${metrics.total}</p>
    </div>
    <div class="metrics-card">
      <p class="metrics-card__label">By Status</p>
      <p class="metrics-card__value">${metrics.total > 0 ? statusEntries.length : 0}</p>
      <p class="metrics-card__sub">${statusBreakdown || "—"}</p>
    </div>
    <div class="metrics-card">
      <p class="metrics-card__label">By Profile</p>
      <p class="metrics-card__value">${profileEntries.length}</p>
      <p class="metrics-card__sub">${profileBreakdown || "—"}</p>
    </div>
    <div class="metrics-card">
      <p class="metrics-card__label">Avg Completion</p>
      <p class="metrics-card__value">${formatDuration(metrics.avgCompletionMs)}</p>
      <p class="metrics-card__sub">${metrics.completedCount} completed</p>
    </div>
  `;
}

function renderAgentRow(agent) {
  const aid = agent.agent_id || "—";
  const pid = agent.project_id || "—";
  const sub = agent.subproject_path || "/";
  const status = statusBadge(agent.status);
  const profile = profileTag(agent.cli_profile);
  const phase = escapeHtml(agent.skill_phase || "—");
  const created = agent.created_at ? timeAgo(agent.created_at) : "—";
  const updated = agent.updated_at ? timeAgo(agent.updated_at) : "—";
  const heartbeat = agent.heartbeat_at ? timeAgo(agent.heartbeat_at) : "—";
  const aborted = agent.aborted_reason ? escapeHtml(agent.aborted_reason) : "";

  return `<tr>
    <td class="metrics-agent-id" title="${escapeHtml(aid)}">${escapeHtml(aid)}</td>
    <td>${escapeHtml(pid)}</td>
    <td>${escapeHtml(sub)}</td>
    <td>${status}</td>
    <td>${profile}</td>
    <td>${phase}</td>
    <td title="${escapeHtml(agent.created_at || "")}">${created}</td>
    <td title="${escapeHtml(agent.updated_at || "")}">${updated}</td>
    <td title="${escapeHtml(agent.heartbeat_at || "")}">${heartbeat}</td>
    <td>${aborted}</td>
  </tr>`;
}

function renderTable(agents) {
  if (!agents || agents.length === 0) {
    return '<p class="metrics-empty">No agents found across any project.</p>';
  }

  const rows = agents.map(renderAgentRow).join("");
  return `<div class="metrics-table-wrap">
    <table class="metrics-table">
      <thead>
        <tr>
          <th>Agent ID</th>
          <th>Project</th>
          <th>Subproject</th>
          <th>Status</th>
          <th>Profile</th>
          <th>Phase</th>
          <th>Created</th>
          <th>Updated</th>
          <th>Heartbeat</th>
          <th>Aborted</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  </div>`;
}

// --- Status helpers ---

function updateConnectionStatus(state, message) {
  const el = document.querySelector("[data-connection-status]");
  if (!el) return;
  el.dataset.state = state;
  el.textContent = message;
}

function updateLastUpdated() {
  const el = document.querySelector("[data-last-updated]");
  if (!el) return;
  el.textContent = `Updated ${new Date().toLocaleTimeString()}`;
}

// --- Data loading ---

async function loadAll() {
  const cardsEl = document.querySelector("[data-metrics-cards]");
  const tableEl = document.querySelector("[data-metrics-table]");

  try {
    const projData = await fetchProjects();
    if (!projData.ok) {
      updateConnectionStatus("error", projData.message || "caffenagent error");
      return;
    }

    const projects = projData.projects || [];
    const allAgents = [];

    for (const p of projects) {
      try {
        const agentData = await fetchAgents(p.project_id);
        if (agentData.ok && agentData.agents) {
          for (const a of agentData.agents) {
            allAgents.push(a);
          }
        }
      } catch {
        // skip projects that fail individually
      }
    }

    allAgents.sort((a, b) => {
      const ta = new Date(a.created_at || 0).getTime();
      const tb = new Date(b.created_at || 0).getTime();
      return tb - ta;
    });

    const metrics = computeMetrics(allAgents);

    if (cardsEl) cardsEl.innerHTML = renderCards(metrics);
    if (tableEl) tableEl.innerHTML = renderTable(allAgents);

    updateConnectionStatus("ok", "Connected");
    updateLastUpdated();
  } catch (err) {
    updateConnectionStatus("error", `Error: ${err.message}`);
    if (cardsEl) cardsEl.innerHTML = `<p class="metrics-empty">Failed to load: ${escapeHtml(err.message)}</p>`;
  }
}

// --- Init ---

function init() {
  assertMountContract();
  loadAll();
  initIsland();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
