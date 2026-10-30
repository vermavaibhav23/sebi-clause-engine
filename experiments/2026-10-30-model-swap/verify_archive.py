"""Validate saved experiment artifacts offline; this does not rerun inference."""
from collections import defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODEL = ROOT / "sebi_model_swap"
PILOT = ROOT / "sebi_pilot"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    manifest = read_json(MODEL / "manifest.json")
    require(manifest["pre_score_hashes"] == read_json(MODEL / "pre_score_hashes.json"),
            "Frozen manifests disagree")
    for name, directory in [("run.py", MODEL), ("protocol.txt", MODEL),
                            ("gold.json", PILOT), ("documents.json", PILOT)]:
        digest = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        require(digest == manifest["pre_score_hashes"][name], f"Hash mismatch: {name}")

    questions = read_json(PILOT / "gold.json")
    gold = {q["id"]: q for q in questions}
    documents = read_json(PILOT / "documents.json")
    pages = {f"{d['id']}:{i+1}": d["date"] for d in documents
             for i in range(len(d["pages"]))}
    require(len(gold) == len(questions) == 72, "Question IDs/count differ")
    require(len(documents) == 8 and len(pages) == 70, "Corpus count differs")
    for q in questions:
        require(bool(q["evidence"]) and all(p in pages and pages[p] <= q["date"]
                for p in q["evidence"]), f"Invalid reference evidence: {q['id']}")

    rows = read_csv(MODEL / "retrieval_predictions.csv")
    pairs = read_csv(MODEL / "neural_pair_scores.csv")
    require(len(rows) == 672 and len(pairs) == 240, "Unexpected record count")
    chosen = set(range(6, 11)) | set(range(21, 26)) | set(range(41, 46))
    chosen |= {51, 52, 54, 56, 57, 59, 60, 62, 69}
    focused = {f"Q{i:03d}" for i in chosen}
    controls = {"BM25_date_filter", "phase_expansion_BM25", "phase_expansion_RRF"}
    methods = controls | {"LaMini_rerank", "BM25_LaMini_RRF"}
    expected_keys = {(s, method, q, k) for s, ids, ms in
                     [("all72", set(gold), controls), ("focused24", focused, methods)]
                     for method in ms for q in ids for k in (3, 5)}
    indexed = {}
    groups = defaultdict(list)
    families = defaultdict(list)
    for row in rows:
        qid, method, dataset, k = row["id"], row["method"], row["evaluation_set"], int(row["k"])
        key = (dataset, method, qid, k)
        require(key not in indexed, f"Duplicate prediction: {key}")
        indexed[key] = row
        q, got = gold[qid], row["retrieved"].split("|")
        require(len(set(got)) == len(got) == k, f"Invalid retrieval budget: {key}")
        require(row["group"] == q["group"], f"Family mismatch: {key}")
        require(all(p in pages and pages[p] <= q["date"] for p in got),
                f"Unknown/future evidence: {key}")
        refs = set(q["evidence"])
        success, recall = int(refs <= set(got)), len(refs & set(got)) / len(refs)
        require(success == int(row["all_required"]) and
                math.isclose(recall, float(row["required_page_recall"])), f"Metric mismatch: {key}")
        groups[(dataset, method, str(k))].append((success, recall))
        families[(dataset, q["group"], method, str(k))].append((success, recall))
    require(set(indexed) == expected_keys, "Missing/unexpected prediction rows")

    for filename, fields, grouped in [
        ("summary.csv", ("evaluation_set", "method", "k"), groups),
        ("by_family.csv", ("evaluation_set", "group", "method", "k"), families),
    ]:
        summary = read_csv(MODEL / filename)
        require(len(summary) == len(grouped), f"Aggregate count mismatch: {filename}")
        seen = set()
        for row in summary:
            key = tuple(row[f] for f in fields)
            require(key in grouped and key not in seen, f"Aggregate key mismatch: {filename}")
            seen.add(key)
            values = grouped[key]
            for i, field in enumerate(("all_required", "required_page_recall")):
                require(math.isclose(sum(v[i] for v in values) / len(values), float(row[field])),
                        f"Aggregate metric mismatch: {filename}, {key}, {field}")

    pair_groups = defaultdict(list)
    for row in pairs:
        qid, page = row["id"], row["page"]
        require(qid in focused and page in pages and pages[page] <= gold[qid]["date"],
                "Invalid model candidate")
        require(0 <= float(row["yes_probability"]) <= 1, "Invalid model score")
        require(row["truncated"] == str(int(row["input_tokens"]) > 512), "Truncation mismatch")
        pair_groups[qid].append(row)
    require(set(pair_groups) == focused, "Missing model query")
    ceiling = {}
    for qid, candidates in pair_groups.items():
        original = [p["page"] for p in candidates]
        require(len(set(original)) == len(original) == 10, "Invalid candidate count")
        neural = [p["page"] for p in sorted(candidates, key=lambda p: -float(p["yes_probability"]))]
        score = dict.fromkeys(original, 0.0)
        for order in (original, neural):
            for pos, page in enumerate(order):
                score[page] += 1 / (60 + pos + 1)
        fused = sorted(score, key=lambda page: -score[page])
        for method, order in [("BM25_date_filter", original), ("LaMini_rerank", neural),
                              ("BM25_LaMini_RRF", fused)]:
            for k in (3, 5):
                require(indexed[("focused24", method, qid, k)]["retrieved"].split("|") == order[:k],
                        f"Ranking mismatch: {qid}, {method}, {k}")
        ceiling[qid] = int(set(gold[qid]["evidence"]) <= set(original))
    saved_ceiling = read_csv(MODEL / "candidate_ceiling.csv")
    require(len(saved_ceiling) == 24 and
            {r["id"]: int(r["all_required_at10"]) for r in saved_ceiling} == ceiling,
            "Candidate ceiling mismatch")
    require(sum(r["truncated"] == "True" for r in pairs) == manifest["truncated_pairs"] == 113,
            "Truncation count differs")
    audit = read_json(MODEL / "audit.json")
    counts = {method: sum(int(indexed[("focused24", method, qid, 5)]["all_required"])
                         for qid in focused) for method in sorted(methods)}
    require(counts == audit["focused24_at5"], "Audit counts disagree")
    require(sum(ceiling.values()) == audit["candidate_ceiling_at10"] == 16, "Audit ceiling differs")
    print("PASS: frozen hashes, 672 predictions, 240 model pairs, dates, metrics, rankings and aggregates")
    for method, count in counts.items():
        print(f"{method}: {count}/24 at five pages")
    print("No inference rerun or independent label review is implied by this verification.")


if __name__ == "__main__":
    main()
