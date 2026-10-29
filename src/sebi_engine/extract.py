"""High precision starter patterns. Results are PROPOSALS, never gold labels."""
import hashlib
import re
from .models import Amendment
from .store import Store


def normalized(text):
    return re.sub(r"\s+", "", text).lower()


def propose(store: Store, document_id: str):
    documents = {d.id: d for d in store.documents()}
    if document_id not in documents:
        raise ValueError("Unknown document")
    all_clauses = store.clauses()
    clauses = [c for c in all_clauses if c.document_id == document_id and c.kind == "clause"]
    text = "\n".join(c.text for c in clauses)
    targets = [d for d in documents if d != document_id and normalized(d) in normalized(text)]
    events = []
    # Only explicit named clause operations; references do not change validity.
    for c in clauses:
        match = re.search(r"(?:para(?:graph)?|clause)\s+(\d+(?:\.\d+)*)\s+(?:shall\s+)?(?:be\s+)?(?:read\s+as\s+(?:follows|under)|(?:replaced|substituted).*?(?:follows|under))\s*[:.\-]?\s*(.*)", c.text, re.I | re.S)
        deletion = re.search(r"(?:para(?:graph)?|clause)\s+(\d+(?:\.\d+)*)\s+(?:shall\s+be\s+|is\s+)(?:deleted|omitted)", c.text, re.I)
        insertion = re.search(r"after\s+(?:para(?:graph)?|clause)\s+(\d+(?:\.\d+)*).*?insert", c.text, re.I | re.S)
        supersede = re.search(r"\b(?:shall\s+be\s+rescinded|in\s+supersession\s+of|hereby\s+supersedes)\b", c.text, re.I)
        if not any([match, deletion, insertion, supersede]):
            continue
        local_targets = [d for d in targets if normalized(d) in normalized(c.text)]
        choices = local_targets or targets
        target = choices[0] if len(choices) == 1 else "UNRESOLVED"
        operation = "replace" if match else "delete" if deletion else "insert" if insertion else "supersede"
        label = (match or deletion or insertion)[1] if not supersede or (match or deletion or insertion) else None
        matches = [x for x in all_clauses if x.document_id == target and x.label == label and x.kind == "clause"]
        event_id = hashlib.sha256(f"{c.id}|{operation}|{target}|{label}".encode()).hexdigest()[:24]
        events.append(Amendment(id=event_id, source_document_id=document_id, source_clause_id=c.id,
            target_document_id=target, target_clause_id=matches[0].id if len(matches) == 1 else None,
            target_label=label, operation=operation,
            # Source circular effective date is not necessarily every provision's effective date.
            effective_date=None, new_text=match[2].strip() if match else None,
            evidence=c.text, review_note="Review target, operation, text boundaries and explicit effective-date evidence."))
    for target in targets:
        if any(e.target_document_id == target for e in events):
            continue
        source = next(c for c in clauses if normalized(target) in normalized(c.text))
        events.append(Amendment(id=hashlib.sha256(f"{source.id}|reference|{target}".encode()).hexdigest()[:24],
            source_document_id=document_id, source_clause_id=source.id, target_document_id=target,
            operation="reference", evidence=source.text))
    return {"created": sum(store.put_amendment(e) for e in events),
            "proposals": [e.model_dump(mode="json") for e in events],
            "limitations": ["Missing external circulars are not automatically discovered",
                            "Unmatched drafting patterns require manual annotation; zero proposals does not prove no amendments"]}
