import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from .models import Amendment, Clause, Document


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS clauses(id TEXT PRIMARY KEY, document_id TEXT NOT NULL,
                    payload TEXT NOT NULL, FOREIGN KEY(document_id) REFERENCES documents(id));
                CREATE INDEX IF NOT EXISTS clauses_document ON clauses(document_id);
                CREATE TABLE IF NOT EXISTS amendments(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, time TEXT NOT NULL,
                    action TEXT NOT NULL, entity_id TEXT NOT NULL, payload TEXT NOT NULL);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def log(db, action, entity_id, payload):
        db.execute("INSERT INTO audit(time,action,entity_id,payload) VALUES(?,?,?,?)",
                   (datetime.now(timezone.utc).isoformat(), action, entity_id, json.dumps(payload)))

    def ingest(self, document: Document, clauses: list[Clause]):
        with self.connect() as db:
            existing = db.execute("SELECT payload FROM documents WHERE id=?", (document.id,)).fetchone()
            if existing:
                if Document.model_validate_json(existing[0]).sha256 == document.sha256:
                    return False
                raise ValueError("Document ID already exists with different bytes; ingest as a distinct revision")
            db.execute("INSERT INTO documents VALUES(?,?)", (document.id, document.model_dump_json()))
            for clause in clauses:
                if clause.document_id != document.id:
                    raise ValueError("Clause document mismatch")
                db.execute("INSERT INTO clauses VALUES(?,?,?)", (clause.id, document.id, clause.model_dump_json()))
            self.log(db, "ingest", document.id, {"sha256": document.sha256, "clauses": len(clauses)})
        return True

    def documents(self):
        with self.connect() as db:
            return [Document.model_validate_json(r[0]) for r in db.execute("SELECT payload FROM documents ORDER BY id")]

    def clauses(self):
        with self.connect() as db:
            return [Clause.model_validate_json(r[0]) for r in db.execute("SELECT payload FROM clauses ORDER BY id")]

    def amendments(self):
        with self.connect() as db:
            return [Amendment.model_validate_json(r[0]) for r in db.execute("SELECT payload FROM amendments ORDER BY id")]

    def put_amendment(self, event: Amendment, *, replace=False):
        with self.connect() as db:
            previous = db.execute("SELECT payload FROM amendments WHERE id=?", (event.id,)).fetchone()
            if previous and not replace:
                return False
            # Preserve both versions in append-only audit; never silently replace a review.
            db.execute("INSERT INTO amendments VALUES(?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
                       (event.id, event.model_dump_json()))
            self.log(db, "amendment_review" if replace else "amendment_proposal", event.id,
                     {"before": json.loads(previous[0]) if previous else None,
                      "after": event.model_dump(mode="json")})
        return True

    def audit(self):
        with self.connect() as db:
            return [dict(zip(["id", "time", "action", "entity_id", "payload"], r))
                    for r in db.execute("SELECT * FROM audit ORDER BY id")]
