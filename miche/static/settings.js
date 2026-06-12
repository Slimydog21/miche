/**
 * Settings page — read-only configuration state viewer.
 *
 * Fetches health endpoints, registered apps, and displays environment status.
 * Imports shared utilities from utils.js.
 */

import { escapeHtml } from "./utils.js";

const PROXY_BASE = "/api/caffenagent";

// --- Utilities ---

function assertMountContract() {
  const mount = document.getElementById("miche-island-mount");
  if (!mount) {
    console.error("[miche-settings] missing required mount #miche-island-mount");
    return;
  }
  mount.dataset.islandReady = "shell";
}

// --- API layer ---

async function fetchJson(url) {
  const r = await fetch(url);
  const text = await r.text();
  if (!r.ok) {
    throw new Error(`HTTP ${r.status}: ${text.slice(0, 200)}`);
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`Non-JSON response from ${url}: ${text.slice(0, 100)}`);
  }
}

async function fetchMicheHealth() {
  return fetchJson("/api/health");
}

async function fetchCaffenagentHealth() {
  return fetchJson(`${PROXY_BASE}/api/health`);
}

async function fetchPlatformApps() {
  return fetchJson("/api/platform/apps");
}

// --- Rendering ---

function statusBadge(ok, label) {
  const cls = ok ? "settings-badge settings-badge--ok" : "settings-badge settings-badge--fail";
  const text = ok ? "OK" : "Unavailable";
  return `<span class="${cls}" aria-label="${escapeHtml(label)}: ${text}">${escapeHtml(text)}</span>`;
}

function renderServiceStatus(micheOk, caffenagentOk) {
  const container = document.querySelector("[data-service-status]");
  if (!container) return;
  container.innerHTML = `
    <div class="settings-row">
      <span class="settings-row__label">Miche Platform</span>
      ${statusBadge(micheOk, "Miche")}
    </div>
    <div class="settings-row">
      <span class="settings-row__label">caffenagent (via proxy)</span>
      ${statusBadge(caffenagentOk, "caffenagent")}
    </div>
    <div class="settings-row">
      <span class="settings-row__label">Active Profile</span>
      <span class="settings-row__value">${escapeHtml(document.body.dataset.installProfile || "unknown")}</span>
    </div>
  `;
}

function renderEnvStatus(regData) {
  const container = document.querySelector("[data-env-status]");
  if (!container) return;
  const hasApps = regData && regData.apps && regData.apps.length > 0;
  const profile = regData ? regData.install_profile : "unknown";

  let caffenagentConfigured = false;
  let authConfigured = false;
  if (hasApps) {
    for (const app of regData.apps) {
      if (app.id === "caffenagent") {
        caffenagentConfigured = !!app.base_url_configured;
        authConfigured = true;
        break;
      }
    }
  }

  container.innerHTML = `
    <div class="settings-row">
      <span class="settings-row__label">CAFFENAGENT_PUBLIC_BASE_URL</span>
      ${statusBadge(caffenagentConfigured, "CAFFENAGENT_PUBLIC_BASE_URL")}
    </div>
    <div class="settings-row">
      <span class="settings-row__label">Auth credentials configured</span>
      ${statusBadge(authConfigured, "Auth")}
    </div>
    <div class="settings-row">
      <span class="settings-row__label">Install profile</span>
      <span class="settings-row__value">${escapeHtml(profile)}</span>
    </div>
    <div class="settings-row">
      <span class="settings-row__label">Registry version</span>
      <span class="settings-row__value">${escapeHtml(regData ? regData.version : "?")}</span>
    </div>
  `;
}

function renderApps(apps) {
  const container = document.querySelector("[data-apps-list]");
  if (!container) return;

  if (!apps || apps.length === 0) {
    container.innerHTML = '<p class="settings-empty">No apps registered.</p>';
    return;
  }

  const rows = apps.map((app) => {
    const name = escapeHtml(app.display_name || app.id);
    const enabled = app.enabled !== false;
    const baseOk = !!app.base_url_configured;
    const capCount = (app.capabilities || []).length;
    return `
      <div class="settings-app-row">
        <span class="settings-app-row__name">${name}</span>
        <span class="settings-app-row__id">${escapeHtml(app.id)}</span>
        <span class="settings-app-row__enabled ${enabled ? "" : "muted"}">${enabled ? "enabled" : "disabled"}</span>
        <span class="settings-app-row__url">${statusBadge(baseOk, app.id + " base_url")}</span>
        <span class="settings-app-row__caps">${capCount} cap${capCount === 1 ? "" : "s"}</span>
      </div>
    `;
  }).join("");

  container.innerHTML = `
    <div class="settings-app-header">
      <span>Name</span>
      <span>ID</span>
      <span>Status</span>
      <span>URL</span>
      <span>Caps</span>
    </div>
    ${rows}
  `;
}

// --- Init ---

async function loadSettings() {
  let micheOk = false;
  let caffenagentOk = false;
  let regData = null;

  try {
    const health = await fetchMicheHealth();
    micheOk = health && health.status === "ok";
  } catch {
    micheOk = false;
  }

  try {
    const health = await fetchCaffenagentHealth();
    caffenagentOk = health && health.status === "ok";
  } catch {
    caffenagentOk = false;
  }

  try {
    const data = await fetchPlatformApps();
    if (data && data.ok) {
      regData = data;
    }
  } catch {
    regData = null;
  }

  renderServiceStatus(micheOk, caffenagentOk);
  renderEnvStatus(regData);
  renderApps(regData ? regData.apps : []);
}

function initIsland() {
  try {
    import("./island.js").then((mod) => {
      mod.mountFloatingIsland();
    }).catch((err) => {
      console.error("[miche-settings] island mount failed", err);
    });
  } catch (err) {
    console.error("[miche-settings] island mount failed", err);
  }
}

function init() {
  assertMountContract();
  loadSettings();
  initIsland();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
