/**
 * api.js
 * ======
 * All communication between frontend and backend.
 *
 * ✅ Correct: Frontend → Backend → Agents → LLM
 * ❌ Wrong:   Frontend → Anthropic API directly
 *
 * Every request goes through YOUR backend server.
 * The backend holds the API key, handles auth, and orchestrates agents.
 */

const API = {
  BASE: "",

  // ── Auth helpers ─────────────────────────────────────
  getToken()        { return localStorage.getItem("lexai_token"); },
  setToken(token)   { localStorage.setItem("lexai_token", token); },
  clearToken()      { localStorage.removeItem("lexai_token"); },
  isLoggedIn()      { return !!this.getToken(); },

  _headers(extra = {}) {
    const h = { "Content-Type": "application/json", ...extra };
    const t = this.getToken();
    if (t) h["Authorization"] = `Bearer ${t}`;
    return h;
  },

  async _fetch(path, opts = {}) {
    let res;
    try {
      res = await fetch(this.BASE + path, {
        ...opts,
        headers: this._headers(opts.headers || {}),
      });
    } catch {
      throw new Error(`Could not reach backend on ${this.BASE}`);
    }
    if (res.status === 401) { this.clearToken(); showAuthModal(); throw new Error("Session expired"); }
    if (!res.ok) {
      let msg = `HTTP ${res.status}`;
      try { msg = (await res.json()).detail || msg; } catch {}
      throw new Error(msg);
    }
    return res;
  },

  // ── Auth ─────────────────────────────────────────────
  async register(username, email, password) {
    const res = await this._fetch("/auth/register", {
      method: "POST", body: JSON.stringify({ username, email, password }),
    });
    return res.json();
  },

  async login(username, password) {
    let res;
    try {
      res = await fetch(this.BASE + "/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ username, password }),
      });
    } catch {
      throw new Error(`Could not reach backend on ${this.BASE}`);
    }
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Login failed"); }
    const data = await res.json();
    this.setToken(data.access_token);
    return data;
  },

  async getMe() {
    const res = await this._fetch("/auth/me");
    return res.json();
  },

  // ── Analysis (streaming SSE) ──────────────────────────
  async analyzeStream(caseDescription, includeAppeals, onStage) {
    const res = await this._fetch("/analyze/stream", {
      method: "POST",
      body: JSON.stringify({ case_description: caseDescription, include_appeals: includeAppeals }),
    });

    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    let   buffer  = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const raw = line.slice(6).trim();
        if (raw === "[DONE]") return;
        try { const { stage, data } = JSON.parse(raw); onStage(stage, data); } catch {}
      }
    }
  },

  // ── Case History ─────────────────────────────────────
  async getCases(limit = 20, offset = 0) {
    const res = await this._fetch(`/cases?limit=${limit}&offset=${offset}`);
    return res.json();
  },

  async getCase(caseId) {
    const res = await this._fetch(`/cases/${caseId}`);
    return res.json();
  },

  async deleteCase(caseId) {
    await this._fetch(`/cases/${caseId}`, { method: "DELETE" });
  },

  // ── PDF Export ────────────────────────────────────────
  async downloadPDF(caseId) {
    const res = await this._fetch(`/cases/${caseId}/pdf`);
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = `lexai_${caseId.slice(0, 8)}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  },

  // ── Health ────────────────────────────────────────────
  async health() {
    const res = await fetch(this.BASE + "/health");
    return res.json();
  },
};
