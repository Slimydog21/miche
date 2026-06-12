import { escapeHtml } from "./utils.js";

const PROXY_BASE = "/api/caffenagent";
const START_PATH = "/api/miche-voice/start";

let currentRunId = null;

function assertMountContract() {
  const mount = document.getElementById("miche-island-mount");
  if (!mount) {
    console.error("[miche-voice] missing required mount #miche-island-mount");
    return;
  }
  mount.dataset.islandReady = "shell";
}

async function startVoice(transcript) {
  const r = await fetch(`${PROXY_BASE}${START_PATH}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ transcript, project: "miche" }),
  });
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

async function checkStatus(runId) {
  const r = await fetch(`${PROXY_BASE}/api/miche-voice/${encodeURIComponent(runId)}`);
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

function statusBadgeClass(status) {
  const s = String(status || "").toLowerCase();
  return `voice-status__badge voice-status__badge--${escapeHtml(s)}`;
}

function renderRun(runId, status) {
  const resultsEl = document.querySelector("[data-voice-results]");
  if (!resultsEl) return;
  resultsEl.hidden = false;

  const idEl = document.querySelector("[data-run-id]");
  if (idEl) idEl.textContent = runId || "—";

  const statusEl = document.querySelector("[data-run-status]");
  if (statusEl) {
    statusEl.textContent = status || "—";
    statusEl.className = statusBadgeClass(status);
  }
}

function renderIntents(intents) {
  const el = document.querySelector("[data-intents]");
  if (!el) return;
  if (!intents || intents.length === 0) {
    el.innerHTML = '<p class="voice-intents__empty">No intents returned.</p>';
    return;
  }
  el.innerHTML = intents
    .map((intent) => {
      const name = escapeHtml(String(intent.name || intent.intent || "—"));
      const conf = intent.confidence != null ? escapeHtml(String(intent.confidence)) : "—";
      const raw = escapeHtml(JSON.stringify(intent, null, 2));
      return `
      <div class="voice-intent">
        <div class="voice-intent__header">
          <span class="voice-intent__name">${name}</span>
          <span class="voice-intent__conf">${conf}</span>
        </div>
        <pre class="voice-intent__raw">${raw}</pre>
      </div>`;
    })
    .join("");
}

async function handleSubmit(e) {
  e.preventDefault();
  const textarea = document.getElementById("voice-transcript");
  if (!textarea) return;
  const transcript = textarea.value.trim();
  if (!transcript) return;

  const btn = document.querySelector(".voice-form__submit");
  if (btn) { btn.disabled = true; btn.textContent = "Starting…"; }

  try {
    const data = await startVoice(transcript);
    currentRunId = data.run_id || data.id || null;
    renderRun(currentRunId, data.status || "started");
    renderIntents(data.intents || []);
  } catch (err) {
    console.error("[miche-voice] start error", err);
    renderRun("—", `Error: ${err.message}`);
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = "Start"; }
  }
}

async function handleCheckStatus() {
  if (!currentRunId) return;
  try {
    const data = await checkStatus(currentRunId);
    renderRun(currentRunId, data.status || "unknown");
    renderIntents(data.intents || []);
  } catch (err) {
    console.error("[miche-voice] status error", err);
    const statusEl = document.querySelector("[data-run-status]");
    if (statusEl) {
      statusEl.textContent = `Error: ${err.message}`;
      statusEl.className = "voice-status__badge voice-status__badge--error";
    }
  }
}

function initActionHandlers() {
  const form = document.querySelector("[data-voice-form]");
  if (form) form.addEventListener("submit", handleSubmit);

  document.addEventListener("click", (e) => {
    const actionEl = e.target.closest("[data-action]");
    if (!actionEl) return;
    if (actionEl.dataset.action === "check-status") {
      e.preventDefault();
      handleCheckStatus();
    }
  });
}

async function initIsland() {
  try {
    const { mountFloatingIsland } = await import("./island.js");
    mountFloatingIsland();
  } catch (err) {
    console.error("[miche-voice] island mount failed", err);
  }
}

function init() {
  assertMountContract();
  initActionHandlers();
  initIsland();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
