import os
from pathlib import Path
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, FileResponse
from .extract import propose
from .ingest import ingest_pdf
from .models import Amendment, Document, Query, Review, ClauseDateReview
from .resolve import resolve
from .search import answer
from .service import review_event, review_clause_date
from .store import Store
from .coverage import coverage_report
from .benchmark import read_jsonl, digest


def create_app(db_path=None):
    store = Store(db_path or os.getenv("SEBI_DB", "runtime/sebi.sqlite"))
    app = FastAPI(title="SEBI Clause Evidence Engine", version="0.2.0",
        description="Local research backend. Extracted proposals require review. No verified legal benchmark is bundled.")
    app.state.store = store

    @app.get("/", response_class=HTMLResponse)
    def home():
        return (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")

    @app.get("/annotate",response_class=HTMLResponse)
    def annotate():
        return (Path(__file__).parent/"static"/"annotate.html").read_text(encoding="utf-8")

    @app.get("/annotation-questions")
    def annotation_questions():
        path=Path(__file__).resolve().parents[2]/"data"/"review_packets"/"questions.jsonl"
        if not path.exists():
            raise HTTPException(404,"Prepare review packets first")
        return [{"question":q,"question_sha256":digest(q)} for q in read_jsonl(path)]

    @app.get("/health")
    def health():
        return {"status": "ok", "documents": len(store.documents()), "answer_mode": "extractive"}

    @app.get("/documents")
    def documents():
        return store.documents()

    @app.get("/clauses")
    def clauses(document_id: str | None = None):
        return [c for c in store.clauses() if document_id is None or c.document_id == document_id]

    @app.post("/ingest")
    async def ingest(metadata: str = Form(...), file: UploadFile = File(...)):
        try:
            doc = Document.model_validate_json(metadata)
            raw = await file.read(25 * 1024 * 1024 + 1)
            if len(raw) > 25 * 1024 * 1024:
                raise HTTPException(413, "PDF exceeds 25 MB pilot limit")
            # Keep canonical bytes under a hash, never an uploaded path.
            import hashlib
            folder = store.path.parent / "pdfs"
            folder.mkdir(exist_ok=True)
            path = folder / (hashlib.sha256(raw).hexdigest() + ".pdf")
            if not raw.startswith(b"%PDF"):
                raise ValueError("Input is not a PDF")
            path.write_bytes(raw)
            return ingest_pdf(store, path, doc)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/extract")
    def extract(document_id: str):
        try:
            return propose(store, document_id)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/amendments")
    def amendments():
        return store.amendments()

    @app.post("/amendments", status_code=201)
    def add_amendment(event: Amendment):
        if event.status != "proposed":
            raise HTTPException(422, "Create a proposal, then use the review endpoint")
        if not store.put_amendment(event):
            raise HTTPException(409, "Event ID already exists")
        return event

    @app.post("/amendments/{event_id}/review")
    def review(event_id: str, body: Review):
        try:
            return review_event(store, event_id, body)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/resolve")
    def snapshot(body: Query):
        return resolve(store, body.scope_document_ids, body.as_of, body.known_at)

    @app.post("/query")
    def query(body: Query):
        return answer(store, body)

    @app.get("/audit")
    def audit():
        return store.audit()

    @app.get("/coverage")
    def coverage():
        return coverage_report(store)

    @app.post("/clauses/review-date")
    def clause_date(body: ClauseDateReview):
        try:
            return review_clause_date(store,body)
        except KeyError as exc:
            raise HTTPException(404,str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422,str(exc)) from exc

    @app.get("/research-status")
    def research_status():
        return {"documents":len(store.documents()),"segments":len(store.clauses()),
            "proposed_events":sum(e.status=="proposed" for e in store.amendments()),
            "approved_events":sum(e.status=="approved" for e in store.amendments()),
            "reviewed_initial_clause_dates":sum(c.applicability_reviewed for c in store.clauses()),
            "methods":["ordinary","recency","document","interval","temporal_rerank","clause","clause_selective"],
            "publication_claim":"No validated superiority or publication-readiness claim",
            "next_gate":"Independent source annotation and frozen real-data evaluation"}

    @app.get("/research-packet/{name}")
    def packet(name: str):
        if name not in {"questions.jsonl","reviewer_a.jsonl","reviewer_b.jsonl","amendment_review_queue.jsonl","document_date_review_queue.jsonl"}:
            raise HTTPException(404,"Unknown research artifact")
        path=Path(__file__).resolve().parents[2]/"data"/"review_packets"/name
        if not path.exists():
            raise HTTPException(404,"Run prepare_review_packets.py in the project checkout first")
        return FileResponse(path,media_type="application/x-ndjson",filename=name)

    return app


app = create_app()
