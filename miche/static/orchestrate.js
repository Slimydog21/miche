/**
 * Orchestration dashboard — MPLAT-ORCH-SPR-02
 *
 * Polls caffenagent via proxy, renders project/agent grid, delegates agent actions.
 * Imports shared utilities from utils.js.
 */

import { escapeHtml, timeAgo } from "./utils.js";

const PROXY_BASE = "/api/caffenagent";
const POLL_INTERVAL_MS = 5000;
const POLL_BACKOFF_MS = 15000;
const MAX_CONSECUTIVE_ERRORS = 3;
const STALE_HEARTBEAT_MS = 30 * 60 * 1000; // 30 minutes

// --- Utilities ---

function assertMountContract() {
  const mount = document.getElementById("miche-island-mount");
  if (!mount) {
    console.error("[miche-orchestrate] missing required mount #miche-island-mount");
    return;
  }
  mount.dataset.islandReady = "shell";
}

// --- Mascot state management ---

const MASCOT_COSTUMES = {
  idle:      { src: "/static/mascot/costumes/miche-base.png",      label: "Idle" },
  working:   { src: "/static/mascot/costumes/miche-mug.png",       label: "Working" },
  blocked:   { src: "/static/mascot/costumes/miche-sword.png",     label: "Blocked" },
  // Agent profile costumes (when single agent is dominant)
  claude:    { src: "/static/mascot/costumes/miche-pencil.png",    label: "Claude Code" },
  grok:      { src: "/static/mascot/costumes/miche-rocket.png",    label: "Grok Build" },
  mimo:      { src: "/static/mascot/costumes/miche-telescope.png", label: "MiMo Code" },
  codex:     { src: "/static/mascot/costumes/miche-plane.png",     label: "Codex" },
};

function updateMascotState(projects) {
  const mascot = document.querySelector("[data-mascot-state]");
  if (!mascot) return;

  const img = mascot.querySelector("[data-mascot-img]");
  const label = mascot.querySelector("[data-mascot-label]");
  if (!img || !label) return;

  // Count agents by status and profile
  let runningCount = 0;
  let blockedCount = 0;
  let profileCounts = {};
  let dominantProfile = null;

  for (const project of projects || []) {
    for (const agent of project._agents || []) {
      if (agent.status === "running") {
        runningCount++;
        const p = agent.cli_profile || "unknown";
        profileCounts[p] = (profileCounts[p] || 0) + 1;
      }
      if (agent.status === "aborted" || agent.status === "degraded") blockedCount++;
    }
  }

  // Find dominant running profile
  let maxCount = 0;
  for (const [profile, count] of Object.entries(profileCounts)) {
    if (count > maxCount) { maxCount = count; dominantProfile = profile; }
  }

  // Determine costume: status overrides profile
  let costumeKey = "idle";
  if (blockedCount > 0) {
    costumeKey = "blocked";
  } else if (runningCount > 0) {
    // If all running agents are the same profile, show that profile's costume
    if (dominantProfile && MASCOT_COSTUMES[dominantProfile] && Object.keys(profileCounts).length === 1) {
      costumeKey = dominantProfile;
    } else {
      costumeKey = "working";
    }
  }

  const config = MASCOT_COSTUMES[costumeKey] || MASCOT_COSTUMES.idle;
  mascot.dataset.mascotState = costumeKey;
  if (img.src !== new URL(config.src, window.location.origin).href) {
    img.src = config.src;
  }
  label.textContent = runningCount > 0
    ? `${runningCount} running${dominantProfile && Object.keys(profileCounts).length === 1 ? ` · ${dominantProfile}` : ""}`
    : blockedCount > 0 ? `${blockedCount} blocked` : config.label;
}

// --- API layer ---

async function fetchJson(path) {
  const r = await fetch(`${PROXY_BASE}${path}`);
  const text = await r.text();
  if (!r.ok) {
    throw new Error(`HTTP ${r.status}: ${text.slice(0, 200)}`);
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`Non-JSON response from ${path}: ${text.slice(0, 100)}`);
  }
}

async function fetchProjects() {
  return fetchJson("/api/miche/studio/projects");
}

async function fetchProjectAgents(projectId) {
  return fetchJson(`/api/miche/studio/projects/${encodeURIComponent(projectId)}/agents`);
}

async function fetchAgentHints(agentId) {
  return fetchJson(`/api/miche/studio/agents/${encodeURIComponent(agentId)}/attach-hints`);
}

async function fetchAgentLoop(agentId) {
  return fetchJson(`/api/miche/studio/agents/${encodeURIComponent(agentId)}/autonomous-loop`);
}

async function startAutonomousLoop(agentId, visionRef) {
  const r = await fetch(`${PROXY_BASE}/api/miche/autonomous-loop/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ agent_id: agentId, vision_ref: visionRef, cassette: true }),
  });
  const text = await r.text();
  let data;
  try { data = JSON.parse(text); } catch { throw new Error(`HTTP ${r.status}: ${text.slice(0, 200)}`); }
  if (!r.ok) throw new Error(data.detail || data.message || `HTTP ${r.status}`);
  return data;
}

async function resumeLoop(loopRunId, target) {
  const r = await fetch(`${PROXY_BASE}/api/miche/autonomous-loop/${encodeURIComponent(loopRunId)}/resume`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target }),
  });
  const text = await r.text();
  let data;
  try { data = JSON.parse(text); } catch { throw new Error(`HTTP ${r.status}: ${text.slice(0, 200)}`); }
  if (!r.ok) throw new Error(data.detail || data.message || `HTTP ${r.status}`);
  return data;
}

async function abortLoop(loopRunId) {
  const r = await fetch(`${PROXY_BASE}/api/miche/autonomous-loop/${encodeURIComponent(loopRunId)}/abort`, {
    method: "POST",
  });
  const text = await r.text();
  let data;
  try { data = JSON.parse(text); } catch { throw new Error(`HTTP ${r.status}: ${text.slice(0, 200)}`); }
  if (!r.ok) throw new Error(data.detail || data.message || `HTTP ${r.status}`);
  return data;
}

async function postAgentAction(agentId, action, body = {}) {
  const r = await fetch(`${PROXY_BASE}/api/miche/studio/agents/${encodeURIComponent(agentId)}/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const text = await r.text().catch(() => "");
    throw new Error(`HTTP ${r.status}: ${text.slice(0, 200)}`);
  }
  return r.json();
}

async function createAgent(projectId, body) {
  const r = await fetch(`${PROXY_BASE}/api/miche/studio/projects/${encodeURIComponent(projectId)}/agents`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const text = await r.text();
  let data;
  try { data = JSON.parse(text); } catch { throw new Error(`HTTP ${r.status}: ${text.slice(0, 200)}`); }
  if (!r.ok) {
    const code = data.code || "";
    if (r.status === 409 && code === "duplicate_active") {
      throw new Error(`Active agent already exists: ${data.existing_id}`);
    }
    throw new Error(data.detail || data.message || `HTTP ${r.status}`);
  }
  return data;
}

// --- Rendering ---

function statusDotClass(status) {
  const s = escapeHtml(String(status || "").toLowerCase());
  return `orchestrate-dot orchestrate-dot--${s}`;
}

function isStale(heartbeatAt) {
  if (!heartbeatAt) return true; // no heartbeat = unknown state, treat as stale
  const ts = new Date(heartbeatAt).getTime();
  if (Number.isNaN(ts)) return true; // malformed timestamp = stale
  return Date.now() - ts > STALE_HEARTBEAT_MS;
}

function renderAgentRow(agent, index) {
  const agentId = agent.agent_id || `__orphan_${index}`;
  const status = escapeHtml(agent.status || "unknown");
  const profile = escapeHtml(agent.cli_profile || "?");
  const phase = escapeHtml(agent.skill_phase || "idle");
  const sub = escapeHtml(agent.subproject_path || "/");
  const stale = isStale(agent.heartbeat_at);

  let actions = "";
  if (agent.status === "running") {
    actions = `
      <button class="orchestrate-btn" data-action="pause" data-agent-id="${escapeHtml(agentId)}" aria-label="Pause agent ${escapeHtml(agentId)}">Pause</button>
      <button class="orchestrate-btn" data-action="done" data-agent-id="${escapeHtml(agentId)}" aria-label="Mark agent ${escapeHtml(agentId)} done">Done</button>
      <button class="orchestrate-btn orchestrate-btn--danger" data-action="abort" data-agent-id="${escapeHtml(agentId)}" aria-label="Abort agent ${escapeHtml(agentId)}">Abort</button>
    `;
  } else if (agent.status === "paused") {
    actions = `
      <button class="orchestrate-btn" data-action="resume" data-agent-id="${escapeHtml(agentId)}" aria-label="Resume agent ${escapeHtml(agentId)}">Resume</button>
      <button class="orchestrate-btn orchestrate-btn--danger" data-action="abort" data-agent-id="${escapeHtml(agentId)}" aria-label="Abort agent ${escapeHtml(agentId)}">Abort</button>
    `;
  } else if (agent.status === "idle") {
    actions = `
      <button class="orchestrate-btn" data-action="done" data-agent-id="${escapeHtml(agentId)}" aria-label="Mark agent ${escapeHtml(agentId)} done">Done</button>
      <button class="orchestrate-btn orchestrate-btn--danger" data-action="abort" data-agent-id="${escapeHtml(agentId)}" aria-label="Abort agent ${escapeHtml(agentId)}">Abort</button>
    `;
  }

  // Loop status (if active)
  let loopHtml = "";
  if (agent._loop) {
    const loop = agent._loop;
    const loopStatus = escapeHtml(loop.status || "unknown");
    const loopPhase = escapeHtml(loop.current_phase || "?");
    const loopRound = loop.current_round || 0;
    loopHtml = `<div class="orchestrate-loop-status">
      <span class="orchestrate-loop-dot orchestrate-loop-dot--${loopStatus}"></span>
      Loop: ${loopPhase} (r${loopRound}) — ${loopStatus}
      ${loop.status === "active" ? `<button class="orchestrate-btn orchestrate-btn--danger" data-action="abort-loop" data-loop-id="${escapeHtml(loop.loop_run_id)}" aria-label="Abort autonomous loop">Abort Loop</button>` : ""}
    </div>`;
  }

  return `
    <li class="orchestrate-agent-row" data-agent-id="${escapeHtml(agentId)}">
      <span class="${statusDotClass(agent.status)}" title="${status}" role="status" aria-label="Agent status: ${status}"></span>
      <span class="orchestrate-profile">${profile}</span>
      <span>${sub}</span>
      <span class="muted">${phase}</span>
      ${stale ? '<span class="orchestrate-stale" role="status" aria-label="Agent heartbeat stale">stale</span>' : ""}
      <span class="orchestrate-agent-actions">
        <button class="orchestrate-btn" data-action="hints" data-agent-id="${escapeHtml(agentId)}" aria-label="Show attach hints for agent ${escapeHtml(agentId)}" aria-expanded="false">Hints</button>
        ${actions}
      </span>
    </li>
    ${loopHtml}
    <li class="orchestrate-hints-panel" data-hints-for="${escapeHtml(agentId)}" style="display:none" role="region" aria-label="Attach hints for agent ${escapeHtml(agentId)}"></li>
  `;
}

function renderProjectCard(project) {
  const title = escapeHtml(project.label || project.project_id);
  const active = project.active_session_count || 0;
  const total = project.session_count || 0;
  const agents = project._agents || [];
  const agentRows = agents.length
    ? agents.map((a, i) => renderAgentRow(a, i)).join("")
    : '<li class="orchestrate-agent-row muted">No agents</li>';

  return `
    <div class="orchestrate-card" data-project-id="${escapeHtml(project.project_id)}">
      <div class="orchestrate-card__header">
        <h2 class="orchestrate-card__title">${title}</h2>
        <span class="orchestrate-card__counts">${active} active / ${total} sessions</span>
      </div>
      <div class="orchestrate-card__body">
        <ul class="orchestrate-agent-list" data-agent-list>
          ${agentRows}
        </ul>
      </div>
      <div class="orchestrate-card__footer">
        <button class="orchestrate-btn" data-action="show-create" data-project-id="${escapeHtml(project.project_id)}">+ New Agent</button>
        <form class="orchestrate-create-form" data-create-form="${escapeHtml(project.project_id)}" style="display:none">
          <div class="orchestrate-form-row">
            <label>Subproject path <input type="text" name="subproject_path" placeholder="/" required class="orchestrate-input"></label>
          </div>
          <div class="orchestrate-form-row">
            <label>CLI Profile
              <select name="cli_profile" class="orchestrate-select">
                <option value="claude">Claude Code</option>
                <option value="grok">Grok Build</option>
                <option value="mimo">MiMo Code</option>
                <option value="codex">Codex</option>
              </select>
            </label>
          </div>
          <div class="orchestrate-form-row">
            <label>Skill Phase
              <select name="skill_phase" class="orchestrate-select">
                <option value="egghead">egghead</option>
                <option value="htmlspec">htmlspec</option>
                <option value="caffenagent">caffenagent</option>
                <option value="prcrouch">prcrouch</option>
                <option value="gap_review">gap_review</option>
              </select>
            </label>
          </div>
          <div class="orchestrate-form-row">
            <label>Vision memo <textarea name="vision_memo" rows="2" class="orchestrate-input" placeholder="Optional — what should this agent focus on?"></textarea></label>
          </div>
          <div class="orchestrate-form-actions">
            <button type="submit" class="orchestrate-btn">Create</button>
            <button type="button" class="orchestrate-btn" data-action="hide-create" data-project-id="${escapeHtml(project.project_id)}">Cancel</button>
          </div>
          <p class="orchestrate-form-error" data-create-error="${escapeHtml(project.project_id)}" style="display:none"></p>
        </form>
      </div>
    </div>
  `;
}

function renderGrid(projects) {
  const grid = document.querySelector("[data-project-grid]");
  if (!grid) return;

  if (!projects || projects.length === 0) {
    grid.innerHTML = '<p class="orchestrate-empty">No projects registered. Add projects to the caffenagent Studio.</p>';
    return;
  }

  grid.innerHTML = projects.map(renderProjectCard).join("");
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

// --- Polling ---

let pollTimer = null;
let consecutiveErrors = 0;
let pollInFlight = false;

function collectOpenForms() {
  const forms = [];
  document.querySelectorAll("[data-create-form]").forEach((form) => {
    if (form.style.display !== "none") {
      const fd = new FormData(form);
      forms.push({
        projectId: form.dataset.createForm,
        values: Object.fromEntries(fd.entries()),
      });
    }
  });
  return forms;
}

function restoreOpenForms(saved) {
  for (const { projectId, values } of saved) {
    const form = document.querySelector(`[data-create-form="${CSS.escape(projectId)}"]`);
    if (!form) continue;
    form.style.display = "";
    for (const [name, val] of Object.entries(values)) {
      const input = form.querySelector(`[name="${CSS.escape(name)}"]`);
      if (input) input.value = val;
    }
    const showBtn = form.closest(".orchestrate-card__footer")?.querySelector("[data-action='show-create']");
    if (showBtn) showBtn.style.display = "none";
  }
}

function currentInterval() {
  return consecutiveErrors >= MAX_CONSECUTIVE_ERRORS ? POLL_BACKOFF_MS : POLL_INTERVAL_MS;
}

async function poll() {
  if (pollInFlight) return;
  pollInFlight = true;
  try {
    const data = await fetchProjects();
    if (!data.ok) {
      consecutiveErrors++;
      updateConnectionStatus("error", data.message || "caffenagent error");
      restartPollingWithBackoff();
      return;
    }

    const projects = data.projects || [];

    // Fetch agents for each project in parallel
    const agentPromises = projects.map(async (p) => {
      try {
        const agentData = await fetchProjectAgents(p.project_id);
        p._agents = agentData.agents || [];
        // Fetch loop status for each agent
        for (const agent of p._agents) {
          try {
            const loopData = await fetchAgentLoop(agent.agent_id);
            agent._loop = loopData.loop || null;
          } catch {
            agent._loop = null;
          }
        }
      } catch {
        p._agents = [];
      }
    });
    await Promise.all(agentPromises);

    consecutiveErrors = 0;
    // Protect open forms from being wiped by re-render
    const openForms = collectOpenForms();
    renderGrid(projects);
    restoreOpenForms(openForms);
    updateMascotState(projects);
    updateConnectionStatus("ok", "Connected");
    updateLastUpdated();
    // Reset to normal polling interval after recovery from backoff
    if (currentInterval() !== POLL_INTERVAL_MS) {
      restartPollingWithBackoff(); // now uses 5s since consecutiveErrors === 0
    }
  } catch (err) {
    consecutiveErrors++;
    updateConnectionStatus("error", `Disconnected: ${err.message}`);
    restartPollingWithBackoff();
  } finally {
    pollInFlight = false;
    // Don't restart polling if tab is hidden (prevents background polling after rapid toggle)
    if (document.hidden) return;
  }
}

function restartPollingWithBackoff() {
  stopPolling();
  pollTimer = setInterval(poll, currentInterval());
}

function startPolling() {
  if (pollTimer) return;
  poll(); // immediate first poll
  pollTimer = setInterval(poll, POLL_INTERVAL_MS);
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

// --- Agent actions ---

async function handleAgentAction(agentId, action) {
  try {
    if (action === "hints") {
      const panel = document.querySelector(`[data-hints-for="${CSS.escape(agentId)}"]`);
      if (!panel) return;
      const btn = e.target.closest(`[data-action="hints"]`);
      if (panel.style.display !== "none") {
        panel.style.display = "none";
        if (btn) btn.setAttribute("aria-expanded", "false");
        return;
      }
      const data = await fetchAgentHints(agentId);
      const hints = data.attach_hints || [];
      panel.innerHTML = `<div class="orchestrate-hints">${hints.length ? escapeHtml(hints.join("\n")) : "No attach hints available."}</div>`;
      panel.style.display = "";
      if (btn) btn.setAttribute("aria-expanded", "true");
      return;
    }
    if (action === "done") {
      const summary = prompt("Confirmation required to mark done. Enter summary (or leave blank):");
      if (summary === null) return; // cancelled
      await postAgentAction(agentId, "done", { confirm: "yes", summary });
    } else if (action === "abort") {
      const reason = prompt("Reason for abort (required):");
      if (!reason) return;
      await postAgentAction(agentId, "abort", { reason });
    } else if (action === "pause") {
      await postAgentAction(agentId, "pause");
    } else if (action === "resume") {
      await postAgentAction(agentId, "resume");
    }
    // Refresh immediately after action
    poll();
  } catch (err) {
    console.error(`[miche-orchestrate] action ${action} failed:`, err);
    alert(`Action failed: ${err.message}`);
  }
}

// --- Event delegation ---

function initActionHandlers() {
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-action]");
    if (!btn) return;
    const action = btn.dataset.action;
    const agentId = btn.dataset.agentId;
    const projectId = btn.dataset.projectId;

    if (action === "show-create" && projectId) {
      const form = document.querySelector(`[data-create-form="${CSS.escape(projectId)}"]`);
      if (form) { form.style.display = ""; btn.style.display = "none"; }
      return;
    }
    if (action === "hide-create" && projectId) {
      const form = document.querySelector(`[data-create-form="${CSS.escape(projectId)}"]`);
      const showBtn = btn.closest(".orchestrate-card__footer")?.querySelector("[data-action='show-create']");
      if (form) form.style.display = "none";
      if (showBtn) showBtn.style.display = "";
      return;
    }
    if (!action || !agentId) {
      // Handle loop-specific actions
      const loopId = btn.dataset.loopId;
      if (action === "abort-loop" && loopId) {
        btn.disabled = true;
        abortLoop(loopId).then(() => poll()).catch((err) => alert(`Abort failed: ${err.message}`)).finally(() => { btn.disabled = false; });
      }
      return;
    }
    btn.disabled = true;
    handleAgentAction(agentId, action).finally(() => {
      btn.disabled = false;
    });
  });

  // Form submissions
  document.addEventListener("submit", (e) => {
    const form = e.target.closest("[data-create-form]");
    if (!form) return;
    e.preventDefault();
    const projectId = form.dataset.createForm;
    const fd = new FormData(form);
    const body = {
      subproject_path: fd.get("subproject_path") || "/",
      cli_profile: fd.get("cli_profile") || "grok",
      skill_phase: fd.get("skill_phase") || "egghead",
      vision_memo: fd.get("vision_memo") || "",
    };
    const submitBtn = form.querySelector("[type='submit']");
    const errorEl = document.querySelector(`[data-create-error="${CSS.escape(projectId)}"]`);
    if (errorEl) { errorEl.style.display = "none"; errorEl.textContent = ""; }
    if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = "Creating…"; }

    createAgent(projectId, body)
      .then(() => {
        form.style.display = "none";
        form.reset();
        const showBtn = form.closest(".orchestrate-card__footer")?.querySelector("[data-action='show-create']");
        if (showBtn) showBtn.style.display = "";
        poll();
      })
      .catch((err) => {
        if (errorEl) { errorEl.textContent = err.message; errorEl.style.display = ""; }
      })
      .finally(() => {
        if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = "Create"; }
      });
  });
}

// --- Visibility change ---

function initVisibilityHandler() {
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      stopPolling();
    } else {
      startPolling();
    }
  });
}

// --- Island mount (same contract as home.js) ---

async function initIsland() {
  try {
    const { mountFloatingIsland } = await import("./island.js");
    mountFloatingIsland();
  } catch (err) {
    console.error("[miche-orchestrate] island mount failed", err);
  }
}

// --- Init ---

function init() {
  assertMountContract();
  initActionHandlers();
  initVisibilityHandler();
  startPolling();
  initIsland();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
