"""Reparse official sources into a separate database, preserving the original pilot."""
import json
from pathlib import Path
from sebi_engine.store import Store
from sebi_engine.ingest import ingest_pdf
from sebi_engine.extract import propose
from sebi_engine.coverage import coverage_report

ROOT=Path(__file__).resolve().parents[1]
original=Store(ROOT/"runtime"/"sebi.sqlite")
revised=Store(ROOT/"runtime"/"research.sqlite")
rows=[]
for doc in original.documents():
    if doc.kind=="synthetic":
        continue
    result=ingest_pdf(revised,ROOT/"runtime"/"pdfs"/doc.filename,doc)
    result["previous_segments"]=sum(c.document_id==doc.id for c in original.clauses())
    rows.append(result)
for doc in revised.documents():
    propose(revised,doc.id)
report={"parser":"numbered-v2","note":"Boundary sanity improvements, not measured extraction accuracy",
        "documents":rows,"coverage":coverage_report(revised)}
(ROOT/"runtime"/"research-rebuild.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps({"documents":len(revised.documents()),"segments":len(revised.clauses()),"events":len(revised.amendments())}))
