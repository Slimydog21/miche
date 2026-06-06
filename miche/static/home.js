/**
 * Home shell client — MPLAT-SPR-02
 * Keeps empty inboxes honest; island mount id frozen for SPR-05.
 */

/** Frozen for SPR-05 — do not rename without bumping layout_version. */
export const MOUNT_ID = "miche-island-mount";

function assertMountContract() {
  const mount = document.getElementById(MOUNT_ID);
  if (!mount) {
    console.error(`[miche-home] missing required mount #${MOUNT_ID}`);
    return;
  }
  // shell: layout + mount present; island: SPR-05 sets "island" when widget mounts
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

function init() {
  assertMountContract();
  markEmptyInboxes();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}