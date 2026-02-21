# [Purpose] Lightweight RAG indexing and retrieval service
# [Source] User defined - uses local PDFs/MD/TXT for retrieval
# [Why] Enables regulation-aware answers without external vector DB

# [Library] json - Persist index to disk
# [Why] Simple, portable storage format
import json

# [Library] math - For BM25 scoring
# [Why] Needed for logarithms and normalization
import math

# [Library] os - Filesystem operations
# [Why] Enumerate documents and manage storage
import os

# [Library] re - Tokenization and cleanup
# [Why] Simple text normalization
import re

# [Library] pathlib - Path utilities
# [Why] Safer path handling
from pathlib import Path

# [Library] typing - Type hints
# [Why] Improves clarity and IDE support
from typing import Dict, List, Any, Tuple

# [Library] pdfplumber - PDF text extraction
# [Why] Extract text from regulatory PDFs
import pdfplumber

# [User Defined] Import logger
# [Source] src/utils/logger.py
# [Why] Trace indexing and retrieval
from src.utils.logger import get_logger

# [User Defined] Get logger instance
logger = get_logger(__name__)


# [User Defined] Tokenizer for RAG
# [Source] Simple regex tokenizer
# [Why] Lightweight, dependency-free
def tokenize(text: str) -> List[str]:
    """
    [Purpose] Tokenize text into lowercase word tokens
    [Why] Supports BM25 retrieval
    """
    return re.findall(r"[a-z0-9]+", text.lower())


# [User Defined] Chunking function
# [Source] User defined chunking
# [Why] Improves retrieval granularity
def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 150) -> List[str]:
    """
    [Purpose] Split text into overlapping chunks
    [Why] Prevents cutting key references in the middle
    """
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
        if start < 0:
            start = 0
        if start >= text_len:
            break
    return chunks


class RagIndex:
    """
    [Purpose] Minimal BM25 index over local chunks
    [Why] Avoids external vector DB while enabling retrieval
    """

    def __init__(self, chunks: List[Dict[str, Any]]):
        self.chunks = chunks
        self.doc_freq: Dict[str, int] = {}
        self.doc_tokens: List[List[str]] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_len = 0.0
        self._build()

    def _build(self) -> None:
        logger.info("Building RAG index in memory")
        self.doc_tokens = []
        self.doc_lengths = []
        self.doc_freq = {}

        for chunk in self.chunks:
            tokens = tokenize(chunk["text"])
            self.doc_tokens.append(tokens)
            self.doc_lengths.append(len(tokens))
            unique_tokens = set(tokens)
            for t in unique_tokens:
                self.doc_freq[t] = self.doc_freq.get(t, 0) + 1

        total_len = sum(self.doc_lengths) if self.doc_lengths else 0
        self.avg_doc_len = total_len / len(self.doc_lengths) if self.doc_lengths else 0.0
        logger.info(f"Indexed {len(self.chunks)} chunks")

    def _bm25_score(self, query_tokens: List[str], doc_idx: int, k1: float = 1.5, b: float = 0.75) -> float:
        tokens = self.doc_tokens[doc_idx]
        if not tokens:
            return 0.0
        freq: Dict[str, int] = {}
        for t in tokens:
            freq[t] = freq.get(t, 0) + 1
        score = 0.0
        doc_len = self.doc_lengths[doc_idx]
        for t in query_tokens:
            if t not in freq:
                continue
            df = self.doc_freq.get(t, 1)
            idf = math.log(1 + (len(self.chunks) - df + 0.5) / (df + 0.5))
            tf = freq[t]
            denom = tf + k1 * (1 - b + b * (doc_len / (self.avg_doc_len or 1.0)))
            score += idf * (tf * (k1 + 1) / denom)
        return score

    def search(self, query: str, top_k: int = 6) -> List[Dict[str, Any]]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        scored: List[Tuple[int, float]] = []
        for i in range(len(self.chunks)):
            scored.append((i, self._bm25_score(query_tokens, i)))
        scored.sort(key=lambda x: x[1], reverse=True)
        results = []
        for idx, score in scored[:top_k]:
            if score <= 0:
                continue
            chunk = self.chunks[idx].copy()
            chunk["score"] = round(score, 4)
            results.append(chunk)
        return results


def extract_text_from_pdf(path: Path) -> List[Dict[str, Any]]:
    """
    [Purpose] Extract text per page from PDF
    [Why] Enables chunking with page metadata
    """
    pages = []
    with pdfplumber.open(path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            text = text.strip()
            if text:
                pages.append({"page": page_num, "text": text})
    return pages


def build_chunks_from_dir(directory: Path) -> List[Dict[str, Any]]:
    """
    [Purpose] Build chunks from PDFs and text files
    [Why] Indexes regulation references for retrieval
    """
    chunks: List[Dict[str, Any]] = []
    for path in sorted(directory.rglob("*")):
        if path.is_dir():
            continue
        ext = path.suffix.lower()
        if ext not in {".pdf", ".md", ".txt"}:
            continue
        logger.info(f"Indexing source: {path.name}")
        if ext == ".pdf":
            pages = extract_text_from_pdf(path)
            for page in pages:
                for i, chunk in enumerate(chunk_text(page["text"])):
                    chunks.append({
                        "id": f"{path.name}-p{page['page']}-c{i}",
                        "source": path.name,
                        "page": page["page"],
                        "text": chunk
                    })
        else:
            text = path.read_text(errors="ignore")
            for i, chunk in enumerate(chunk_text(text)):
                chunks.append({
                    "id": f"{path.name}-c{i}",
                    "source": path.name,
                    "page": None,
                    "text": chunk
                })
    return chunks


def save_index(chunks: List[Dict[str, Any]], index_path: Path) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"chunks": chunks}
    index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    logger.info(f"Saved RAG index to {index_path}")


def load_index(index_path: Path) -> RagIndex:
    data = json.loads(index_path.read_text())
    return RagIndex(data.get("chunks", []))
