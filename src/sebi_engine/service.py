from .models import Amendment, Review, ClauseDateReview
from .store import Store


def review_clause_date(store: Store, review: ClauseDateReview):
    clauses={c.id:c for c in store.clauses()}
    target=clauses.get(review.clause_id)
    if not target:
        raise KeyError("Unknown clause")
    if not review.reviewer.strip() or not review.note.strip():
        raise ValueError("Record reviewer and source-date rationale")
    if any(key not in clauses or clauses[key].document_id!=target.document_id for key in review.evidence_clause_ids):
        raise ValueError("Initial applicability evidence must come from the same original document; later changes require amendment events")
    updated=target.model_copy(update={"initial_effective_date":review.effective_date,"applicability_reviewed":True,
        "applicability_note":review.note,"applicability_reviewer":review.reviewer})
    with store.connect() as db:
        db.execute("UPDATE clauses SET payload=? WHERE id=?",(updated.model_dump_json(),target.id))
        store.log(db,"initial_clause_date_review",target.id,{"before":target.model_dump(mode="json"),
            "after":updated.model_dump(mode="json"),"evidence_clause_ids":review.evidence_clause_ids})
    return updated


def review_event(store: Store, event_id: str, review: Review):
    event = next((e for e in store.amendments() if e.id == event_id), None)
    if not event:
        raise KeyError("Unknown amendment")
    patch = {k: v for k, v in review.model_dump().items() if v is not None and k != "note"}
    patch["review_note"] = review.note
    updated = Amendment.model_validate({**event.model_dump(), **patch})
    clauses = {c.id: c for c in store.clauses()}
    docs = {d.id: d for d in store.documents()}
    if updated.status == "approved":
        if updated.source_document_id not in docs or updated.target_document_id not in docs:
            raise ValueError("Both source and target documents must be imported")
        source = clauses.get(updated.source_clause_id)
        if not source or source.document_id != updated.source_document_id:
            raise ValueError("Source citation does not belong to source document")
        if docs[updated.source_document_id].kind == "draft":
            raise ValueError("A draft cannot amend an operative circular")
        if updated.operation not in {"supersede", "reference"}:
            target = clauses.get(updated.target_clause_id)
            inserted = next((e for e in store.amendments()
                if f"insert::{e.id}" == updated.target_clause_id and e.operation == "insert"
                and e.status == "approved" and e.target_document_id == updated.target_document_id
                and e.effective_date < updated.effective_date), None)
            if not inserted and (not target or target.document_id != updated.target_document_id):
                raise ValueError("Target clause does not belong to target document")
        if not review.note.strip():
            raise ValueError("Record effective-date/source rationale in the review note")
    store.put_amendment(updated, replace=True)
    return updated
