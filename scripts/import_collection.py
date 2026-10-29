"""Import collected bytes without promoting metadata or events to verified labels."""
import json
from pathlib import Path
import shutil
from sebi_engine.store import Store
from sebi_engine.models import Document
from sebi_engine.ingest import ingest_pdf
from sebi_engine.extract import propose
from sebi_engine.coverage import coverage_report

ROOT=Path(__file__).resolve().parents[1]
store=Store(ROOT/"runtime"/"sebi.sqlite")
folder=ROOT/"runtime"/"collection"
results=[]
for row in json.loads((ROOT/"data"/"expanded_sources.json").read_text(encoding="utf-8")):
    filename=row.pop("local_filename")
    target=ROOT/"runtime"/"pdfs"/filename
    if not target.exists():
        shutil.copyfile(folder/filename,target)
    try:
        results.append(ingest_pdf(store,target,Document(**row)))
    except Exception as exc:
        results.append({"document_id":row["id"],"error":str(exc)})
for doc in store.documents():
    propose(store,doc.id)
report={"imports":results,"coverage":coverage_report(store)}
(ROOT/"runtime"/"collection-import.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps({"documents":len(store.documents()),"clauses":len(store.clauses()),
    "events":len(store.amendments()),"import_errors":[r for r in results if "error" in r]},indent=2))
