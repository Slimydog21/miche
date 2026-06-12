/**
 * Shared utilities for Miche client-side JS.
 * Import from home.js, orchestrate.js, island.js.
 */

export function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function renderMarkdownSafe(text) {
  const escaped = escapeHtml(text);
  return escaped
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\n/g, "<br />");
}

export function formatTimestamp(isoString) {
  try {
    const d = new Date(isoString);
    if (Number.isNaN(d.getTime())) return "unknown";
    return d.toLocaleTimeString();
  } catch {
    return "unknown";
  }
}

export function timeAgo(isoString) {
  try {
    const d = new Date(isoString);
    if (Number.isNaN(d.getTime())) return "unknown";
    const diff = Date.now() - d.getTime();
    if (diff < 60_000) return "just now";
    if (diff < 3600_000) return `${Math.floor(diff / 60_000)}m ago`;
    if (diff < 86400_000) return `${Math.floor(diff / 3600_000)}h ago`;
    return `${Math.floor(diff / 86400_000)}d ago`;
  } catch {
    return "unknown";
  }
}
