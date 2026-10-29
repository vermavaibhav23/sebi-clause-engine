"""Controlled SOFTWARE stress checks. Never report these as SEBI research results."""
import json
from pathlib import Path
import tempfile
from sebi_engine.demo import seed_demo
from sebi_engine.store import Store
from sebi_engine.models import Amendment
from sebi_engine.evaluate import evaluate
from sebi_engine.benchmark import read_jsonl,write_jsonl

ROOT=Path(__file__).resolve().parents[1]
out=ROOT/"runtime"/"research_checks"
out.mkdir(exist_ok=True)
summary={}
with tempfile.TemporaryDirectory(prefix="sebi-research-") as tmp:
    dataset=Path(tmp)/"stress_questions.jsonl"
    # Scope-checkbox policy is a UI contract test, not a fair comparative research case.
    write_jsonl(dataset,[r for r in read_jsonl(ROOT/"data"/"synthetic_qa.jsonl") if r["id"]!="unreviewed-scope"])
    for condition in ["clean_reviewed_fixture","known_uncertainty","unobserved_amendment","wrong_effective_date"]:
        store=Store(Path(tmp)/(condition+".sqlite")); seed_demo(store)
        event=next(e for e in store.amendments() if e.id=="demo-replace").model_dump()
        if condition=="known_uncertainty":
            event.update(id="uncertain-replacement",status="proposed",effective_date=None,reviewer=None)
            store.put_amendment(Amendment(**event))
        elif condition=="unobserved_amendment":
            # Explicit test-only omission. Neither gate can discover a missing unknown event.
            with store.connect() as db:
                db.execute("DELETE FROM amendments WHERE id=?",("demo-replace",))
        elif condition=="wrong_effective_date":
            event["effective_date"]="2024-03-01"
            event["review_note"]="SYNTHETIC CORRUPTION: wrong publication-as-effective-date assumption"
            store.put_amendment(Amendment(**event),replace=True)
        scores=evaluate(store,dataset,out/(condition+".json"),True)
        summary[condition]={k:{m:v[m] for m in ["extractive_rubric_accuracy","coverage","outdated_rule_rate_all"]} for k,v in scores.items()}
report={"synthetic":True,"purpose":"Sanity checks and falsification, not research-performance evidence",
        "conditions":summary,"limitations":"Four hand-constructed questions in one fictional family; scope-checkbox policy test excluded; no statistical generalization."}
(out/"summary.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2))
