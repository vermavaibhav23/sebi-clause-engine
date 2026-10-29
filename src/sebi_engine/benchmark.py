"""Independent annotation merge and family-level frozen splits. No AI gold labels."""
import hashlib
import json
from pathlib import Path
import random
import re

STRATA={"changed","unchanged","dependent_provision","date_sensitive","date_extension","unanswerable"}


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path, rows):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in rows),encoding="utf-8")


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def corpus_fingerprint(store):
    content={"documents":[d.model_dump(mode="json") for d in store.documents()],
        "clauses":[c.model_dump(mode="json") for c in store.clauses()],
        "amendments":[e.model_dump(mode="json") for e in store.amendments()]}
    for rows in content.values():
        rows.sort(key=lambda r:r["id"])
    return digest(content)


def unique_rows(rows):
    ids=[r["id"] for r in rows]
    if len(ids)!=len(set(ids)):
        raise ValueError("Duplicate question IDs")
    return {r["id"]:r for r in rows}


def compile_reviews(questions_path, first_path, second_path, store, output, adjudication_path=None):
    if Path(output).exists():
        raise ValueError("Use a new benchmark version filename; existing benchmark is not overwritten")
    questions=unique_rows(read_jsonl(questions_path))
    reviewers=[unique_rows(read_jsonl(p)) for p in [first_path,second_path]]
    adjudications=unique_rows(read_jsonl(adjudication_path)) if adjudication_path else {}
    if any(set(r)!=set(questions) for r in reviewers):
        raise ValueError("Both independent review files must cover exactly the frozen questions")
    clauses={c.id for c in store.clauses()}
    fields=["family_id","stratum","scope_complete","should_abstain","required_citation_ids","required_answer_fragments",
            "forbidden_answer_fragments","outdated_citation_ids","obsolete_answer_fragments"]
    compiled=[]; conflicts=[]
    for key,q in questions.items():
        a,b=(r[key] for r in reviewers)
        names=[str(r.get("reviewer","")).strip() for r in [a,b]]
        if not all(names) or names[0].casefold()==names[1].casefold():
            raise ValueError(f"{key}: two distinct identified human reviewers required")
        for review in [a,b]:
            if review.get("human_attestation") is not True or review.get("completed") is not True:
                raise ValueError(f"{key}: independent human source review is incomplete")
            if review.get("question_sha256")!=digest(q):
                raise ValueError(f"{key}: question changed after review packet creation")
            if not review.get("rationale","").strip() or not review.get("family_id","").strip():
                raise ValueError(f"{key}: family assignment and evidence rationale required")
            if review.get("stratum") not in STRATA:
                raise ValueError(f"{key}: independently confirm the question stratum")
            if type(review.get("should_abstain")) is not bool:
                raise ValueError(f"{key}: explicit answerability label required")
            if type(review.get("scope_complete")) is not bool:
                raise ValueError(f"{key}: explicitly review bounded corpus completeness")
            if not review["should_abstain"] and not review["scope_complete"]:
                raise ValueError(f"{key}: cannot label an applicable answer without complete in-scope evidence")
            cited=set(review.get("required_citation_ids",[]))|set(review.get("outdated_citation_ids",[]))
            if not cited<=clauses:
                raise ValueError(f"{key}: unknown source clause IDs")
            if not review["should_abstain"] and (not review.get("required_citation_ids") or not review.get("required_answer_fragments")):
                raise ValueError(f"{key}: answerable cases need an answer rubric and source evidence")
        def canonical(value):
            return sorted(" ".join(str(x).casefold().split()) for x in value) if isinstance(value,list) else value
        different=[f for f in fields if canonical(a.get(f))!=canonical(b.get(f))]
        final=a
        adjudicated=None
        if different and key in adjudications:
            adjudicated=adjudications[key]
            if (adjudicated.get("human_attestation") is not True or not adjudicated.get("rationale","").strip()
                or not adjudicated.get("reviewer","").strip()
                or adjudicated["reviewer"].strip().casefold() in {n.casefold() for n in names}):
                raise ValueError(f"{key}: disagreement needs a distinct human adjudicator and rationale")
            if adjudicated.get("first_sha256")!=digest(a) or adjudicated.get("second_sha256")!=digest(b):
                raise ValueError(f"{key}: adjudication does not reference these original reviews")
            final=adjudicated.get("resolution",{})
            if any(f not in final for f in fields) or type(final["should_abstain"]) is not bool or type(final["scope_complete"]) is not bool:
                raise ValueError(f"{key}: incomplete adjudicated labels")
            if not final["family_id"] or final["stratum"] not in STRATA or not (set(final["required_citation_ids"])|set(final["outdated_citation_ids"]))<=clauses:
                raise ValueError(f"{key}: invalid adjudicated family/evidence")
            if not final["should_abstain"] and (not final["scope_complete"] or not final["required_citation_ids"] or not final["required_answer_fragments"]):
                raise ValueError(f"{key}: unsupported adjudicated answer")
            different=[]
        if different:
            conflicts.append({"id":key,"differing_fields":[f for f in fields if a.get(f)!=b.get(f)],
                              "first":a,"second":b,"first_sha256":digest(a),"second_sha256":digest(b),
                              "adjudication_template":{"id":key,"reviewer":"","human_attestation":False,"rationale":"",
                                  "first_sha256":digest(a),"second_sha256":digest(b),"resolution":{f:None for f in fields}}})
        else:
            compiled.append({"id":key,"label_status":"human_verified","reviewers":names,
                "query":{**q["query"],"scope_reviewed":final["scope_complete"]},**{f:final.get(f,[]) for f in fields},
                "review_provenance":{"question_sha256":digest(q),"first_sha256":digest(a),"second_sha256":digest(b),
                    "adjudication_sha256":digest(adjudicated) if adjudicated else None,
                    "adjudicator":adjudicated["reviewer"] if adjudicated else None}})
    if conflicts:
        path=Path(output).with_suffix(".conflicts.json")
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(conflicts,indent=2),encoding="utf-8")
        return {"status":"needs_adjudication","conflicts":len(conflicts),"path":str(path),"benchmark_written":False}
    write_jsonl(output,compiled)
    return {"status":"compiled","questions":len(compiled),"path":str(output),
            "notice":"Attestations record reviewer claims; software cannot authenticate human review."}


def freeze_split(dataset, output, seed=20261029, store=None, development_families=None):
    if Path(output).exists():
        raise ValueError("Existing split is frozen; choose an explicitly versioned new path")
    rows=read_jsonl(dataset); unique_rows(rows)
    if not rows or any(r.get("label_status")!="human_verified" or not r.get("family_id") for r in rows):
        raise ValueError("Freeze only independently reviewed questions with adjudicated family IDs")
    families=sorted({r["family_id"] for r in rows})
    if len(families)<3:
        raise ValueError("At least three independent families needed for train/dev/test; one chain is only a pilot")
    # Same wording at different dates cannot be placed in separately named families.
    wording={}
    for r in rows:
        text=re.sub(r"\W+"," ",r["query"]["question"].casefold()).strip()
        if text in wording and wording[text]!=r["family_id"]:
            raise ValueError("Repeated question wording crosses family assignments")
        wording[text]=r["family_id"]
    reserved=set(development_families or [])
    if not reserved<=set(families):
        raise ValueError("Unknown calibration/development family")
    eligible=[f for f in families if f not in reserved]
    if reserved and len(eligible)<2:
        raise ValueError("Calibration leaves too few untouched families for train and test")
    random.Random(seed).shuffle(eligible)
    ntest=max(1,round(.2*len(families)))
    ndev=max(0,max(1,round(.2*len(families)))-len(reserved))
    ntest=min(ntest,len(eligible)-ndev-1)
    groups={f:("test" if i<ntest else "dev" if i<ntest+ndev else "train") for i,f in enumerate(eligible)}
    groups.update({f:"dev" for f in reserved})
    manifest={"seed":seed,"dataset_sha256":hashlib.sha256(Path(dataset).read_bytes()).hexdigest(),
        "corpus_sha256":corpus_fingerprint(store) if store else None,
        "reserved_development_families":sorted(reserved),
        "family_assignments":groups,"question_assignments":{r["id"]:groups[r["family_id"]] for r in rows},
        "limitations":"Manual family IDs require dependency audit; this checks IDs and exact normalized wording, not semantic paraphrases."}
    output=Path(output); output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return manifest
