const baseUrlInput = document.getElementById("baseUrl");
const indexUrlInput = document.getElementById("indexUrl");
const arrInput = document.getElementById("arrInput");
const truingInput = document.getElementById("truingInput");
const verdictBtn = document.getElementById("verdictBtn");
const indexSeedBtn = document.getElementById("indexSeedBtn");
const ragFiles = document.getElementById("ragFiles");
const uploadRagBtn = document.getElementById("uploadRagBtn");
const refreshRagBtn = document.getElementById("refreshRagBtn");
const healthBtn = document.getElementById("healthBtn");

const healthStatus = document.getElementById("healthStatus");
const verdictStatus = document.getElementById("verdictStatus");
const ragStatus = document.getElementById("ragStatus");
const analysisSummary = document.getElementById("analysisSummary");
const agentSummary = document.getElementById("agentSummary");
const ragSnippets = document.getElementById("ragSnippets");
const verdictDownload = document.getElementById("verdictDownload");

let latestVerdict = null;

function getBaseUrl() {
  return baseUrlInput.value.trim().replace(/\/+$/, "");
}

function getIndexBaseUrl() {
  const value = indexUrlInput?.value.trim() || "";
  if (!value) return getBaseUrl();
  return value.replace(/\/+$/, "");
}

function setStatus(el, text, isError = false) {
  el.textContent = text;
  el.classList.toggle("muted", !isError);
  el.style.color = isError ? "#b91c1c" : "";
}

function requireBaseUrl(statusEl) {
  const base = getBaseUrl();
  if (!base) {
    setStatus(statusEl, "Set Backend Base URL first.", true);
    throw new Error("Missing Backend Base URL");
  }
  return base;
}

async function testHealth() {
  setStatus(healthStatus, "Checking backend...");
  try {
    const base = requireBaseUrl(healthStatus);
    const response = await fetch(`${base}/`);
    if (!response.ok) {
      throw new Error(`Health check failed (${response.status})`);
    }
    const data = await response.json();
    setStatus(healthStatus, `Connected • ${data.system || "API"} v${data.version || ""}`);
  } catch (error) {
    setStatus(healthStatus, `Connection failed: ${error.message}`, true);
  }
}

async function generateVerdict() {
  const arrFile = arrInput.files[0];
  const truingFile = truingInput.files[0];
  if (!arrFile || !truingFile) {
    setStatus(verdictStatus, "Please select both ARR and Truing-Up PDFs.", true);
    return;
  }

  setStatus(verdictStatus, "Generating verdict via RAG + 4 LLM agents...");
  try {
    const base = requireBaseUrl(verdictStatus);
    const formData = new FormData();
    formData.append("arr_pdf", arrFile);
    formData.append("truing_pdf", truingFile);

    const response = await fetch(`${base}/verdict/`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Verdict failed (${response.status})`);
    }

    latestVerdict = await response.json();
    renderVerdict(latestVerdict);
    setStatus(verdictStatus, "Verdict generated.");
  } catch (error) {
    setStatus(verdictStatus, `Verdict failed: ${error.message}`, true);
  }
}

function renderVerdict(data) {
  analysisSummary.textContent = "";
  const summaryRow = document.createElement("div");
  const summaryLabel = document.createElement("strong");
  summaryLabel.textContent = "Summary:";
  summaryRow.appendChild(summaryLabel);
  summaryRow.append(` ${data.summary || "No summary"}`);
  analysisSummary.appendChild(summaryRow);

  const approvedRow = document.createElement("div");
  const approvedLabel = document.createElement("strong");
  approvedLabel.textContent = "Approved:";
  approvedRow.appendChild(approvedLabel);
  approvedRow.append(` ${(data.approved_items || []).length}`);
  analysisSummary.appendChild(approvedRow);

  const disallowedRow = document.createElement("div");
  const disallowedLabel = document.createElement("strong");
  disallowedLabel.textContent = "Disallowed:";
  disallowedRow.appendChild(disallowedLabel);
  disallowedRow.append(` ${(data.disallowed_items || []).length}`);
  analysisSummary.appendChild(disallowedRow);

  const conditionsRow = document.createElement("div");
  const conditionsLabel = document.createElement("strong");
  conditionsLabel.textContent = "Conditions:";
  conditionsRow.appendChild(conditionsLabel);
  conditionsRow.append(` ${(data.conditions || []).length}`);
  analysisSummary.appendChild(conditionsRow);
  analysisSummary.classList.remove("muted");

  agentSummary.textContent = "";
  const agentRows = [
    ["Legal Brain", data.agent_outputs?.legal_brain ? "✓" : "-"],
    ["Forensic Auditor", data.agent_outputs?.forensic_auditor ? "✓" : "-"],
    ["Technical Validator", data.agent_outputs?.technical_validator ? "✓" : "-"],
    ["CRO Verdict", data.agent_outputs?.chief_regulatory_officer ? "✓" : "-"],
  ];
  agentRows.forEach(([label, value]) => {
    const row = document.createElement("div");
    const strong = document.createElement("strong");
    strong.textContent = `${label}:`;
    row.appendChild(strong);
    row.append(` ${value}`);
    agentSummary.appendChild(row);
  });
  agentSummary.classList.remove("muted");

  verdictDownload.href = `${getBaseUrl()}${data.verdict_pdf_url}`;
  verdictDownload.classList.remove("muted");

  renderRagSnippets(data.rag_snippets || []);
}

function renderRagSnippets(snippets) {
  if (!snippets.length) {
    ragSnippets.textContent = "No RAG snippets available.";
    ragSnippets.classList.add("muted");
    return;
  }
  ragSnippets.textContent = "";
  snippets.forEach((s) => {
    const card = document.createElement("div");
    card.className = "rag-card";

    const meta = document.createElement("div");
    const strong = document.createElement("strong");
    strong.textContent = s.source || "Unknown";
    meta.appendChild(strong);
    if (s.page) {
      meta.append(` • Page ${s.page}`);
    }

    const body = document.createElement("div");
    body.textContent = s.text || "";

    card.appendChild(meta);
    card.appendChild(body);
    ragSnippets.appendChild(card);
  });
  ragSnippets.classList.remove("muted");
}

async function indexSeed() {
  setStatus(ragStatus, "Indexing seed folder...");
  try {
    requireBaseUrl(ragStatus);
    const indexBase = getIndexBaseUrl();
    if (!indexBase) {
      setStatus(ragStatus, "Set Index Service URL first.", true);
      return;
    }
    const response = await fetch(`${indexBase}/rag/index-seed`, { method: "POST" });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Index failed (${response.status})`);
    }
    const data = await response.json();
    setStatus(ragStatus, `Indexed ${data.indexed_chunks} chunks from ${data.sources.length} sources.`);
    if (indexBase !== getBaseUrl()) {
      await refreshRag();
    }
  } catch (error) {
    setStatus(ragStatus, `RAG index failed: ${error.message}`, true);
  }
}

async function refreshRag() {
  setStatus(ragStatus, "Refreshing backend index...");
  try {
    const base = requireBaseUrl(ragStatus);
    const response = await fetch(`${base}/rag/refresh`, { method: "POST" });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Refresh failed (${response.status})`);
    }
    const data = await response.json();
    setStatus(ragStatus, `Backend refreshed (${data.indexed_chunks} chunks).`);
  } catch (error) {
    setStatus(ragStatus, `RAG refresh failed: ${error.message}`, true);
  }
}

async function uploadRag() {
  const files = ragFiles.files;
  if (!files.length) {
    setStatus(ragStatus, "Select files to upload.", true);
    return;
  }
  setStatus(ragStatus, "Uploading and indexing...");
  try {
    requireBaseUrl(ragStatus);
    const formData = new FormData();
    Array.from(files).forEach((f) => formData.append("files", f));
    const indexBase = getIndexBaseUrl();
    if (!indexBase) {
      setStatus(ragStatus, "Set Index Service URL first.", true);
      return;
    }
    const response = await fetch(`${indexBase}/rag/upload`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Upload failed (${response.status})`);
    }
    const data = await response.json();
    setStatus(ragStatus, `Uploaded & indexed ${data.indexed_chunks} chunks.`);
    if (indexBase !== getBaseUrl()) {
      await refreshRag();
    }
  } catch (error) {
    setStatus(ragStatus, `RAG upload failed: ${error.message}`, true);
  }
}

healthBtn.addEventListener("click", testHealth);
verdictBtn.addEventListener("click", generateVerdict);
indexSeedBtn.addEventListener("click", indexSeed);
uploadRagBtn.addEventListener("click", uploadRag);
refreshRagBtn.addEventListener("click", refreshRag);
