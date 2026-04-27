const $ = (id) => document.getElementById(id);

function setTextIfExists(id, value) {
  const element = $(id);
  if (element) element.textContent = value;
}

function escHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function nl2html(text) {
  return escHtml(text).replace(/\n/g, "<br>");
}

function getRuntimeSetting(key, fallback) {
  const settings = window.LEXAI_RUNTIME_SETTINGS || {};
  return key in settings ? settings[key] : fallback;
}

function scrollToSection(id) {
  const element = $(id);
  if (element) {
    element.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function showError(message) {
  const banner = $("errorBanner");
  banner.textContent = message;
  banner.style.display = "block";
}

function hideError() {
  $("errorBanner").style.display = "none";
}

function setSidebarActive(key) {
  document.querySelectorAll(".sidebar-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.sidebar === key);
  });
}

function switchResultsTab(tab) {
  document.querySelectorAll(".result-tab").forEach((button) => {
    button.classList.toggle("active", button.dataset.resultTab === tab);
  });
  $("debatePanel").classList.toggle("active", tab === "debate");
  $("evidencePanel").classList.toggle("active", tab === "evidence");
  $("insightsPanel").classList.toggle("active", tab === "insights");
}

function toggleUserActivityPanel(event) {
  if (event) event.stopPropagation();
  const panel = $("userActivityPanel");
  if (!panel) return;
  panel.style.display = panel.style.display === "block" ? "none" : "block";
}

function setAnalyzeLoading(isLoading) {
  const button = $("analyzeBtn");
  button.disabled = isLoading;
  button.textContent = isLoading ? "Analyzing case..." : "Analyze Case";
}

function setLiveStatus(message) {
  $("liveStatus").textContent = message;
}

function setStepState(step, state) {
  const element = $("step-" + step);
  if (!element) return;
  element.classList.remove("pending", "running", "done");
  element.classList.add(state || "pending");
}

function setAgentStatus(agent, label, tone = "neutral") {
  const element = $("status-" + agent);
  if (!element) return;
  element.textContent = label;
  element.style.background =
    tone === "green" ? "rgba(31, 143, 98, 0.12)" :
    tone === "red" ? "rgba(209, 79, 74, 0.12)" :
    tone === "gold" ? "rgba(196, 154, 46, 0.14)" :
    "rgba(243, 246, 251, 1)";
  element.style.color =
    tone === "green" ? "var(--green)" :
    tone === "red" ? "var(--red)" :
    tone === "gold" ? "var(--gold)" :
    "var(--muted)";
}

function setTypingContent(elementId, text, emptyFallback = "Run analysis to see results", speed = getRuntimeSetting("typing_speed_ms", 8)) {
  setStaticContent(elementId, text, emptyFallback);
}

function setStaticContent(elementId, text, emptyFallback = "Run analysis to see results") {
  const element = $(elementId);
  if (!text) {
    element.className = "agent-content empty-state";
    element.textContent = emptyFallback;
    return;
  }
  element.className = "agent-content";
  element.innerHTML = nl2html(text);
}

function resetAnalysisUI() {
  hideError();
  setLiveStatus("Waiting for input");
  ["research", "debate", "scoring", "judge", "appeals"].forEach((step) => setStepState(step, "pending"));
  setAgentStatus("research", "Standby");
  setAgentStatus("defense", "Standby");
  setAgentStatus("prosecution", "Standby");
  setAgentStatus("judge", "Standby");
  setAgentStatus("appeals", "Standby");
  setStaticContent("body-research", "");
  setStaticContent("body-defense", "");
  setStaticContent("body-prosecution", "");
  setStaticContent("body-judge", "");
  setStaticContent("body-appeals", "");
  $("appealsCard").style.display = "none";
  $("verdictRuling").textContent = "-";
  $("verdictConfidence").textContent = "-";
  $("verdictWinner").textContent = "-";
  $("verdictFinding").textContent = "";
  $("confidenceBar").style.width = "0%";
  $("insightConfidence").textContent = "0%";
  $("insightConfidenceBar").style.width = "0%";
  $("defenseScoreMini").textContent = "-";
  $("prosecutionScoreMini").textContent = "-";
  $("defenseCompareBar").style.width = "0%";
  $("prosecutionCompareBar").style.width = "0%";
  $("roundsTimeline").className = "rounds-timeline empty-state";
  $("roundsTimeline").textContent = "Run analysis to see results";
  $("evidenceMeta").textContent = "Run analysis to see results";
  $("evidenceList").className = "evidence-accordion empty-state";
  $("evidenceList").textContent = "Run analysis to see results";
  $("verdictDistribution").className = "css-chart empty-state";
  $("verdictDistribution").textContent = "Run analysis to see results";
}

function renderSystemStatus(health) {
  const agent = health.agent_backend || {};
  const rag = health.rag_backend || {};
  setTextIfExists("statusAgentProvider", agent.provider || "Unavailable");
  setTextIfExists("statusAgentModel", agent.model || "-");
  setTextIfExists("statusRagBackend", rag.backend || "-");
  setTextIfExists("statusCorpusDocs", rag.documents || "-");
}

function renderRoundTimeline(rounds) {
  const container = $("roundsTimeline");
  if (!rounds?.length) {
    container.className = "rounds-timeline empty-state";
    container.textContent = "Run analysis to see results";
    return;
  }

  container.className = "rounds-timeline";
  container.innerHTML = rounds.map((round) => `
    <article class="round-card">
      <div class="round-card-header">
        <div class="round-number">${round.round}</div>
        <div>
          <strong>${escHtml(round.label || `Round ${round.round}`)}</strong>
        </div>
      </div>
      <div class="round-columns">
        <div class="round-column">
          <div class="round-column-label defense">Defense</div>
          <div class="round-column-copy">${nl2html(round.defense || "")}</div>
        </div>
        <div class="round-column">
          <div class="round-column-label prosecution">Prosecution</div>
          <div class="round-column-copy">${nl2html(round.prosecution || "")}</div>
        </div>
      </div>
    </article>
  `).join("");
}

function renderResearch(text, animate = true) {
  setAgentStatus("research", "Complete", "neutral");
  if (animate) setTypingContent("body-research", text);
  else setStaticContent("body-research", text);
}

function renderArgument(agent, text, animate = true) {
  const tone = agent === "defense" ? "green" : "red";
  setAgentStatus(agent, "Complete", tone);
  if (animate) setTypingContent(`body-${agent}`, text);
  else setStaticContent(`body-${agent}`, text);
}

function renderVerdict(verdict, animate = true) {
  setAgentStatus("judge", "Complete", "gold");
  if (animate) setTypingContent("body-judge", `${verdict.reasoning || ""}\n\nCited basis: ${verdict.cited_basis || "Not specified"}`);
  else setStaticContent("body-judge", `${verdict.reasoning || ""}\n\nCited basis: ${verdict.cited_basis || "Not specified"}`);

  $("verdictRuling").textContent = verdict.ruling || "-";
  $("verdictConfidence").textContent = `${Math.round(verdict.confidence || 0)}%`;
  $("verdictWinner").textContent = verdict.winning_side || "-";
  $("verdictFinding").textContent = verdict.key_finding || "";
  const conf = Math.round(verdict.confidence || 0);
  $("confidenceBar").style.width = `${conf}%`;
  $("insightConfidence").textContent = `${conf}%`;
  $("insightConfidenceBar").style.width = `${conf}%`;
}

function renderAppeals(appeals, animate = true) {
  $("appealsCard").style.display = "block";
  setAgentStatus("appeals", "Complete", "gold");
  const content = [
    `Appeal warranted: ${appeals.appeal_warranted ? "Yes" : "No"}`,
    `Recommended action: ${appeals.recommended_action || "-"}`,
    `Appeal strength: ${Math.round(appeals.appeal_strength || 0)}%`,
    `Grounds: ${(appeals.grounds || []).join(", ") || "None identified"}`,
    `Dissenting view: ${appeals.dissenting_view || "-"}`
  ].join("\n\n");
  if (animate) setTypingContent("body-appeals", content);
  else setStaticContent("body-appeals", content);
}

function highlightKeywords(text, keywords) {
  if (!getRuntimeSetting("show_keyword_highlights", true)) {
    return escHtml(text || "");
  }
  let html = escHtml(text || "");
  (keywords || []).slice(0, getRuntimeSetting("evidence_highlight_limit", 8)).forEach((keyword) => {
    if (!keyword) return;
    const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    html = html.replace(new RegExp(`(${escaped})`, "ig"), '<span class="keyword-inline">$1</span>');
  });
  return html;
}

function toggleEvidenceAccordion(index) {
  const item = document.querySelector(`[data-accordion="${index}"]`);
  if (item) item.classList.toggle("open");
}

function renderEvidence(evidence) {
  const documents = evidence?.documents || [];
  $("evidenceMeta").textContent = documents.length
    ? `${documents.length} legal sources / IPC references retrieved`
    : "Run analysis to see results";

  const container = $("evidenceList");
  if (!documents.length) {
    container.className = "evidence-accordion empty-state";
    container.textContent = "Run analysis to see results";
    return;
  }

  container.className = "evidence-accordion";
  container.innerHTML = documents.map((doc, index) => `
    <article class="accordion-item ${index === 0 ? "open" : ""}" data-accordion="${index}">
      <button class="accordion-trigger" onclick="toggleEvidenceAccordion(${index})">
        <span>${escHtml(doc.citation || doc.title || `Source ${index + 1}`)}</span>
        <span>${index === 0 ? "▴" : "▾"}</span>
      </button>
      <div class="accordion-content">
        <p><strong>${escHtml(doc.title || "Untitled Source")}</strong></p>
        <p>${highlightKeywords(doc.content || "", doc.keywords || [])}</p>
      </div>
    </article>
  `).join("");
}

function renderScoring(scoring) {
  const defense = Math.round(scoring?.defense_score || 0);
  const prosecution = Math.round(scoring?.prosecution_score || 0);
  $("defenseScoreMini").textContent = `${defense}%`;
  $("prosecutionScoreMini").textContent = `${prosecution}%`;
  $("defenseCompareBar").style.width = `${defense}%`;
  $("prosecutionCompareBar").style.width = `${prosecution}%`;

  const stronger = scoring?.stronger_side || "balanced";
  $("verdictDistribution").className = "css-chart";
  $("verdictDistribution").innerHTML = `
    <div class="chart-row">
      <span class="chart-label">Defense</span>
      <div class="chart-track"><div class="chart-fill defense-fill" style="width:${defense}%"></div></div>
      <strong>${defense}%</strong>
    </div>
    <div class="chart-row">
      <span class="chart-label">Prosecution</span>
      <div class="chart-track"><div class="chart-fill prosecution-fill" style="width:${prosecution}%"></div></div>
      <strong>${prosecution}%</strong>
    </div>
    <p class="subtle-label" style="margin-top:0.9rem">Stronger side: ${escHtml(stronger)}</p>
  `;
}

function renderHistory(cases) {
  const container = $("historyList");
  if (!cases?.length) {
    container.className = "history-grid empty-state";
    container.textContent = "Run analysis to see results";
    return;
  }

  container.className = "history-grid";
  container.innerHTML = cases.map((item) => `
    <article class="history-card" onclick="loadCase('${item.id}')">
      <div>
        <h3>${escHtml(item.title || "Untitled case")}</h3>
        <p>${escHtml(item.ruling || "Pending")}</p>
      </div>
      <div class="history-actions">
        <strong>${item.confidence ? Math.round(item.confidence) + "%" : "-"}</strong>
        <button class="delete-btn" onclick="deleteCase('${item.id}', event)">Delete</button>
      </div>
    </article>
  `).join("");
}

function renderAnalytics(data) {
  const cards = [
    ["Total Cases", data.total_cases ?? 0],
    ["Completed", data.completed_cases ?? 0],
    ["Avg Confidence", `${Math.round(data.average_confidence || 0)}%`],
    ["Downloads", data.report_downloads ?? 0],
    ["Knowledge Docs", data.knowledge_documents ?? 0],
    ["Model", data.agent_backend?.model || "-"],
  ];

  $("insightsSummary").innerHTML = cards.map(([label, value]) => `
    <div class="metric-tile">
      <span>${escHtml(label)}</span>
      <strong>${escHtml(value)}</strong>
    </div>
  `).join("");

  const recent = data.recent_cases || [];
  $("recentCasesChart").className = "analytics-card";
  $("recentCasesChart").innerHTML = recent.length
    ? `<h3>Recent Cases</h3>${recent.map((item) => `
        <div class="chart-row">
          <span>${escHtml(item.title)}</span>
          <div class="chart-track"><div class="chart-fill" style="width:${Math.max(8, Math.round(item.confidence || 0))}%"></div></div>
          <strong>${Math.round(item.confidence || 0)}%</strong>
        </div>
      `).join("")}`
    : "Run analysis to see results";

  const verdicts = Object.entries(data.verdict_distribution || {});
  $("verdictMetricsCard").className = "analytics-card";
  $("verdictMetricsCard").innerHTML = verdicts.length
    ? `<h3>Verdict Distribution</h3>${verdicts.map(([label, value]) => `
        <div class="chart-row">
          <span>${escHtml(label)}</span>
          <div class="chart-track"><div class="chart-fill" style="width:${Math.max(12, value * 18)}%"></div></div>
          <strong>${escHtml(value)}</strong>
        </div>
      `).join("")}`
    : "Run analysis to see results";

  $("insightsBackendCard").className = "analytics-card";
  $("insightsBackendCard").innerHTML = `
    <h3>Workspace Summary</h3>
    <p class="backend-line">Reasoning mode: ${escHtml(data.system_settings?.reasoning_mode || "multi-agent-rag")}.</p>
    <p class="backend-line">Rule-based shortcuts: ${data.system_settings?.rule_based ? "enabled" : "disabled"}.</p>
    <p class="backend-line">Recent activity events: ${escHtml(data.activity_events ?? 0)}.</p>
  `;
}

function renderActivityLogs(logs) {
  const container = $("activityLogList");
  if (!container) return;
  if (!logs?.length) {
    container.className = "activity-log-list empty-state";
    container.textContent = "No user activity yet";
    return;
  }

  container.className = "activity-log-list";
  container.innerHTML = logs.map((item) => `
    <div class="activity-log-row">
      <div>
        <strong>${escHtml(item.description || item.action)}</strong>
        <div class="history-meta">${escHtml((item.action || "").replaceAll("_", " "))}</div>
      </div>
      <time class="history-meta">${escHtml((item.created_at || "").replace("T", " ").slice(0, 16))}</time>
    </div>
  `).join("");
}

function renderKnowledgeBase(documents) {
  const container = $("knowledgeDocList");
  if (!container) return;
  if (!documents?.length) {
    container.className = "knowledge-doc-list empty-state";
    container.textContent = "No legal documents available";
    return;
  }

  container.className = "knowledge-doc-list";
  container.innerHTML = documents.map((doc) => `
    <article class="knowledge-doc-card">
      <div>
        <strong>${escHtml(doc.title || "Untitled document")}</strong>
        <div class="history-meta">${escHtml(doc.citation || "-")}</div>
      </div>
      <div class="knowledge-doc-actions">
        <button class="secondary-btn compact-btn" onclick="editKnowledgeDocument('${escHtml(doc.id)}')">Edit</button>
        <button class="delete-btn compact-btn" onclick="deleteKnowledgeDocument('${escHtml(doc.id)}')">Delete</button>
      </div>
    </article>
  `).join("");
}

function renderSystemSettings(settings) {
  const note = $("systemModeNote");
  if (!settings) {
    if (note) note.textContent = "Reasoning mode: multi-agent-rag";
    return;
  }
  $("settingDefaultAppeals").checked = !!settings.default_include_appeals;
  $("settingRetrievalDocs").value = settings.retrieval_documents ?? 4;
  $("settingReasoningProfile").value = settings.reasoning_profile || "balanced";
  $("settingHighlightLimit").value = settings.evidence_highlight_limit ?? 8;
  $("settingTypingSpeed").value = settings.typing_speed_ms ?? 8;
  $("settingAutoScroll").checked = !!settings.auto_scroll_results;
  $("settingKeywordHighlights").checked = !!settings.show_keyword_highlights;
  if (note) {
    note.textContent = `Reasoning mode: ${settings.reasoning_mode || "multi-agent-rag"} | Rule based: ${settings.rule_based ? "yes" : "no"}`;
  }
}
