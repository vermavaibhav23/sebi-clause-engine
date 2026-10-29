"""Independent interval-index baseline and explicitly adapted temporal reranker.

Does not call the proposed snapshot resolver. Both consume the same reviewed
event inputs. See docs/BASELINES.md for assumptions and paper/code differences.
"""
from datetime import date
import math
from .resolve import citation


def version_index(store, scope, known_at):
    docs={d.id:d for d in store.documents()}
    clauses={c.id:c for c in store.clauses()}
    versions=[]
    for c in clauses.values():
        d=docs[c.document_id]
        if c.document_id in scope and d.publication_date<=known_at and d.kind!="draft":
            effective=c.initial_effective_date if c.applicability_reviewed else d.effective_date
            versions.append({**c.model_dump(),"logical_id":c.id,"version_id":c.id+"::base",
                "valid_from":str(effective) if effective else None,"valid_to":None,
                "publication_date":str(d.publication_date),"status":"interval_candidate","history":[],
                "citations":[citation(c,d)]})
    events=[e for e in store.amendments() if e.status=="approved" and e.operation!="reference"
        and e.effective_date and e.target_document_id in scope and e.source_document_id in docs
        and docs[e.source_document_id].publication_date<=known_at
        and docs[e.source_document_id].kind!="draft" and e.source_clause_id in clauses]
    events.sort(key=lambda e:(e.effective_date,e.id))
    for event in events:
        boundary=str(event.effective_date)
        affected=[v for v in versions if v["document_id"]==event.target_document_id
            and (event.operation=="supersede" or v["logical_id"]==event.target_clause_id)]
        if event.operation!="insert":
            for v in affected:
                if v["valid_to"] is None or boundary<v["valid_to"]:
                    v["valid_to"]=boundary
        if event.operation not in {"replace","insert"}:
            continue
        target=clauses.get(event.target_clause_id)
        template=affected[-1] if affected else (target.model_dump() if target else None)
        if template is None:
            continue
        logical_id=f"insert::{event.id}" if event.operation=="insert" else event.target_clause_id
        source=docs[event.source_document_id]
        base_cites=[citation(target,docs[target.document_id])] if target and event.operation=="replace" else []
        versions.append({**template,"id":logical_id,"logical_id":logical_id,"version_id":event.id,
            "label":event.new_label if event.operation=="insert" else template["label"],
            "text":event.new_text,"valid_from":boundary,"valid_to":None,
            "publication_date":str(source.publication_date),"status":"interval_candidate",
            "history":[event.id],"citations":base_cites+[citation(clauses[event.source_clause_id],source)]})
    counts={}
    for v in versions:
        stamp=(v["logical_id"],v["valid_from"])
        counts[stamp]=counts.get(stamp,0)+1
    for v in versions:
        if counts[(v["logical_id"],v["valid_from"])]>1:
            v["valid_to"]=v["valid_from"]
            v["status"]="conflicting_versions"
    return versions


def is_valid(candidate, when):
    start,end=candidate["valid_from"],candidate["valid_to"]
    return candidate.get("status")!="conflicting_versions" and start is not None and start<=str(when) and (end is None or str(when)<end)


def interval_distance(when, start, end):
    if start is None:
        return None
    first=date.fromisoformat(start)
    last=date.fromisoformat(end) if end else None
    if when<first:
        return (first-when).days
    # Validity is [start,end); first expired day has positive distance.
    if last and when>=last:
        return (when-last).days+1
    return 0


def rerank(candidates, query):
    if not candidates:
        return []
    when=query.as_of
    known=query.known_at or when
    semantic=[c["score"] for c in candidates]
    delta=[]
    for c in candidates:
        published=date.fromisoformat(c["publication_date"])
        distance=interval_distance(when,c["valid_from"],c["valid_to"])
        # Explicitly documented adaptation: only this term falls back to publication.
        distance=abs((when-published).days) if distance is None else distance
        start=date.fromisoformat(c["valid_from"]) if c["valid_from"] else published
        delta.append(distance+.1*abs((known-published).days)+.1*abs((known-start).days)
                     +.1*abs((when-published).days))
    def normalize(values):
        low,high=min(values),max(values)
        return [(v-low)/(high-low) if high>low else 0.0 for v in values]
    scores,distances=normalize(semantic),normalize(delta)
    output=[]
    for c,s,d in zip(candidates,scores,distances):
        affinity=math.exp(-2*d)
        score=(1-query.temporal_weight)*s+query.temporal_weight*affinity
        output.append({**c,"score":score,"bm25_score":c["score"],"temporal_affinity":affinity})
    return sorted(output,key=lambda c:(-c["score"],c["version_id"]))
