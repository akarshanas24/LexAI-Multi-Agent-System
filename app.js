const state = {
  history: [],
  rounds: [],
  activeCaseId: "",
  activityLogs: [],
  knowledgeDocuments: [],
  systemSettings: null,
};

function showAuthModal(tab = "login") {
  $("authModal").style.display = "grid";
  switchAuthTab(tab);
}

function hideAuthModal() {
  $("authModal").style.display = "none";
  $("authError").textContent = "";
}

function switchAuthTab(tab) {
  $("loginTab").style.display = tab === "login" ? "block" : "none";
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
  if (!username || !password) {
    $("authError").textContent = "Fill in all fields.";
    return;
  }
  const passwordError = validatePasswordLength(password);
  if (passwordError) {
    $("authError").textContent = passwordError;
    return;
  }

  try {
    await API.login(username, password);
    hideAuthModal();
    await onAuthSuccess();
  } catch (error) {
    $("authError").textContent = error.message;
  }
}

async function doRegister() {
  const username = $("regUsername").value.trim();
  const email = $("regEmail").value.trim();
  const password = $("regPassword").value;
  if (!username || !email || !password) {
    $("authError").textContent = "Fill in all fields.";
    return;
  }
  const passwordError = validatePasswordLength(password);
  if (passwordError) {
    $("authError").textContent = passwordError;
    return;
  }

  try {
    await API.register(username, email, password);
    await API.login(username, password);
    hideAuthModal();
    await onAuthSuccess();
  } catch (error) {
    $("authError").textContent = error.message;
  }
}

async function onAuthSuccess() {
  const me = await API.getMe();
  $("userInfo").textContent = me.username;
  $("userActivityToggle").textContent = (me.username || "L").trim().charAt(0).toUpperCase() || "L";
  $("userBar").style.display = "flex";
  $("authPrompt").style.display = "none";
  await Promise.all([
    loadHistory(),
    loadAnalytics(),
    loadActivityLogs(),
    loadKnowledgeBase(),
    loadSystemSettings(),
  ]);
}

function doLogout() {
  API.clearToken();
  $("userBar").style.display = "none";
  $("authPrompt").style.display = "inline-flex";
  $("userActivityPanel").style.display = "none";
  state.history = [];
  state.activeCaseId = "";
  state.activityLogs = [];
  state.knowledgeDocuments = [];
  state.systemSettings = null;
  renderHistory([]);
  renderActivityLogs([]);
  renderKnowledgeBase([]);
  renderSystemSettings(null);
  resetAnalysisUI();
  showAuthModal("login");
}

async function loadHistory() {
  if (!API.isLoggedIn()) return;
  const payload = await API.getCases();
  state.history = payload.cases || [];
  applyHistoryFilters();
}

function applyHistoryFilters() {
  const query = $("historySearch").value.trim().toLowerCase();
  const filter = $("historyFilter").value;
  const filtered = state.history.filter((item) => {
    const title = (item.title || "").toLowerCase();
    const ruling = (item.ruling || "").toLowerCase();
    const matchesQuery = !query || title.includes(query) || ruling.includes(query);
    const matchesFilter =
      filter === "all" ||
      (filter === "liable" && (ruling.includes("liable") || ruling.includes("guilty"))) ||
      (filter === "not" && ruling.includes("not")) ||
      (filter === "pending" && !item.ruling);
    return matchesQuery && matchesFilter;
  });
  renderHistory(filtered);
}

async function loadAnalytics() {
  if (!API.isLoggedIn()) return;
  const analytics = await API.getAnalytics();
  renderAnalytics(analytics);
}

async function loadActivityLogs() {
  if (!API.isLoggedIn()) return;
  const payload = await API.getActivityLogs(40);
  state.activityLogs = payload.logs || [];
  renderActivityLogs(state.activityLogs);
}

async function loadKnowledgeBase() {
  if (!API.isLoggedIn()) return;
  const payload = await API.getKnowledgeDocuments();
  state.knowledgeDocuments = payload.documents || [];
  renderKnowledgeBase(state.knowledgeDocuments);
}

function applyRuntimeSettings(settings) {
  state.systemSettings = settings;
  window.LEXAI_RUNTIME_SETTINGS = settings || {};
  if (!state.activeCaseId && settings) {
    $("appealsToggle").checked = !!settings.default_include_appeals;
  }
}

async function loadSystemSettings() {
  if (!API.isLoggedIn()) return;
  const settings = await API.getSystemSettings();
  applyRuntimeSettings(settings);
  renderSystemSettings(settings);
}

function markDebateRunning() {
  setStepState("debate", "running");
  setAgentStatus("defense", "Running");
  setAgentStatus("prosecution", "Running");
}

async function analyzeCase() {
  if (!API.isLoggedIn()) {
    showAuthModal("login");
    return;
  }

  const caseDescription = $("caseInput").value.trim();
  if (!caseDescription) {
    showError("Please enter a case description before analysis.");
    return;
  }

  const payload = {
    title: $("caseTitle").value.trim() || null,
    case_description: caseDescription,
    include_appeals: $("appealsToggle").checked,
  };

  resetAnalysisUI();
  hideError();
  switchResultsTab("debate");
  setSidebarActive("analyze");
  setAnalyzeLoading(true);
  setLiveStatus("Analyzing case...");
  setStepState("research", "running");
  setAgentStatus("research", "Running");

  state.rounds = [];
  state.activeCaseId = "";

  try {
    await API.analyzeStream(payload, (stage, data) => {
      if (stage === "research") {
        renderResearch(data.content || "", true);
        setStepState("research", "done");
        markDebateRunning();
        setLiveStatus("Generating multi-agent debate...");
      } else if (stage === "evidence") {
        renderEvidence(data);
      } else if (stage === "round") {
        state.rounds.push(data);
        renderRoundTimeline(state.rounds);
      } else if (stage === "defense") {
        renderArgument("defense", data.content || "", true);
      } else if (stage === "prosecution") {
        renderArgument("prosecution", data.content || "", true);
        setStepState("debate", "done");
        setStepState("scoring", "running");
        setLiveStatus("Scoring defense vs prosecution...");
      } else if (stage === "scoring") {
        renderScoring(data);
        setStepState("scoring", "done");
        setStepState("judge", "running");
        setAgentStatus("judge", "Running");
        setLiveStatus("Generating explainable verdict...");
      } else if (stage === "judge") {
        renderVerdict(data, true);
        setStepState("judge", "done");
        if ($("appealsToggle").checked) {
          setStepState("appeals", "running");
          setAgentStatus("appeals", "Running");
          setLiveStatus("Running appeals review...");
        } else {
          setLiveStatus("Analysis complete.");
        }
      } else if (stage === "appeals") {
        renderAppeals(data, true);
        setStepState("appeals", "done");
        setLiveStatus("Analysis complete.");
      } else if (stage === "complete") {
        state.activeCaseId = data.case_id;
        $("pdfBtn").style.display = "inline-flex";
        loadHistory();
        loadAnalytics();
        loadActivityLogs();
      }
    });
  } catch (error) {
    showError(error.message);
    setLiveStatus("Analysis failed.");
  } finally {
    setAnalyzeLoading(false);
  }
}

async function loadCase(caseId) {
  try {
    const caseData = await API.getCase(caseId);
    state.activeCaseId = caseId;
    state.rounds = caseData.rounds || [];
    $("caseTitle").value = caseData.title || "";
    $("caseInput").value = caseData.case_description || "";
    $("appealsToggle").checked = !!caseData.appeals;
    $("pdfBtn").style.display = "inline-flex";

    resetAnalysisUI();
    switchResultsTab("debate");
    setSidebarActive("analyze");
    renderResearch(caseData.research?.content || "", false);
    renderArgument("defense", caseData.defense?.content || "", false);
    renderArgument("prosecution", caseData.prosecution?.content || "", false);
    renderRoundTimeline(state.rounds);
    renderEvidence(caseData.evidence || { documents: [] });
    renderScoring(caseData.scoring || {});
    if (caseData.verdict) {
      renderVerdict(caseData.verdict, false);
    }
    if (caseData.appeals) {
      renderAppeals(caseData.appeals, false);
      setStepState("appeals", "done");
    }

    setStepState("research", "done");
    setStepState("debate", "done");
    setStepState("scoring", "done");
    setStepState("judge", "done");
    setLiveStatus("Loaded saved case.");
    loadActivityLogs();
    scrollToSection("resultsSection");
  } catch (error) {
    showError(`Could not load case: ${error.message}`);
  }
}

async function deleteCase(caseId, event) {
  event.stopPropagation();
  try {
    await API.deleteCase(caseId);
    if (state.activeCaseId === caseId) {
      clearAll();
    }
    await Promise.all([loadHistory(), loadAnalytics(), loadActivityLogs()]);
  } catch (error) {
    showError(`Delete failed: ${error.message}`);
  }
}

async function downloadPDF() {
  if (!state.activeCaseId) {
    showError("Analyze or load a case before exporting.");
    return;
  }
  try {
    await API.downloadPDF(state.activeCaseId);
    await Promise.all([loadActivityLogs(), loadAnalytics()]);
  } catch (error) {
    showError(`PDF export failed: ${error.message}`);
  }
}

function editKnowledgeDocument(docId) {
  const doc = state.knowledgeDocuments.find((item) => item.id === docId);
  if (!doc) return;
  $("knowledgeDocId").value = doc.id || "";
  $("knowledgeTitle").value = doc.title || "";
  $("knowledgeCitation").value = doc.citation || "";
  $("knowledgeSource").value = doc.source || "";
  $("knowledgeKeywords").value = (doc.keywords || []).join(", ");
  $("knowledgeContent").value = doc.content || "";
}

function resetKnowledgeForm() {
  $("knowledgeDocId").value = "";
  $("knowledgeTitle").value = "";
  $("knowledgeCitation").value = "";
  $("knowledgeSource").value = "";
  $("knowledgeKeywords").value = "";
  $("knowledgeContent").value = "";
}

async function saveKnowledgeDocument() {
  try {
    const payload = {
      id: $("knowledgeDocId").value.trim() || undefined,
      title: $("knowledgeTitle").value.trim(),
      citation: $("knowledgeCitation").value.trim(),
      source: $("knowledgeSource").value.trim() || undefined,
      keywords: $("knowledgeKeywords").value.split(",").map((item) => item.trim()).filter(Boolean),
      content: $("knowledgeContent").value.trim(),
    };
    await API.saveKnowledgeDocument(payload);
    resetKnowledgeForm();
    await Promise.all([loadKnowledgeBase(), loadActivityLogs(), loadAnalytics()]);
  } catch (error) {
    showError(`Knowledge save failed: ${error.message}`);
  }
}

async function deleteKnowledgeDocument(docId) {
  try {
    await API.deleteKnowledgeDocument(docId);
    resetKnowledgeForm();
    await Promise.all([loadKnowledgeBase(), loadActivityLogs(), loadAnalytics()]);
  } catch (error) {
    showError(`Knowledge delete failed: ${error.message}`);
  }
}

async function saveSystemSettings() {
  try {
    const payload = {
      default_include_appeals: $("settingDefaultAppeals").checked,
      retrieval_documents: Number($("settingRetrievalDocs").value),
      reasoning_profile: $("settingReasoningProfile").value,
      evidence_highlight_limit: Number($("settingHighlightLimit").value),
      typing_speed_ms: Number($("settingTypingSpeed").value),
      auto_scroll_results: $("settingAutoScroll").checked,
      show_keyword_highlights: $("settingKeywordHighlights").checked,
    };
    const settings = await API.updateSystemSettings(payload);
    applyRuntimeSettings(settings);
    renderSystemSettings(settings);
    await Promise.all([loadActivityLogs(), loadAnalytics()]);
  } catch (error) {
    showError(`Settings update failed: ${error.message}`);
  }
}

function clearAll() {
  $("caseTitle").value = "";
  $("caseInput").value = "";
  $("appealsToggle").checked = !!state.systemSettings?.default_include_appeals;
  $("pdfBtn").style.display = "none";
  state.rounds = [];
  state.activeCaseId = "";
  resetAnalysisUI();
}

document.addEventListener("click", (event) => {
  const panel = $("userActivityPanel");
  const toggle = $("userActivityToggle");
  if (!panel || !toggle) return;
  if (panel.style.display !== "block") return;
  if (panel.contains(event.target) || toggle.contains(event.target)) return;
  panel.style.display = "none";
});

(async function init() {
  resetAnalysisUI();
  try {
    const health = await API.health();
    renderSystemStatus(health);
  } catch {}

  if (API.isLoggedIn()) {
    try {
      await onAuthSuccess();
    } catch {
      API.clearToken();
      showAuthModal("login");
    }
  } else {
    showAuthModal("login");
  }
})();
