/**
 * Session Studio — browse caffenagent sessions per project.
 */

import { escapeHtml } from "./utils.js";

const PROXY_BASE = "/api/caffenagent";

// --- State ---

let currentProjectId = "";
let currentSort = "flat";
let sessions = [];

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

async function fetchSessions(projectId, sort) {
  return fetchJson(
    `/api/miche/studio/projects/${encodeURIComponent(projectId)}/sessions?sort=${encodeURIComponent(sort)}`
  );
}

// --- Island ---

function assertMountContract() {
  const mount = document.getElementById("miche-island-mount");
  if (!mount) {
    console.error("[miche-studio] missing required mount #miche-island-mount");
    return;
  }
  mount.dataset.islandReady = "shell";
}

async function initIsland() {
  try {
    const { mountFloatingIsland } = await import("./island.js");
    mountFloatingIsland();
  } catch (err) {
    console.error("[miche-studio] island mount failed", err);
  }
}

// --- Rendering ---

function statusBadge(status) {
  const s = escapeHtml(String(status || "unknown").toLowerCase());
  return `<span class="studio-status studio-status--${s}">${s}</span>`;
}

function sourceTag(source) {
  if (!source) return "";
  return `<span class="studio-source">${escapeHtml(source)}</span>`;
}

function renderSessionRow(session) {
  const sid = session.session_id || "—";
  const title = escapeHtml(session.title || "Untitled");
  const status = statusBadge(session.status);
  const count = session.message_count ?? "—";
  const src = sourceTag(session.source);
  return `<tr>
    <td class="studio-session-id" title="${escapeHtml(sid)}">${escapeHtml(sid)}</td>
    <td>${title}</td>
    <td>${status}</td>
    <td style="text-align:right">${count}</td>
    <td>${src}</td>
  </tr>`;
}

function renderTable(sessionList) {
  if (!sessionList || sessionList.length === 0) {
    return '<p class="studio-empty">No sessions found for this project.</p>';
  }

  const rows = sessionList.map(renderSessionRow).join("");
  return `<div class="studio-table-wrap">
    <table class="studio-table">
      <thead>
        <tr>
          <th>Session ID</th>
          <th>Title</th>
          <th>Status</th>
          <th style="text-align:right">Messages</th>
          <th>Source</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  </div>`;
}

function renderSubprojectGroups(groups) {
  if (!groups || groups.length === 0) {
    return '<p class="studio-empty">No sessions found for this project.</p>';
  }

  return groups
    .map((g) => {
      const label = escapeHtml(g.subproject_path || "/");
      const table = renderTable(g.sessions || []);
      return `<div class="studio-group"><h3 class="studio-group-header">${label}</h3>${table}</div>`;
    })
    .join("");
}

function renderThemeGroups(groups) {
  if (!groups || groups.length === 0) {
    return '<p class="studio-empty">No sessions found for this project.</p>';
  }

  return groups
    .map((g) => {
      const label = escapeHtml(g.theme || "Uncategorized");
      const table = renderTable(g.sessions || []);
      return `<div class="studio-group"><h3 class="studio-group-header">${label}</h3>${table}</div>`;
    })
    .join("");
}

function renderContent(data) {
  const el = document.querySelector("[data-session-content]");
  if (!el) return;

  if (currentSort === "subproject") {
    el.innerHTML = renderSubprojectGroups(data.groups || []);
  } else if (currentSort === "theme") {
    el.innerHTML = renderThemeGroups(data.groups || []);
  } else {
    el.innerHTML = renderTable(data.sessions || []);
  }
}

function updateCounts(data) {
  const el = document.querySelector("[data-session-counts]");
  if (!el) return;

  let active = 0;
  let total = 0;
  if (currentSort === "subproject" || currentSort === "theme") {
    for (const g of data.groups || []) {
      for (const s of g.sessions || []) {
        total++;
        if (s.status === "active") active++;
      }
    }
  } else {
    total = (data.sessions || []).length;
    active = (data.sessions || []).filter((s) => s.status === "active").length;
  }
  el.textContent = `${active} active / ${total} sessions`;
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
  el.textContent = `Updated ${new Date().toLocaleTimeString()}`;
}

// --- Project selector ---

async function loadProjects() {
  try {
    const data = await fetchProjects();
    if (!data.ok) {
      updateConnectionStatus("error", data.message || "caffenagent error");
      return;
    }

    const select = document.querySelector("[data-project-select]");
    if (!select) return;

    const projects = data.projects || [];
    for (const p of projects) {
      const opt = document.createElement("option");
      opt.value = p.project_id;
      opt.textContent = `${p.label || p.project_id} (${p.active_session_count || 0}/${p.session_count || 0})`;
      select.appendChild(opt);
    }

    updateConnectionStatus("ok", "Connected");
  } catch (err) {
    updateConnectionStatus("error", `Disconnected: ${err.message}`);
  }
}

async function loadSessions() {
  if (!currentProjectId) {
    const el = document.querySelector("[data-session-content]");
    if (el) el.innerHTML = '<p class="studio-empty">Select a project to view sessions.</p>';
    const counts = document.querySelector("[data-session-counts]");
    if (counts) counts.textContent = "";
    return;
  }

  const el = document.querySelector("[data-session-content]");
  if (el) el.innerHTML = '<p class="studio-loading">Loading sessions…</p>';

  try {
    const data = await fetchSessions(currentProjectId, currentSort);
    if (!data.ok) {
      updateConnectionStatus("error", data.message || "caffenagent error");
      return;
    }

    sessions = data.sessions || data.groups || [];
    renderContent(data);
    updateCounts(data);
    updateConnectionStatus("ok", "Connected");
    updateLastUpdated();
  } catch (err) {
    updateConnectionStatus("error", `Error: ${err.message}`);
    if (el) el.innerHTML = `<p class="studio-empty">Failed to load sessions: ${escapeHtml(err.message)}</p>`;
  }
}

// --- Sort toggle ---

function initSortHandlers() {
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-sort]");
    if (!btn) return;

    const sort = btn.dataset.sort;
    if (sort === currentSort) return;

    currentSort = sort;
    document.querySelectorAll("[data-sort]").forEach((b) => {
      b.classList.toggle("studio-sort-btn--active", b.dataset.sort === sort);
    });

    loadSessions();
  });
}

// --- Project change ---

function initProjectSelect() {
  const select = document.querySelector("[data-project-select]");
  if (!select) return;

  select.addEventListener("change", () => {
    currentProjectId = select.value;
    loadSessions();
  });
}

// --- Init ---

function init() {
  assertMountContract();
  initProjectSelect();
  initSortHandlers();
  loadProjects();
  initIsland();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
