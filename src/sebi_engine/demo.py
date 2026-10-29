"""Synthetic software fixtures only. Never regulatory research ground truth."""
import hashlib
from datetime import date
from .models import Amendment, Clause, Document
from .store import Store


def seed_demo(store: Store):
    fixtures = [
        ("DEMO-BASE", "Synthetic disclosure policy", "2024-01-01", "2024-01-01",
         [("1", "The disclosure threshold is 10 units."), ("2", "Records must be retained for 5 years."),
          ("3", "A quarterly paper report must be submitted.")]),
        ("DEMO-AMENDMENT", "Synthetic partial amendment", "2024-03-01", "2024-04-01",
         [("1", "Clause 1 of DEMO-BASE is replaced: The disclosure threshold is 20 units. This takes effect on April 1, 2024. All other clauses remain unchanged.")]),
        ("DEMO-DELETE", "Synthetic deletion", "2024-05-01", "2024-06-01",
         [("1", "Clause 3 of DEMO-BASE is deleted with effect from June 1, 2024.")]),
    ]
    for doc_id, title, published, effective, rows in fixtures:
        digest = hashlib.sha256(str(rows).encode()).hexdigest()
        d = Document(id=doc_id, title=title, publication_date=published, effective_date=effective,
                     kind="synthetic", sha256=digest, date_evidence="Synthetic fixture dates")
        store.ingest(d, [Clause(id=f"{doc_id}:{label}", document_id=doc_id, label=label, text=text,
                               page=1, end_page=1) for label, text in rows])
    store.put_amendment(Amendment(id="demo-replace", source_document_id="DEMO-AMENDMENT",
        source_clause_id="DEMO-AMENDMENT:1", target_document_id="DEMO-BASE", target_clause_id="DEMO-BASE:1",
        operation="replace", new_text="The disclosure threshold is 20 units.", effective_date=date(2024,4,1),
        evidence="Synthetic replacement fixture", status="approved", reviewer="synthetic-fixture",
        review_note="SOFTWARE TEST ONLY, not a human-reviewed legal label"))
    store.put_amendment(Amendment(id="demo-delete", source_document_id="DEMO-DELETE",
        source_clause_id="DEMO-DELETE:1", target_document_id="DEMO-BASE", target_clause_id="DEMO-BASE:3",
        operation="delete", effective_date=date(2024,6,1), evidence="Synthetic deletion fixture",
        status="approved", reviewer="synthetic-fixture", review_note="SOFTWARE TEST ONLY"))
    return {"status": "ready", "scope": ["DEMO-BASE"], "warning": "Synthetic fixtures, not SEBI rules"}
