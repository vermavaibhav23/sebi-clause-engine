"""Deterministic, explicitly limited evidence evaluation; no LLM judge."""
import hashlib
import json
import platform
import time
from importlib.metadata import version
from pathlib import Path
from .models import Query
from .search import answer
from .store import Store
from .statistics import cluster_bootstrap, risk_coverage
from .benchmark import corpus_fingerprint


def evaluate(store: Store, dataset: Path, output: Path, allow_synthetic=False, split_manifest=None, split="test"):
    rows = [json.loads(s) for s in dataset.read_text(encoding="utf-8").splitlines() if s.strip()]
    if not rows:
        raise ValueError("Empty benchmark")
    if len({r["id"] for r in rows})!=len(rows):
        raise ValueError("Duplicate benchmark IDs")
    frozen = None
    if split_manifest:
        frozen=json.loads(Path(split_manifest).read_text(encoding="utf-8"))
        if frozen["dataset_sha256"]!=hashlib.sha256(dataset.read_bytes()).hexdigest():
            raise ValueError("Benchmark changed after split freeze")
        if set(frozen["question_assignments"])!={r["id"] for r in rows}:
            raise ValueError("Split IDs do not match dataset")
        if frozen.get("corpus_sha256") and frozen["corpus_sha256"]!=corpus_fingerprint(store):
            raise ValueError("Corpus or annotations changed after split freeze")
        for r in rows:
            if frozen["question_assignments"][r["id"]]!=frozen["family_assignments"].get(r["family_id"]):
                raise ValueError("Split manifest divides an amendment family")
        rows=[r for r in rows if frozen["question_assignments"][r["id"]]==split]
        if not rows:
            raise ValueError("Selected split is empty")
    for r in rows:
        if r.get("label_status") == "synthetic" and allow_synthetic:
            continue
        if r.get("label_status") != "human_verified" or len(set(r.get("reviewers", []))) < 2:
            raise ValueError(f"{r.get('id')}: benchmark requires two named reviewers; AI drafts are not gold")
        if not r.get("family_id") or not r.get("review_provenance"):
            raise ValueError("Real benchmark requires merged independent reviews and family IDs")
        if not r.get("should_abstain") and (not r.get("required_citation_ids") or not r.get("required_answer_fragments")):
            raise ValueError("Answerable cases need evidence and an answer rubric")
    results, totals = [], {}
    for mode in ["ordinary", "recency", "document", "interval", "temporal_rerank", "clause", "clause_selective"]:
        correct, abstain_tp, abstain_fp, abstain_fn, stale, answered = 0, 0, 0, 0, 0, 0
        evidence_recall, unchanged_correct, unchanged_n = [], 0, 0
        latencies=[]
        for r in rows:
            query = Query(**{**r["query"], "baseline": mode})
            started=time.perf_counter()
            pred = answer(store, query)
            latencies.append((time.perf_counter()-started)*1000)
            abstained = pred["status"] == "insufficient_evidence"
            should_abstain = r["should_abstain"]
            abstain_tp += abstained and should_abstain
            abstain_fp += abstained and not should_abstain
            abstain_fn += not abstained and should_abstain
            answered += not abstained
            # Match source clause IDs, not publication recency. Gold supplies applicable evidence.
            cited = {x["clause_id"] for c in pred["evidence"] for x in c["citations"]}
            gold = set(r.get("required_citation_ids", []))
            if gold:
                evidence_recall.append(len(cited & gold) / len(gold))
            stale_flag = bool(set(r.get("outdated_citation_ids", [])) & cited)
            # A base citation retained as provenance is not stale by itself: test obsolete rule text.
            stale_flag = stale_flag and any(s.casefold() in pred["answer"].casefold()
                                           for s in r.get("obsolete_answer_fragments", []))
            stale += stale_flag
            matched = all(s.casefold() in pred["answer"].casefold() for s in r.get("required_answer_fragments", []))
            forbidden = any(s.casefold() in pred["answer"].casefold() for s in r.get("forbidden_answer_fragments", []))
            ok = abstained if should_abstain else (not abstained and matched and not forbidden and gold <= cited)
            correct += ok
            if r.get("stratum") == "unchanged":
                unchanged_n += 1
                unchanged_correct += ok
            results.append({"id": r["id"], "mode": mode, "rubric_pass": bool(ok),
                            "family_id":r.get("family_id","synthetic-demo-family"),"stratum":r.get("stratum","unspecified"),
                            "outdated_rule": stale_flag, "prediction": pred})
        ratio = lambda a,b: a / b if b else None
        totals[mode] = {"n": len(rows), "extractive_rubric_accuracy": correct / len(rows),
            "outdated_rule_rate_all": stale / len(rows), "outdated_rule_rate_answered": ratio(stale, answered),
            "coverage": answered / len(rows), "abstention_precision": ratio(abstain_tp, abstain_tp+abstain_fp),
            "abstention_recall": ratio(abstain_tp, abstain_tp+abstain_fn),
            "required_evidence_recall": ratio(sum(evidence_recall),len(evidence_recall)),
            "questions_with_required_evidence": len(evidence_recall),
            "mean_latency_ms":sum(latencies)/len(latencies),
            "unchanged_preservation_accuracy": ratio(unchanged_correct,unchanged_n)}
    source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob("*.py"))}
    report = {"dataset": str(dataset), "dataset_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
              "corpus_sha256": corpus_fingerprint(store),"source_sha256":source_hashes,
              "environment": {"python": platform.python_version(), "engine": version("sebi-clause-engine")},
              "split":split if frozen else "unfrozen_exploratory",
              "split_manifest":frozen,
              "risk_coverage_operating_points":risk_coverage(results),
              "paired_comparisons":{m:cluster_bootstrap(results,"clause_selective",m) for m in ["ordinary","interval","temporal_rerank","clause"]},
              "synthetic": any(r.get("label_status") == "synthetic" for r in rows),
              "limitations": "Substring+evidence rubric is not general semantic/legal correctness. Human adjudication required for publication.",
              "summary": totals, "predictions": results}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return totals


def score_amendments(predictions: list[dict], gold: list[dict]):
    """Exact event tuple P/R/F1; review status is not part of extraction scoring."""
    fields = ("source_document_id", "source_clause_id", "target_document_id", "target_clause_id", "operation", "effective_date")
    tuples = lambda rows: {tuple(r.get(f) for f in fields) for r in rows if r.get("operation") != "reference"}
    p, g = tuples(predictions), tuples(gold)
    tp = len(p & g)
    precision, recall = (tp/len(p) if p else None), (tp/len(g) if g else None)
    return {"exact_precision": precision, "exact_recall": recall,
            "exact_f1": 2*tp/(len(p)+len(g)) if p or g else None,
            "true_positive": tp, "predicted": len(p), "gold": len(g)}
