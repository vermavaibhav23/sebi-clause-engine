from datetime import date
from .store import Store


def resolve(store: Store, scope: list[str], as_of: date, known_at: date | None = None):
    """Resolve a bounded document scope using reviewed edits. Unknowns are explicit."""
    known_at = known_at or as_of
    docs = {d.id: d for d in store.documents()}
    originals = {c.id: c for c in store.clauses()}
    states, issues = {}, []
    if not scope:
        return {"clauses": [], "issues": [{"reason": "scope_required"}], "as_of": str(as_of)}
    for doc_id in scope:
        d = docs.get(doc_id)
        if not d:
            issues.append({"reason": "missing_document", "document_id": doc_id})
            continue
        if d.kind == "draft":
            issues.append({"reason": "draft_is_not_authority", "document_id": doc_id})
            continue
        if d.publication_date > known_at:
            issues.append({"reason": "not_yet_published", "document_id": doc_id})
            continue
        for c in originals.values():
            if c.document_id == doc_id:
                effective=c.initial_effective_date if c.applicability_reviewed else d.effective_date
                if effective and effective>as_of:
                    continue
                if effective is None:
                    issues.append({"reason":"unknown_base_effective_date","document_id":doc_id,"target_clause_id":c.id})
                states[c.id] = {**c.model_dump(), "logical_id": c.id, "valid_from": str(effective) if effective else None,
                               "status": "active" if effective else "unresolved", "history": [], "citations": [citation(c, d)]}
    events = sorted(store.amendments(), key=lambda e: (e.effective_date or date.min, e.id))
    changed = set()
    for e in events:
        source = docs.get(e.source_document_id)
        if source and source.publication_date > known_at:
            continue
        if e.status == "rejected" or e.operation == "reference":
            continue
        if e.target_document_id not in scope and e.target_document_id != "UNRESOLVED":
            continue
        if e.effective_date and e.effective_date > as_of:
            continue
        affected = [e.target_clause_id] if e.target_clause_id else [k for k, v in states.items()
                    if v["document_id"] == e.target_document_id]
        reason = None
        if not source or e.source_clause_id not in originals:
            reason = "missing_amendment_source"
        elif source.kind == "draft":
            reason = "draft_amendment"
        elif e.status != "approved":
            reason = "unreviewed_amendment"
        elif e.effective_date is None:
            reason = "unknown_effective_date"
        elif e.target_document_id not in docs:
            reason = "missing_target_document"
        elif e.operation != "supersede" and e.target_clause_id not in states:
            reason = "missing_target_clause"
        if reason:
            issues.append({"reason": reason, "event_id": e.id, "target_document_id": e.target_document_id,
                           "target_clause_id": e.target_clause_id})
            for key in affected:
                if key in states:
                    states[key]["status"] = "unresolved"
            continue
        if e.operation == "supersede":
            for state in states.values():
                if state["document_id"] == e.target_document_id:
                    state["status"] = "superseded"
                    state["history"].append(e.id)
            continue
        key = e.target_clause_id
        state = states[key]
        stamp = (key, e.effective_date)
        if state["status"] != "active" or stamp in changed:
            state["status"] = "unresolved"
            issues.append({"reason": "conflicting_or_inactive_target", "event_id": e.id, "target_clause_id": key})
            continue
        changed.add(stamp)
        new_citation = citation(originals[e.source_clause_id], source)
        if e.operation == "insert":
            new_key = f"insert::{e.id}"
            if any(v["document_id"] == state["document_id"] and v["label"] == e.new_label
                   and v["status"] == "active" for v in states.values()):
                issues.append({"reason": "duplicate_inserted_label", "event_id": e.id})
                continue
            states[new_key] = {**state, "id": new_key, "logical_id": new_key, "label": e.new_label,
                "text": e.new_text, "valid_from": str(e.effective_date), "history": [e.id],
                "citations": [new_citation], "inserted_after": key}
        elif e.operation == "delete":
            state["status"] = "deleted"
            state["valid_to"] = str(e.effective_date)
            state["history"].append(e.id)
            state["citations"].append(new_citation)
        elif e.operation == "replace":
            state["text"] = e.new_text
            state["valid_from"] = str(e.effective_date)
            state["history"].append(e.id)
            state["citations"].append(new_citation)
    return {"clauses": list(states.values()), "issues": issues, "as_of": str(as_of),
            "known_at": str(known_at), "scope": scope,
            "coverage": "Bounded corpus only; absence of an amendment is not proof of completeness"}


def citation(clause, document):
    return {"document_id": document.id, "clause_id": clause.id, "label": clause.label,
            "page": clause.page, "end_page": clause.end_page, "source_url": document.source_url,
            "sha256": document.sha256, "quote": clause.text}
