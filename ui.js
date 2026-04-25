/**
 * ui.js
 * All DOM manipulation helpers for the LexAI frontend.
 * Keeps visual state changes isolated from business logic.
 */

// ── Shorthand ──────────────────────────────────────────
const $ = (id) => document.getElementById(id);

// ── Pipeline Step States ───────────────────────────────
/**
 * Set the visual state of a pipeline step.
 * @param {'research'|'defense'|'prosecution'|'judge'} name
 * @param {''|'active'|'done'} state
 */
function setPipeStep(name, state) {
  const el = $('ps-' + name);
  if (!el) return;
  el.className = 'pipe-step' + (state ? ' ' + state : '');
}

// ── Agent Card States ──────────────────────────────────
/**
 * Set the visual state of an agent card.
 * @param {string} agent
 * @param {''|'active'|'done'} state
 */
function setCardState(agent, state) {
  const card = $('card-' + agent);
  if (!card) return;
  card.classList.remove('active', 'done');
  if (state) card.classList.add(state);
}

// ── Status Badge ───────────────────────────────────────
/**
 * Update the status badge on an agent card.
 * @param {string} agent
 * @param {'idle'|'working'|'done'|'error'} state
 * @param {string} label - Display text
 */
function setStatus(agent, state, label) {
  const el = $('status-' + agent);
  if (!el) return;
  el.className = 'agent-status status-' + state;
  el.textContent = label;
}

// ── Skeleton Loader ────────────────────────────────────
/**
 * Replace agent body content with animated skeleton lines.
 * @param {string} agent
 */
function setSkeleton(agent) {
  $('body-' + agent).innerHTML =
    '<div class="skeleton-line"></div>' +
    '<div class="skeleton-line"></div>' +
    '<div class="skeleton-line"></div>' +
    '<div class="skeleton-line"></div>';
}

// ── Content Rendering ──────────────────────────────────
/**
 * Convert bullet-point text (•, -, *) into a <ul> list.
 * Falls back to plain paragraph if no bullets found.
 * @param {string} text
 * @returns {string} HTML string
 */
function renderBullets(text) {
  const lines = text.split('\n').filter((l) => l.trim());
  const items = lines
    .map((l) => l.replace(/^[•\-\*·§]\s*/, '').trim())
    .filter(Boolean);
  if (items.length === 0) return `<p>${text}</p>`;
  return '<ul>' + items.map((i) => `<li>${i}</li>`).join('') + '</ul>';
}

/**
 * Set the body content of an agent card.
 * @param {string} agent
 * @param {string} html
 */
function setAgentBody(agent, html) {
  const el = $('body-' + agent);
  if (!el) return;
  el.innerHTML = html;
  el.classList.add('fade-in');
}

// ── Error Banner ───────────────────────────────────────
/**
 * Show an error message banner and auto-hide after 8s.
 * @param {string} message
 */
function showError(message) {
  const el = $('errorBanner');
  el.textContent = '⚠ ' + message;
  el.style.display = 'block';
  setTimeout(() => (el.style.display = 'none'), 8000);
}

// ── Verdict Metrics ────────────────────────────────────
/**
 * Populate and reveal the verdict metrics panel.
 * @param {string} ruling  - e.g. "Liable", "Not Guilty"
 * @param {number} confidence - 0–100
 * @param {string} keyFinding - one-sentence finding
 */
function renderVerdict(ruling, confidence, keyFinding) {
  // Ruling
  const rulingEl = $('m-ruling');
  rulingEl.textContent = ruling;
  const isGuilty = /guilty|liable/i.test(ruling) && !/not/i.test(ruling);
  const isNotGuilty = /not|insufficient/i.test(ruling);
  rulingEl.className =
    'metric-value ' + (isGuilty ? 'guilty' : isNotGuilty ? 'not-guilty' : 'uncertain');

  // Confidence
  const conf = Math.round(confidence);
  $('m-conf').textContent = conf + '%';
  setTimeout(() => {
    $('confBar').style.width = conf + '%';
  }, 100);

  // Key finding
  $('m-finding').textContent = keyFinding || '—';

  // Show panel
  $('verdictMetrics').style.display = 'grid';
}

// ── Analyze Button ─────────────────────────────────────
function setAnalyzeLoading(isLoading) {
  const btn = $('analyzeBtn');
  btn.disabled = isLoading;
  btn.innerHTML = isLoading
    ? 'Deliberating… <span class="btn-icon">⏳</span>'
    : 'Convene the Court <span class="btn-icon">⚖</span>';
}

// ── Show / Hide Results Area ───────────────────────────
function showResultsArea() {
  $('divider').style.display = 'flex';
  const grid = $('agentsGrid');
  grid.style.display = 'grid';
  grid.classList.add('fade-in');
}

// ── Reset All UI ───────────────────────────────────────
function resetUI() {
  $('errorBanner').style.display = 'none';
  $('divider').style.display = 'none';
  $('agentsGrid').style.display = 'none';
  $('verdictMetrics').style.display = 'none';

  const agents = ['research', 'defense', 'prosecution', 'judge'];

  agents.forEach((a) => {
    setPipeStep(a, '');
    setStatus(a, 'idle', 'Standby');
    setCardState(a, '');
  });

  $('body-research').innerHTML    = '<p class="agent-placeholder">Awaiting case submission to retrieve relevant legal doctrine…</p>';
  $('body-defense').innerHTML     = '<p class="agent-placeholder">Defense arguments will appear here…</p>';
  $('body-prosecution').innerHTML = '<p class="agent-placeholder">Prosecution arguments will appear here…</p>';
  $('body-judge').innerHTML       = '<p class="agent-placeholder">The court is not yet in session…</p>';

  setAnalyzeLoading(false);
}

function renderSystemStatus(health) {
  const agent = health.agent_backend || {};
  const rag = health.rag_backend || {};

  $('statusAgentProvider').textContent = agent.provider || 'Unavailable';
  $('statusAgentModel').textContent = agent.model || '-';
  $('statusRagBackend').textContent = rag.backend || '-';
  $('statusCorpusDocs').textContent = rag.documents || '-';
}
