/**
 * FloatingIsland — MPLAT-SPR-05 vanilla JS (repo standard, not React)
 */

import { MOUNT_ID } from "./home.js";

const STORAGE_KEY = "island_expanded";

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

function renderInlineCard(card) {
  const type = escapeHtml(card.type || "card");
  const title = escapeHtml(card.title || "");
  const body = escapeHtml(card.body || "");
  const app = escapeHtml(card.source_app_id || "");
  let cta = "";
  if (card.type === "focus_cta" && card.focus_route) {
    const appId = card.source_app_id || "caffenagent";
    const expanded = sessionStorage.getItem(STORAGE_KEY) === "true";
    const qs = new URLSearchParams({ path: card.focus_route });
    if (expanded) qs.set("island_expanded", "true");
    cta = `<a class="miche-island__focus-cta" href="/focus/${escapeHtml(appId)}?${qs.toString()}" data-focus-cta="true">Open in Focus</a>`;
  } else if (card.deep_link) {
    cta = `<a class="miche-island__focus-cta" href="${escapeHtml(card.deep_link)}">${type === "info_summary" ? "View summary" : "Open"}</a>`;
  }
  return `<div class="miche-island__card miche-island__card--${type}" data-card-type="${type}">
    <span class="miche-island__card-type">${type} · ${app}</span>
    <strong>${title}</strong>
    <p>${body}</p>${cta}
  </div>`;
}

function formatAck(body, latencyMs) {
  const appId = body.inline_cards?.[0]?.source_app_id || body.suggested_focus?.app_id || "miche";
  const mode = body.router_mode || "router";
  const ts = new Date().toISOString();
  return `${mode} · ${appId} · ${latencyMs}ms · ${ts}`;
}

function focusablesIn(panel) {
  return Array.from(
    panel.querySelectorAll(
      'button:not([disabled]), textarea:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])'
    )
  ).filter((el) => el.offsetParent !== null);
}

export class FloatingIsland {
  constructor(mountEl, { dock = "bottom-right", personaId = "engine" } = {}) {
    this.mount = mountEl;
    this.dock = dock;
    this.personaId = personaId;
    this.state = "collapsed";
    this.routerMode = "cassette";
    this.mediaRecorder = null;
    this.audioChunks = [];
    this._build();
    this._bind();
    this._restoreExpanded();
    this._loadThread();
  }

  _build() {
    const dockClass = this.dock === "bottom-center" ? "miche-island--dock-center" : "miche-island--dock-right";
    this.root = document.createElement("div");
    this.root.className = `miche-island ${dockClass}`;
    this.root.setAttribute("data-island-state", "collapsed");
    this.root.innerHTML = `
      <button type="button" class="miche-island__pill" aria-expanded="false" aria-controls="miche-island-panel">
        <img src="/static/miche-mascot.svg" alt="" width="28" height="28" />
        <span>Ask Miche</span>
      </button>
      <div id="miche-island-panel" class="miche-island__panel" role="region" aria-label="Miche assistant">
        <header class="miche-island__header">
          <div>
            <h2>Miche</h2>
            <div class="miche-island__cassette-banner" data-cassette-banner hidden>Router cassette mode (dev)</div>
          </div>
          <button type="button" class="miche-island__collapse" aria-label="Collapse island">−</button>
        </header>
        <div class="miche-island__thread" role="log" aria-live="polite" aria-relevant="additions"></div>
        <form class="miche-island__composer">
          <textarea class="miche-island__input" rows="2" placeholder="Ask Miche…" aria-label="Message Miche"></textarea>
          <button type="button" class="miche-island__voice" aria-label="Hold to talk" aria-pressed="false">🎤<span class="miche-island__recording-ring"></span></button>
          <button type="submit" class="miche-island__send" disabled>Send</button>
        </form>
      </div>`;
    this.mount.innerHTML = "";
    this.mount.appendChild(this.root);
    this.mount.classList.add("miche-island-mount--active");
    this.mount.dataset.islandReady = "island";

    this.pill = this.root.querySelector(".miche-island__pill");
    this.panel = this.root.querySelector(".miche-island__panel");
    this.thread = this.root.querySelector(".miche-island__thread");
    this.input = this.root.querySelector(".miche-island__input");
    this.sendBtn = this.root.querySelector(".miche-island__send");
    this.voiceBtn = this.root.querySelector(".miche-island__voice");
    this.collapseBtn = this.root.querySelector(".miche-island__collapse");
    this.cassetteBanner = this.root.querySelector("[data-cassette-banner]");
    this.form = this.root.querySelector(".miche-island__composer");
  }

  _bind() {
    this.pill.addEventListener("click", () => this.expand());
    this.collapseBtn.addEventListener("click", () => this.collapse());
    this.input.addEventListener("input", () => {
      this.sendBtn.disabled = !this.input.value.trim();
    });
    this.input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        this.form.requestSubmit();
      }
    });
    this.form.addEventListener("submit", (e) => {
      e.preventDefault();
      this._sendText();
    });
    this.voiceBtn.addEventListener("mousedown", () => this._startVoice());
    this.voiceBtn.addEventListener("mouseup", () => this._stopVoice());
    this.voiceBtn.addEventListener("mouseleave", () => this._stopVoice());
    this.voiceBtn.addEventListener("touchstart", (e) => {
      e.preventDefault();
      this._startVoice();
    });
    this.voiceBtn.addEventListener("touchend", (e) => {
      e.preventDefault();
      this._stopVoice();
    });
    this._focusTrapHandler = (e) => {
      if (this.state !== "expanded" || e.key !== "Tab") return;
      const list = focusablesIn(this.panel);
      if (!list.length) return;
      const first = list[0];
      const last = list[list.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    this.panel.addEventListener("keydown", this._focusTrapHandler);
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && this.state === "expanded") this.collapse();
    });
  }

  expand() {
    this.state = "expanded";
    this.root.classList.add("miche-island--expanded");
    this.root.setAttribute("data-island-state", "expanded");
    this.pill.setAttribute("aria-expanded", "true");
    sessionStorage.setItem(STORAGE_KEY, "true");
    this.input.focus();
  }

  collapse() {
    this.state = "collapsed";
    this.root.classList.remove("miche-island--expanded", "miche-island--recording");
    this.root.setAttribute("data-island-state", "collapsed");
    this.pill.setAttribute("aria-expanded", "false");
    sessionStorage.setItem(STORAGE_KEY, "false");
    this.pill.focus();
  }

  _restoreExpanded() {
    if (sessionStorage.getItem(STORAGE_KEY) === "true") this.expand();
  }

  async _loadThread() {
    try {
      const r = await fetch("/api/platform/island/thread");
      const body = await r.json();
      if (body.router_mode === "cassette" || body.router_mode === "production_unavailable") {
        this.cassetteBanner.hidden = false;
        this.cassetteBanner.textContent =
          body.router_mode === "cassette"
            ? "Router cassette mode (dev)"
            : "Production router unavailable — honest degraded mode";
      }
      for (const msg of body.messages || []) {
        this._appendMessage(msg.role, msg.content, msg.inline_cards, msg.created_at);
      }
    } catch (err) {
      this._appendError(`Thread load failed: ${err.message}`);
    }
  }

  _appendMessage(role, content, cards, createdAt) {
    const el = document.createElement("div");
    el.className = `miche-island__msg miche-island__msg--${role}`;
    el.setAttribute("role", role === "user" ? "status" : "article");
    el.innerHTML = renderMarkdownSafe(content);
    if (createdAt) {
      const meta = document.createElement("div");
      meta.className = "miche-island__meta";
      meta.textContent = createdAt;
      el.appendChild(meta);
    }
    if (cards && cards.length) {
      for (const card of cards) {
        el.insertAdjacentHTML("beforeend", renderInlineCard(card));
      }
    }
    this.thread.appendChild(el);
    this.thread.scrollTop = this.thread.scrollHeight;
  }

  _appendError(message) {
    const el = document.createElement("div");
    el.className = "miche-island__msg miche-island__msg--error";
    el.setAttribute("role", "alert");
    el.textContent = message;
    this.thread.appendChild(el);
  }

  async _sendText() {
    const text = this.input.value.trim();
    if (!text) return;
    const utteranceId = crypto.randomUUID();
    this.input.value = "";
    this.sendBtn.disabled = true;
    this._appendMessage("user", text, null, new Date().toISOString());

    try {
      const started = performance.now();
      const r = await fetch("/api/platform/island/utterance", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ utterance_id: utteranceId, text, source: "island" }),
      });
      let body = {};
      try {
        body = await r.json();
      } catch {
        body = {};
      }
      if (!r.ok) {
        const detail = typeof body.detail === "string" ? body.detail : r.statusText;
        this._appendError(`Request failed (${r.status}): ${detail}`);
        return;
      }
      const latency = Math.round(performance.now() - started);
      this._appendMessage("assistant", body.reply_markdown, body.inline_cards, formatAck(body, latency));
      if (body.timeout_badge) {
        this._appendError("Router slow (>5s) — timeout badge shown.");
      }
    } catch (err) {
      this._appendError(`Could not reach router: ${err.message}`);
    }
  }

  async _startVoice() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.mediaRecorder = new MediaRecorder(stream);
      this.audioChunks = [];
      this.mediaRecorder.ondataavailable = (e) => this.audioChunks.push(e.data);
      this.mediaRecorder.start();
      this.voiceBtn.setAttribute("aria-pressed", "true");
      this.root.classList.add("miche-island--recording");
    } catch {
      this._appendError("Microphone permission denied — voice capture unavailable.");
    }
  }

  async _stopVoice() {
    if (!this.mediaRecorder || this.mediaRecorder.state === "inactive") return;
    this.voiceBtn.setAttribute("aria-pressed", "false");
    this.root.classList.remove("miche-island--recording");
    const recorder = this.mediaRecorder;
    const done = new Promise((resolve) => {
      recorder.onstop = resolve;
    });
    recorder.stop();
    recorder.stream.getTracks().forEach((t) => t.stop());
    await done;
    const blob = new Blob(this.audioChunks, { type: "audio/webm" });
    const utteranceId = crypto.randomUUID();
    const form = new FormData();
    form.append("utterance_id", utteranceId);
    form.append("audio", blob, "voice.webm");
    try {
      const r = await fetch("/api/platform/island/voice", { method: "POST", body: form });
      const body = await r.json();
      if (!r.ok) throw new Error(body.detail || r.statusText);
      if (body.voice?.user_line) {
        this._appendMessage("user", body.voice.user_line, null, body.voice.created_at);
      }
      if (body.route) {
        this._appendMessage("assistant", body.route.reply_markdown, body.route.inline_cards);
      }
    } catch (err) {
      this._appendError(`Voice upload failed: ${err.message}`);
    }
    this.mediaRecorder = null;
  }
}

export function mountFloatingIsland() {
  const mount = document.getElementById(MOUNT_ID);
  if (!mount) {
    console.error("[miche-island] missing mount");
    return null;
  }
  return new FloatingIsland(mount);
}