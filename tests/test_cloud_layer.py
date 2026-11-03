"""Tests for the cloud layer: document store, LLM gateway helpers, regulation retrieval."""

import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture()
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("CLOUD", "local")
    monkeypatch.setenv("LOCAL_DB_PATH", str(tmp_path / "store.sqlite3"))
    from src.cloud import docstore, settings

    importlib.reload(settings)
    docstore._client = None
    yield docstore.client()
    docstore._client = None


def test_docstore_set_get_merge_update(store):
    ref = store.collection("analyses").document("a1")
    assert not ref.get().exists
    ref.set({"status": "RUNNING", "progress_log": []})
    ref.set({"status": "DONE"}, merge=True)
    ref.update({"progress_log": ["x"]})
    snap = ref.get()
    assert snap.exists and snap.to_dict() == {"status": "DONE", "progress_log": ["x"]}
    ref.delete()
    assert not ref.get().exists


def test_docstore_subcollections_where_order_limit(store):
    years = store.collection("myt_norms").document("Infopark").collection("years")
    for fy in ("2022-23", "2024-25", "2023-24"):
        years.document(fy).set({"financial_year": fy, "licensee": "Infopark"})
    store.collection("myt_norms").document("KDHP").collection("years").document("2024-25").set({"x": 1})

    assert {s.id for s in years.stream()} == {"2022-23", "2023-24", "2024-25"}
    latest = list(years.where("licensee", "==", "Infopark")
                  .order_by("financial_year", direction="DESCENDING").limit(2).stream())
    assert [s.id for s in latest] == ["2024-25", "2023-24"]


def test_update_missing_document_raises(store):
    with pytest.raises(KeyError):
        store.collection("analyses").document("nope").update({"a": 1})


def test_extract_json_text_strips_fences_and_prose():
    from src.cloud.llm import extract_json_text

    assert extract_json_text('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert extract_json_text('Here you go:\n{"a": [1, 2]}\nThanks') == '{"a": [1, 2]}'
    assert extract_json_text("[1, 2]") == "[1, 2]"


def test_bedrock_blocks_put_documents_before_text():
    from src.cloud.llm import _bedrock_blocks
    from src.cloud.llm_types import Part

    blocks = _bedrock_blocks([Part.from_text("Question"), Part.from_bytes(b"%PDF-1.4 tiny", "application/pdf"),
                              Part.from_bytes(b"\x89PNG", "image/png")])
    assert [b["type"] for b in blocks] == ["document", "image", "text"]
    assert blocks[0]["source"]["media_type"] == "application/pdf"


def test_offline_provider_returns_empty_json(monkeypatch):
    from src.cloud import llm, settings

    monkeypatch.setattr(settings, "LLM_PROVIDER", "offline")
    assert llm.generate("anything") == "{}"
    assert llm.generate("anything", response_mime_type="text/plain") == ""


def test_regulation_retrieval_ranks_relevant_passage(store):
    from src.rag import regulation_store as rs

    rs._index_cache.clear()
    col = store.collection(rs.COLLECTION)
    col.document("reg").set({"filename": "Tariff Regulations.pdf", "category": "regulations",
                             "content": "Clause 27. Return on equity shall be allowed at 14 percent."})
    col.document("myt").set({"filename": "MYT Order.pdf", "category": "myt_orders",
                             "content": "Distribution loss target for the control period is 4 percent."})
    ctx = rs.retrieve_context("distribution loss target", ["regulations", "myt_orders"], k=1)
    assert ctx.startswith("[MYT Order.pdf]")
