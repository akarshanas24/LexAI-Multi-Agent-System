/**
 * app.js
 * ======
 * Main application controller.
 * Wires together: auth modal, case analysis, history panel, PDF export, appeals.
 */

// ── Auth Modal ────────────────────────────────────────
function showAuthModal(tab = "login") {
  $("authModal").style.display = "flex";
  switchAuthTab(tab);
}

function hideAuthModal() {
  $("authModal").style.display = "none";
  $("authError").textContent = "";
}

function switchAuthTab(tab) {
  $("loginTab").style.display  = tab === "login"    ? "block" : "none";
  $("registerTab").style.display = tab === "register" ? "block" : "none";
  $("tabLogin").classList.toggle("active", tab === "login");
  $("tabRegister").classList.toggle("active", tab === "register");
}

function passwordByteLength(password) {
  return new TextEncoder().encode(password).length;
}

function validatePasswordLength(password) {
  const bytes = passwordByteLength(password);
  if (bytes > 256) {
    return `Password is too long (${bytes} bytes). Maximum is 256 bytes.`;
  }
  return "";
}

async function doLogin() {
  const username = $("loginUsername").value.trim();
  const password = $("loginPassword").value;
  if (!username || !password) { $("authError").textContent = "Fill in all fields."; return; }
  const passwordError = validatePasswordLength(password);
  if (passwordError) { $("authError").textContent = passwordError; return; }
  try {
    await API.login(username, password);
    hideAuthModal();
    await onAuthSuccess();
  } catch (e) {
    $("authError").textContent = e.message;
  }
}

async function doRegister() {
  const username = $("regUsername").value.trim();
  const email    = $("regEmail").value.trim();
  const password = $("regPassword").value;
  if (!username || !email || !password) { $("authError").textContent = "Fill in all fields."; return; }
  const passwordError = validatePasswordLength(password);
  if (passwordError) { $("authError").textContent = passwordError; return; }
  try {
    await API.register(username, email, password);
    await API.login(username, password);
    hideAuthModal();
    await onAuthSuccess();
  } catch (e) {
    $("authError").textContent = e.message;
  }
}

async function onAuthSuccess() {
  const me = await API.getMe();
  $("userInfo").textContent = me.username;
  $("userBar").style.display = "flex";
  $("authPrompt").style.display = "none";
  await loadHistory();
}

function doLogout() {
  API.clearToken();
  $("userBar").style.display = "none";
  $("authPrompt").style.display = "flex";
  $("historyList").innerHTML = "";
  clearAll();
}

// ── Case History Sidebar ──────────────────────────────
async function loadHistory() {
  try {
    const data = await API.getCases(20, 0);
    renderHistory(data.cases || []);
  } catch {}
}

function renderHistory(cases) {
  const list = $("historyList");
  if (!cases.length) {
    list.innerHTML = '<p class="history-empty">No cases yet.</p>';
    return;
  }
  list.innerHTML = cases.map(c => `
    <div class="history-item" onclick="loadCase('${c.id}')">
      <div class="history-title">${escHtml(c.title.slice(0, 55))}${c.title.length > 55 ? "…" : ""}</div>
      <div class="history-meta">
        <span class="history-ruling ${rulingClass(c.ruling)}">${c.ruling || "Pending"}</span>
        <span class="history-conf">${c.confidence ? Math.round(c.confidence) + "%" : ""}</span>
        <button class="history-delete" onclick="deleteCase('${c.id}', event)" title="Delete">✕</button>
      </div>
    </div>
  `).join("");
}

function rulingClass(ruling) {
  if (!ruling) return "";
  const r = ruling.toLowerCase();
  if (r.includes("not") || r.includes("insufficient")) return "ruling-green";
  if (r.includes("guilty") || r.includes("liable"))    return "ruling-red";
  return "ruling-amber";
}

async function loadCase(caseId) {
  try {
    const c = await API.getCase(caseId);
    $("caseInput").value = c.case_description;
    const outputs = c.agent_outputs || {};

    showResultsArea();
    ["research", "defense", "prosecution"].forEach(a => {
      if (outputs[a]) { completeAgent(a, renderBullets(outputs[a])); }
    });
    if (outputs.judge) {
      try {
        const v = JSON.parse(outputs.judge);
        completeAgent("judge", `<p>${v.reasoning || ""}</p>${v.key_finding ? `<p><b>Key finding:</b> ${v.key_finding}</p>` : ""}`);
        renderVerdict(v.ruling, v.confidence, v.key_finding);
      } catch {}
    }
    if (outputs.appeals) {
      try {
        const a = JSON.parse(outputs.appeals);
        renderAppeals(a);
      } catch {}
    }
    $("pdfBtn").dataset.caseId = caseId;
    $("pdfBtn").style.display = "inline-flex";
    $("currentCaseId").value = caseId;
  } catch (e) {
    showError("Could not load case: " + e.message);
  }
}

async function deleteCase(caseId, event) {
  event.stopPropagation();
  if (!confirm("Delete this case from history?")) return;
  try {
    await API.deleteCase(caseId);
    await loadHistory();
    if ($("currentCaseId").value === caseId) clearAll();
  } catch (e) {
    showError("Delete failed: " + e.message);
  }
}

async function downloadPDF() {
  const caseId = $("pdfBtn").dataset.caseId || $("currentCaseId").value;
  if (!caseId) { showError("No completed case to export."); return; }
  try {
    $("pdfBtn").textContent = "Generating…";
    await API.downloadPDF(caseId);
  } catch (e) {
    showError("PDF export failed: " + e.message);
  } finally {
    $("pdfBtn").textContent = "Export PDF ↓";
  }
}

// ── Main Analysis Flow ────────────────────────────────
async function analyzeCase() {
  if (!API.isLoggedIn()) { showAuthModal("login"); return; }

  const caseText      = $("caseInput").value.trim();
  const inclAppeals   = $("appealsToggle").checked;
  if (!caseText) { showError("Please describe a legal case before convening the court."); return; }

  setAnalyzeLoading(true);
  showResultsArea();
  $("errorBanner").style.display = "none";
  $("pdfBtn").style.display = "none";
  $("appealsCard").style.display = "none";
  $("currentCaseId").value = "";

  ["research","defense","prosecution","judge","appeals"].forEach(a => {
    setCardState(a, ""); setStatus(a, "idle", "Standby"); setPipeStep(a, "");
  });

  activateAgent("research");
  let currentCaseId = null;

  try {
    await API.analyzeStream(caseText, inclAppeals, (stage, data) => {
      handleAgentResult(stage, data, inclAppeals);
      if (stage === "complete" && data.case_id) {
        currentCaseId = data.case_id;
        $("pdfBtn").dataset.caseId = data.case_id;
        $("pdfBtn").style.display = "inline-flex";
        $("currentCaseId").value  = data.case_id;
        loadHistory(); // refresh sidebar
      }
    });
  } catch (e) {
    ["research","defense","prosecution","judge","appeals"].forEach(a => {
      if (document.getElementById("status-" + a)?.classList.contains("status-working")) {
        setStatus(a, "error", "Error"); setCardState(a, ""); setPipeStep(a, "");
      }
    });
    showError(e.message.includes("Session expired")
      ? "Session expired — please log in again."
      : "Backend error: " + e.message + " — is the server running on port 8000?");
  } finally {
    setAnalyzeLoading(false);
  }
}

function handleAgentResult(stage, data, inclAppeals) {
  switch (stage) {
    case "research":
      completeAgent("research", renderBullets(data.content || ""));
      activateAgent("defense"); activateAgent("prosecution");
      break;
    case "defense":
      completeAgent("defense", renderBullets(data.content || ""));
      break;
    case "prosecution":
      completeAgent("prosecution", renderBullets(data.content || ""));
      activateAgent("judge");
      break;
    case "judge":
      completeAgent("judge", `<p>${data.reasoning || ""}</p>${data.key_finding ? `<p><b>Key finding:</b> ${data.key_finding}</p>` : ""}`);
      renderVerdict(data.ruling || "Undetermined", data.confidence || 50, data.key_finding || "");
      if (inclAppeals) activateAgent("appeals");
      break;
    case "appeals":
      completeAgent("appeals", "");
      renderAppeals(data);
      break;
  }
}

// ── Appeals Card ───────────────────────────────────────
function renderAppeals(data) {
  const card = $("appealsCard");
  card.style.display = "block";
  card.classList.add("fade-in");

  $("ap-warranted").textContent = data.appeal_warranted ? "Yes" : "No";
  $("ap-warranted").className   = "metric-value " + (data.appeal_warranted ? "guilty" : "not-guilty");
  $("ap-strength").textContent  = Math.round(data.appeal_strength || 0) + "%";
  $("ap-action").textContent    = data.recommended_action || "—";

  const groundsEl = $("ap-grounds");
  const grounds   = data.grounds || [];
  groundsEl.innerHTML = grounds.length
    ? "<ul>" + grounds.map(g => `<li>${escHtml(g)}</li>`).join("") + "</ul>"
    : "<p class='agent-placeholder'>No grounds for appeal identified.</p>";

  const dissentEl = $("ap-dissent");
  dissentEl.textContent = data.dissenting_view || "";
}

// ── Agent Lifecycle ────────────────────────────────────
function activateAgent(agent) {
  setCardState(agent, "active"); setStatus(agent, "working", "Working…");
  setPipeStep(agent, "active"); setSkeleton(agent);
}

function completeAgent(agent, html) {
  setCardState(agent, "done"); setStatus(agent, "done", "Complete");
  setPipeStep(agent, "done"); setAgentBody(agent, html);
}

// ── Clear Session ──────────────────────────────────────
function clearAll() {
  $("caseInput").value = "";
  $("pdfBtn").style.display = "none";
  $("appealsCard").style.display = "none";
  $("currentCaseId").value = "";
  resetUI();
}

// ── Helpers ───────────────────────────────────────────
function escHtml(str) {
  return String(str).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

// ── Init ──────────────────────────────────────────────
(async function loadSystemStatus() {
  try {
    const health = await API.health();
    renderSystemStatus(health);
  } catch {
    renderSystemStatus({});
  }
})();

(async function init() {
  if (API.isLoggedIn()) {
    try {
      await onAuthSuccess();
    } catch {
      API.clearToken();
    }
  } else {
    showAuthModal("login");
  }
})();
