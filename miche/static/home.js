/**
 * Home shell client — MPLAT-SPR-02 + information expand MPLAT-SPR-04
 */

/** Frozen for SPR-05 — do not rename without bumping layout_version. */
export const MOUNT_ID = "miche-island-mount";

const EXPAND_THRESHOLD = 200;

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderMarkdownSafe(text) {
  const escaped = escapeHtml(text);
  return escaped
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\n/g, "<br />");
}

function initInformationExpand() {
  for (const el of document.querySelectorAll("[data-info-body][data-expandable='true']")) {
    const full = el.textContent || "";
    if (full.length <= EXPAND_THRESHOLD) {
      el.innerHTML = renderMarkdownSafe(full);
      continue;
    }
    const preview = full.slice(0, EXPAND_THRESHOLD).trimEnd() + "…";
    el.innerHTML = renderMarkdownSafe(preview);
    el.dataset.infoFull = full;

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "miche-info-expand";
    btn.textContent = "Show more";
    btn.addEventListener("click", () => {
      const expanded = el.dataset.expanded === "true";
      if (expanded) {
        el.innerHTML = renderMarkdownSafe(preview);
        el.dataset.expanded = "false";
        btn.textContent = "Show more";
      } else {
        el.innerHTML = renderMarkdownSafe(el.dataset.infoFull || full);
        el.dataset.expanded = "true";
        btn.textContent = "Show less";
      }
    });
    el.insertAdjacentElement("afterend", btn);
  }

  for (const el of document.querySelectorAll("[data-info-body][data-expandable='false']")) {
    const full = el.textContent || "";
    el.innerHTML = renderMarkdownSafe(full);
  }
}

function assertMountContract() {
  const mount = document.getElementById(MOUNT_ID);
  if (!mount) {
    console.error(`[miche-home] missing required mount #${MOUNT_ID}`);
    return;
  }
  mount.dataset.islandReady = "shell";
}

function markEmptyInboxes() {
  for (const el of document.querySelectorAll("[data-inbox][data-empty='true']")) {
    const rows = el.querySelectorAll("[data-inbox-row]");
    if (rows.length === 0) {
      el.setAttribute("aria-busy", "false");
    }
  }
}

async function restoreFocusReturn() {
  const params = new URLSearchParams(window.location.search);
  const handoffId = params.get("focus_return");
  if (!handoffId) return;
  try {
    const r = await fetch(`/api/platform/focus/restore?handoff_id=${encodeURIComponent(handoffId)}`);
    if (!r.ok) return;
    const body = await r.json();
    if (body.island_expanded) {
      sessionStorage.setItem("island_expanded", "true");
    } else {
      sessionStorage.setItem("island_expanded", "false");
    }
    params.delete("focus_return");
    const next = params.toString();
    const url = next ? `${window.location.pathname}?${next}` : window.location.pathname;
    window.history.replaceState({}, "", url);
  } catch (err) {
    console.error("[miche-home] focus return restore failed", err);
  }
}

async function initHomeMascot() {
  const mount = document.getElementById("miche-home-mascot");
  if (!mount) return;
  try {
    const params = new URLSearchParams({ context: "home" });
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      params.set("reduced_motion", "true");
    }
    const r = await fetch(`/api/miche/persona?${params.toString()}`);
    if (!r.ok) return;
    const persona = await r.json();
    const img = mount.querySelector("[data-mascot-sprite]");
    if (img && persona.sprite_url) img.src = persona.sprite_url;
    if (persona.animation_key && !persona.reduced_motion) {
      mount.dataset.animation = persona.animation_key;
    }
  } catch (err) {
    console.warn("[miche-home] mascot persona failed", err);
  }
}

async function initIsland() {
  await restoreFocusReturn();
  try {
    const { mountFloatingIsland } = await import("./island.js");
    mountFloatingIsland();
  } catch (err) {
    console.error("[miche-home] island mount failed", err);
  }
}

function init() {
  assertMountContract();
  initInformationExpand();
  markEmptyInboxes();
  initHomeMascot();
  initIsland();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}