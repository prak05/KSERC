import { getDocument } from "pdfjs-dist/legacy/build/pdf.mjs";

type Env = {
  RAG_BUCKET: R2Bucket;
  RAG_AUTH_TOKEN?: string;
};

type RagChunk = {
  id: string;
  source: string;
  page: number | null;
  text: string;
};

const CHUNK_SIZE = 1200;
const CHUNK_OVERLAP = 150;

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function unauthorized(): Response {
  return jsonResponse({ error: "unauthorized" }, 401);
}

function checkAuth(request: Request, env: Env): boolean {
  if (!env.RAG_AUTH_TOKEN) return true;
  const header = request.headers.get("authorization") || "";
  return header === `Bearer ${env.RAG_AUTH_TOKEN}`;
}

function chunkText(text: string): string[] {
  const chunks: string[] = [];
  let start = 0;
  while (start < text.length) {
    const end = Math.min(start + CHUNK_SIZE, text.length);
    const chunk = text.slice(start, end).trim();
    if (chunk) chunks.push(chunk);
    start = end - CHUNK_OVERLAP;
    if (start < 0) start = 0;
    if (start >= text.length) break;
  }
  return chunks;
}

async function extractPdfPages(buffer: ArrayBuffer): Promise<Array<{ page: number; text: string }>> {
  const loadingTask = getDocument({
    data: new Uint8Array(buffer),
    disableWorker: true,
  });
  const pdf = await loadingTask.promise;
  const pages: Array<{ page: number; text: string }> = [];
  for (let pageNum = 1; pageNum <= pdf.numPages; pageNum += 1) {
    const page = await pdf.getPage(pageNum);
    const content = await page.getTextContent();
    const text = content.items
      .map((item: any) => (typeof item.str === "string" ? item.str : ""))
      .join(" ")
      .replace(/\s+/g, " ")
      .trim();
    if (text) pages.push({ page: pageNum, text });
  }
  return pages;
}

function addTextChunks(
  chunks: RagChunk[],
  source: string,
  page: number | null,
  text: string
): void {
  const parts = chunkText(text);
  parts.forEach((chunk, idx) => {
    chunks.push({
      id: `${source}${page ? `-p${page}` : ""}-c${idx}`,
      source,
      page,
      text: chunk,
    });
  });
}

async function buildChunksFromBuffer(name: string, buffer: ArrayBuffer): Promise<RagChunk[]> {
  const ext = name.split(".").pop()?.toLowerCase() || "";
  const chunks: RagChunk[] = [];
  if (ext === "pdf") {
    const pages = await extractPdfPages(buffer);
    pages.forEach((p) => addTextChunks(chunks, name, p.page, p.text));
    return chunks;
  }
  if (ext === "md" || ext === "txt") {
    const text = new TextDecoder().decode(buffer).trim();
    if (text) addTextChunks(chunks, name, null, text);
    return chunks;
  }
  return chunks;
}

async function listSeedObjects(env: Env): Promise<R2Object[]> {
  const objects: R2Object[] = [];
  let cursor: string | undefined = undefined;
  while (true) {
    const result = await env.RAG_BUCKET.list({
      prefix: "rag/seed/",
      cursor,
    });
    objects.push(...result.objects);
    if (!result.truncated) break;
    cursor = result.cursor;
  }
  return objects;
}

async function saveIndex(env: Env, chunks: RagChunk[]): Promise<void> {
  const payload = JSON.stringify({ chunks });
  await env.RAG_BUCKET.put("rag/index.json", payload, {
    httpMetadata: { contentType: "application/json" },
  });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (!checkAuth(request, env)) return unauthorized();

    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/rag/index") {
      const obj = await env.RAG_BUCKET.get("rag/index.json");
      if (!obj) return jsonResponse({ error: "index_not_found" }, 404);
      return new Response(obj.body, {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }

    if (request.method === "POST" && url.pathname === "/rag/index-seed") {
      const objects = await listSeedObjects(env);
      if (!objects.length) {
        return jsonResponse({ status: "empty", indexed_chunks: 0, sources: [] }, 200);
      }
      const chunks: RagChunk[] = [];
      for (const obj of objects) {
        const name = obj.key.replace("rag/seed/", "");
        const file = await env.RAG_BUCKET.get(obj.key);
        if (!file) continue;
        const buffer = await file.arrayBuffer();
        const fileChunks = await buildChunksFromBuffer(name, buffer);
        chunks.push(...fileChunks);
      }
      await saveIndex(env, chunks);
      const sources = Array.from(new Set(chunks.map((c) => c.source))).sort();
      return jsonResponse({
        status: "indexed",
        indexed_chunks: chunks.length,
        sources,
      });
    }

    if (request.method === "POST" && url.pathname === "/rag/upload") {
      const form = await request.formData();
      const files = form.getAll("files").filter((f) => f instanceof File) as File[];
      if (!files.length) {
        return jsonResponse({ error: "no_files" }, 400);
      }
      const chunks: RagChunk[] = [];
      const timestamp = Date.now();
      for (const file of files) {
        const buffer = await file.arrayBuffer();
        const safeName = file.name || `upload-${timestamp}`;
        const storageKey = `rag/uploads/${timestamp}-${safeName}`;
        await env.RAG_BUCKET.put(storageKey, buffer);
        const fileChunks = await buildChunksFromBuffer(safeName, buffer);
        chunks.push(...fileChunks);
      }
      await saveIndex(env, chunks);
      const sources = Array.from(new Set(chunks.map((c) => c.source))).sort();
      return jsonResponse({
        status: "uploaded_and_indexed",
        indexed_chunks: chunks.length,
        sources,
      });
    }

    if (request.method === "GET" && url.pathname === "/health") {
      return jsonResponse({ status: "ok" });
    }

    return jsonResponse({ error: "not_found" }, 404);
  },
};
