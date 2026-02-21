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
  return baseUrlInput.value.replace(/\/+$/, "");
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

async function testHealth() {
  setStatus(healthStatus, "Checking backend...");
  try {
    const response = await fetch(`${getBaseUrl()}/`);
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
    const formData = new FormData();
    formData.append("arr_pdf", arrFile);
    formData.append("truing_pdf", truingFile);

    const response = await fetch(`${getBaseUrl()}/verdict/`, {
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
  analysisSummary.innerHTML = `
    <div><strong>Summary:</strong> ${data.summary || "No summary"}</div>
    <div><strong>Approved:</strong> ${(data.approved_items || []).length}</div>
    <div><strong>Disallowed:</strong> ${(data.disallowed_items || []).length}</div>
    <div><strong>Conditions:</strong> ${(data.conditions || []).length}</div>
  `;
  analysisSummary.classList.remove("muted");

  agentSummary.innerHTML = `
    <div><strong>Legal Brain:</strong> ${data.agent_outputs?.legal_brain ? "✓" : "-"}</div>
    <div><strong>Forensic Auditor:</strong> ${data.agent_outputs?.forensic_auditor ? "✓" : "-"}</div>
    <div><strong>Technical Validator:</strong> ${data.agent_outputs?.technical_validator ? "✓" : "-"}</div>
    <div><strong>CRO Verdict:</strong> ${data.agent_outputs?.chief_regulatory_officer ? "✓" : "-"}</div>
  `;
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
  ragSnippets.innerHTML = snippets
    .map(
      (s) => `
      <div class="rag-card">
        <div><strong>${s.source}</strong> ${s.page ? `• Page ${s.page}` : ""}</div>
        <div>${s.text}</div>
      </div>`
    )
    .join("");
  ragSnippets.classList.remove("muted");
}

async function indexSeed() {
  setStatus(ragStatus, "Indexing seed folder...");
  try {
    const indexBase = getIndexBaseUrl();
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
    const response = await fetch(`${getBaseUrl()}/rag/refresh`, { method: "POST" });
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
    const formData = new FormData();
    Array.from(files).forEach((f) => formData.append("files", f));
    const indexBase = getIndexBaseUrl();
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
