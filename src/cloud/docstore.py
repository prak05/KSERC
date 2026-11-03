"""
Document store with a small fluent API:

    db = client()
    db.collection("analyses").document(aid).set({...}, merge=True)
    db.collection("myt_norms").document(lic).collection("years").stream()
    db.collection("depreciation_records").where("licensee", "==", x) \
      .order_by("financial_year", direction="DESCENDING").limit(5).stream()

Backends
  local  SQLite file (``LOCAL_DB_PATH``)
  aws    one DynamoDB table — partition key ``pk`` = collection path,
         sort key ``sk`` = document id, ``doc`` = JSON body. Bodies larger than
         DynamoDB's 400 KB item limit are written to S3 and referenced by key.
"""

import json
import sqlite3
import threading
from typing import Any, Dict, Iterator, List, Optional, Tuple

from src.cloud import settings

_DYNAMO_INLINE_LIMIT = 350_000  # bytes; DynamoDB's hard item limit is 400 KB


# ═══════════════════════════════════════════════════════════════════════
# Backends
# ═══════════════════════════════════════════════════════════════════════

class _SQLiteBackend:
    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS docs (coll TEXT, id TEXT, doc TEXT, PRIMARY KEY (coll, id))"
            )
            self._conn.commit()

    def get(self, coll: str, doc_id: str) -> Optional[dict]:
        with self._lock:
            row = self._conn.execute("SELECT doc FROM docs WHERE coll=? AND id=?", (coll, doc_id)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, coll: str, doc_id: str, data: dict):
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO docs (coll, id, doc) VALUES (?, ?, ?)",
                (coll, doc_id, json.dumps(data, default=str)),
            )
            self._conn.commit()

    def delete(self, coll: str, doc_id: str):
        with self._lock:
            self._conn.execute("DELETE FROM docs WHERE coll=? AND id=?", (coll, doc_id))
            self._conn.commit()

    def scan(self, coll: str) -> List[Tuple[str, dict]]:
        with self._lock:
            rows = self._conn.execute("SELECT id, doc FROM docs WHERE coll=?", (coll,)).fetchall()
        return [(i, json.loads(d)) for i, d in rows]


class _DynamoBackend:
    def __init__(self):
        import boto3

        self._table = boto3.resource("dynamodb", region_name=settings.AWS_REGION).Table(settings.DYNAMODB_TABLE)
        self._s3 = boto3.client("s3", region_name=settings.AWS_REGION)

    def _spill_key(self, coll: str, doc_id: str) -> str:
        return f"docstore/{coll}/{doc_id}.json"

    def get(self, coll: str, doc_id: str) -> Optional[dict]:
        item = self._table.get_item(Key={"pk": coll, "sk": doc_id}).get("Item")
        return self._decode(item) if item else None

    def _decode(self, item: dict) -> dict:
        if "s3_key" in item:
            body = self._s3.get_object(Bucket=settings.DOCS_BUCKET, Key=item["s3_key"])["Body"].read()
            return json.loads(body)
        return json.loads(item["doc"])

    def put(self, coll: str, doc_id: str, data: dict):
        body = json.dumps(data, default=str)
        if len(body.encode()) > _DYNAMO_INLINE_LIMIT:
            key = self._spill_key(coll, doc_id)
            self._s3.put_object(Bucket=settings.DOCS_BUCKET, Key=key, Body=body.encode(),
                                ContentType="application/json")
            self._table.put_item(Item={"pk": coll, "sk": doc_id, "s3_key": key})
        else:
            self._table.put_item(Item={"pk": coll, "sk": doc_id, "doc": body})

    def delete(self, coll: str, doc_id: str):
        self._table.delete_item(Key={"pk": coll, "sk": doc_id})

    def scan(self, coll: str) -> List[Tuple[str, dict]]:
        from boto3.dynamodb.conditions import Key

        out, kwargs = [], {"KeyConditionExpression": Key("pk").eq(coll)}
        while True:
            page = self._table.query(**kwargs)
            out.extend((it["sk"], self._decode(it)) for it in page.get("Items", []))
            if "LastEvaluatedKey" not in page:
                return out
            kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]


# ═══════════════════════════════════════════════════════════════════════
# Fluent API
# ═══════════════════════════════════════════════════════════════════════

class Snapshot:
    def __init__(self, doc_id: str, data: Optional[dict]):
        self.id = doc_id
        self._data = data

    @property
    def exists(self) -> bool:
        return self._data is not None

    def to_dict(self) -> Optional[dict]:
        return dict(self._data) if self._data is not None else None


class DocumentRef:
    def __init__(self, backend, coll: str, doc_id: str):
        self._b, self._coll, self.id = backend, coll, doc_id

    def get(self) -> Snapshot:
        return Snapshot(self.id, self._b.get(self._coll, self.id))

    def set(self, data: Dict[str, Any], merge: bool = False):
        if merge:
            current = self._b.get(self._coll, self.id) or {}
            current.update(data)
            data = current
        self._b.put(self._coll, self.id, data)

    def update(self, data: Dict[str, Any]):
        current = self._b.get(self._coll, self.id)
        if current is None:
            raise KeyError(f"No document to update: {self._coll}/{self.id}")
        current.update(data)
        self._b.put(self._coll, self.id, current)

    def delete(self):
        self._b.delete(self._coll, self.id)

    def collection(self, name: str) -> "CollectionRef":
        return CollectionRef(self._b, f"{self._coll}/{self.id}/{name}")


class Query:
    def __init__(self, backend, coll: str, filters=None, order=None, limit_n=None):
        self._b, self._coll = backend, coll
        self._filters = filters or []
        self._order = order
        self._limit = limit_n

    def where(self, field: str, op: str, value) -> "Query":
        if op != "==":
            raise NotImplementedError(f"Only '==' filters are supported (got {op})")
        return Query(self._b, self._coll, self._filters + [(field, value)], self._order, self._limit)

    def order_by(self, field: str, direction: str = "ASCENDING") -> "Query":
        return Query(self._b, self._coll, self._filters, (field, str(direction).upper()), self._limit)

    def limit(self, n: int) -> "Query":
        return Query(self._b, self._coll, self._filters, self._order, n)

    def stream(self) -> Iterator[Snapshot]:
        rows = [(i, d) for i, d in self._b.scan(self._coll)
                if all(d.get(f) == v for f, v in self._filters)]
        if self._order:
            field, direction = self._order
            rows.sort(key=lambda r: (r[1].get(field) is None, r[1].get(field) or ""),
                      reverse=direction.startswith("DESC"))
        if self._limit is not None:
            rows = rows[: self._limit]
        return iter(Snapshot(i, d) for i, d in rows)


class CollectionRef(Query):
    def __init__(self, backend, path: str):
        super().__init__(backend, path)

    def document(self, doc_id: str) -> DocumentRef:
        return DocumentRef(self._b, self._coll, doc_id)


class Client:
    def __init__(self, backend):
        self._b = backend

    def collection(self, name: str) -> CollectionRef:
        return CollectionRef(self._b, name)


_client: Optional[Client] = None
_lock = threading.Lock()


def client() -> Client:
    global _client
    with _lock:
        if _client is None:
            backend = _DynamoBackend() if settings.IS_AWS else _SQLiteBackend(settings.LOCAL_DB_PATH)
            _client = Client(backend)
    return _client
