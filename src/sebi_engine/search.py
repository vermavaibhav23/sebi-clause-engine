"""Small-corpus BM25 retrieval; no model download or GPU required."""
import math
import re
from collections import Counter
from .models import Query
from .resolve import citation, resolve
from .store import Store
from .temporal import version_index, is_valid, rerank
from .selective import select_with_gate

STOP = set("a an the is are was were be been what which who how when where why of for to in on as at and or with by from this that it do does please current rule rules tell me under".split())


def tokens(text):
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP]


def rank(question, clauses, top_k, recency=False):
    q = set(tokens(question))
    bags = [Counter(tokens(c["label"] + " " + c["text"])) for c in clauses]
    if not bags or not q:
        return []
    avg = sum(sum(b.values()) for b in bags) / len(bags) or 1
    dfs = {w: sum(w in b for b in bags) for w in q}
    hits = []
    for c, b in zip(clauses, bags):
        length = sum(b.values())
        score = sum(math.log(1 + (len(bags) - dfs[w] + .5) / (dfs[w] + .5)) *
                    b[w] * 2.5 / (b[w] + 1.5 * (.25 + .75 * length / avg))
                    for w in q if b[w])
        if score > 0:
            hits.append({**c, "score": round(score, 6), "matched_terms": sorted(q & b.keys())})
    hits.sort(key=lambda x: (x.get("publication_date", ""), x["score"]) if recency else (x["score"],), reverse=True)
    return hits[:top_k]


def answer(store: Store, query: Query):
    docs = {d.id: d for d in store.documents()}
    known_at = query.known_at or query.as_of
    response = {"question": query.question, "as_of": str(query.as_of), "known_at": str(known_at),
                "baseline": query.baseline, "answer_mode": "extractive", "status": "insufficient_evidence",
                "answer": "Insufficient evidence.", "evidence": [], "issues": [],
                "scope": query.scope_document_ids,
                "notice": "Research evidence within a bounded corpus; not a declaration of current law."}
    if not query.scope_document_ids:
        response["issues"] = [{"reason": "scope_required"}]
        return response
    evidence = None
    if query.baseline in {"clause", "clause_selective"}:
        result = resolve(store, query.scope_document_ids, query.as_of, known_at)
        response["issues"] = result["issues"]
        if not query.scope_reviewed:
            response["issues"].append({"reason": "corpus_scope_not_reviewed"})
        if not query.scope_reviewed:
            return response
        if query.baseline=="clause_selective":
            visible_events=[e for e in store.amendments() if e.source_document_id in docs
                            and docs[e.source_document_id].publication_date<=known_at]
            evidence,issues,ignored=select_with_gate(result,query,rank,visible_events)
            response["issues"]=issues
            response["out_of_query_issues"]=ignored
            response["notice"]+=" Experimental selective gate: relevance and dependency completeness are not guaranteed."
            if issues:
                return response
        else:
            if response["issues"]:
                return response
        candidates = [c for c in result["clauses"] if c["status"] == "active"]
    elif query.baseline in {"interval","temporal_rerank"}:
        candidates=version_index(store,query.scope_document_ids,known_at)
        if query.baseline=="interval":
            candidates=[c for c in candidates if is_valid(c,query.as_of)]
        else:
            pool=rank(query.question,candidates,query.candidate_pool)
            evidence=rerank(pool,query)[:query.top_k]
        response["notice"]+=" Independent interval baseline; unresolved event proposals are not applied."
        if query.baseline=="temporal_rerank":
            response["notice"]+=" Paper-inspired fixed-weight adaptation, not a TimelyRAG reproduction."
    else:
        # Experimental baselines intentionally do not resolve clause-level amendments.
        allowed = set(query.scope_document_ids)
        # Reach a fixed point so chained documents do not depend on database row order.
        while True:
            expanded = allowed | {e.source_document_id for e in store.amendments()
                                  if e.target_document_id in allowed and e.status != "rejected"}
            if expanded == allowed:
                break
            allowed = expanded
        if query.baseline == "document":
            for e in store.amendments():
                source = docs.get(e.source_document_id)
                if e.status == "approved" and e.operation == "supersede" and e.effective_date <= query.as_of and source and source.publication_date <= known_at:
                    allowed.discard(e.target_document_id)
        candidates = [{**c.model_dump(), "logical_id": c.id, "status": "baseline_unresolved",
                       "history": [], "publication_date": str(docs[c.document_id].publication_date),
                       "citations": [citation(c, docs[c.document_id])]}
                      for c in store.clauses() if c.document_id in allowed
                      and docs[c.document_id].publication_date <= known_at
                      and docs[c.document_id].kind != "draft"]
        response["notice"] += " Baseline output is intentionally not applicability-validated."
    if evidence is None:
        evidence = rank(query.question, candidates, query.top_k, query.baseline == "recency")
    if not evidence:
        response["issues"].append({"reason": "no_matching_evidence"})
        return response
    response.update(status="evidence_found", evidence=evidence,
        answer="\n\n".join(f"[{i}] {c['text']}" for i, c in enumerate(evidence, 1)))
    return response
