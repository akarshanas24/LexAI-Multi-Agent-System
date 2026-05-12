const API = {
  BASE: (() => {
    if (window.LEXAI_API_BASE) return window.LEXAI_API_BASE;
    const isLocalHost = /^(localhost|127\.0\.0\.1)$/i.test(window.location.hostname);
    if (window.location.protocol === "file:") return "http://127.0.0.1:8003";
    if (isLocalHost && ["8000", "8003"].includes(window.location.port)) return "";
    return "http://127.0.0.1:8003";
  })(),

  FALLBACK_BASES: (() => {
    if (window.LEXAI_API_BASE) return [window.LEXAI_API_BASE];
    const bases = [];
    const isLocalHost = /^(localhost|127\.0\.0\.1)$/i.test(window.location.hostname);
    if (window.location.protocol !== "file:" && isLocalHost && window.location.port) {
      bases.push("");
    }
    bases.push("http://127.0.0.1:8003", "http://127.0.0.1:8000");
    return [...new Set(bases)];
  })(),

  getToken() {
    return localStorage.getItem("lexai_token");
  },

  setToken(token) {
    localStorage.setItem("lexai_token", token);
  },

  clearToken() {
    localStorage.removeItem("lexai_token");
  },

  isLoggedIn() {
    return !!this.getToken();
  },

  _headers(extra = {}) {
    const headers = { ...extra };
    const token = this.getToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    return headers;
  },

  async _readJsonResponse(response, fallbackMessage = "Invalid server response") {
    const text = await response.text();
    if (!text) return null;
    try {
      return JSON.parse(text);
    } catch {
      throw new Error(text.trim() || fallbackMessage);
    }
  },

  async _fetch(path, options = {}) {
    let response = null;
    let lastError = null;

    for (const base of this.FALLBACK_BASES) {
      try {
        response = await fetch(base + path, {
          ...options,
          headers: this._headers(options.headers || {}),
        });
        if (response) {
          this.BASE = base;
          break;
        }
      } catch (error) {
        lastError = error;
      }
    }

    if (!response) {
      throw new Error(`Could not reach backend on ${window.location.origin}`);
    }

    if (response.status === 401) {
      this.clearToken();
      window.dispatchEvent(new CustomEvent("lexai:session-expired"));
      throw new Error("Session expired");
    }

    if (!response.ok) {
      let message = `HTTP ${response.status}`;
      try {
        const payload = await this._readJsonResponse(response, message);
        message = payload?.detail || message;
      } catch (error) {
        message = error.message || message;
      }
      throw new Error(message);
    }

    return response;
  },

  async register(username, email, password) {
    const response = await this._fetch("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, password }),
    });
    return this._readJsonResponse(response);
  },

  async resetPassword(identifier, password) {
    const response = await this._fetch("/auth/reset-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier, password }),
    });
    return this._readJsonResponse(response);
  },

  async login(username, password) {
    let response = null;

    for (const base of this.FALLBACK_BASES) {
      try {
        response = await fetch(base + "/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: new URLSearchParams({ username, password }),
        });
        this.BASE = base;
        break;
      } catch {}
    }

    if (!response) {
      throw new Error(`Could not reach backend on ${window.location.origin}`);
    }

    if (!response.ok) {
      try {
        const payload = await this._readJsonResponse(response, "Login failed");
        throw new Error(payload?.detail || "Login failed");
      } catch (error) {
        throw new Error(error.message || "Login failed");
      }
    }

    const data = await this._readJsonResponse(response, "Login failed");
    this.setToken(data.access_token);
    return data;
  },

  async getMe() {
    const response = await this._fetch("/auth/me");
    return this._readJsonResponse(response);
  },

  async analyzeStream(payload, onStage) {
    const response = await this._fetch("/analyze/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const raw = line.slice(6).trim();
        if (raw === "[DONE]") return;
        try {
          const payload = JSON.parse(raw);
          onStage(payload.stage, payload.data);
        } catch {}
      }
    }
  },

  async getCases(limit = 50, offset = 0) {
    const response = await this._fetch(`/cases?limit=${limit}&offset=${offset}`);
    return this._readJsonResponse(response);
  },

  async getCase(caseId) {
    const response = await this._fetch(`/cases/${caseId}`);
    return this._readJsonResponse(response);
  },

  async getCaseEvidence(caseId) {
    const response = await this._fetch(`/cases/${caseId}/evidence`);
    return this._readJsonResponse(response);
  },

  async getAnalytics() {
    const response = await this._fetch("/analytics/summary");
    return this._readJsonResponse(response);
  },

  async getActivityLogs(limit = 50) {
    const response = await this._fetch(`/activity/logs?limit=${limit}`);
    return this._readJsonResponse(response);
  },

  async getKnowledgeDocuments() {
    const response = await this._fetch("/knowledge/documents");
    return this._readJsonResponse(response);
  },

  async saveKnowledgeDocument(payload) {
    const response = await this._fetch("/knowledge/documents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return this._readJsonResponse(response);
  },

  async deleteKnowledgeDocument(docId) {
    await this._fetch(`/knowledge/documents/${docId}`, { method: "DELETE" });
  },

  async getSystemSettings() {
    const response = await this._fetch("/system/settings");
    return this._readJsonResponse(response);
  },

  async updateSystemSettings(payload) {
    const response = await this._fetch("/system/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return this._readJsonResponse(response);
  },

  async deleteCase(caseId) {
    await this._fetch(`/cases/${caseId}`, { method: "DELETE" });
  },

  async downloadPDF(caseId) {
    const response = await this._fetch(`/cases/${caseId}/pdf`);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `lexai_${caseId.slice(0, 8)}.pdf`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  },

  async health() {
    const response = await this._fetch("/health");
    return this._readJsonResponse(response);
  },
};
