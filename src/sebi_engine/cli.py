import argparse
import json
import urllib.request
from pathlib import Path
from .demo import seed_demo
from .evaluate import evaluate
from .extract import propose
from .ingest import ingest_pdf
from .models import Document
from .store import Store
from .coverage import coverage_report
from .benchmark import compile_reviews, freeze_split


def main():
    p = argparse.ArgumentParser(description="SEBI Clause Engine research tools")
    p.add_argument("--db", default="runtime/sebi.sqlite")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("demo", help="Load explicitly synthetic software fixtures")
    sub.add_parser("coverage", help="List missing-reference candidates for a human corpus audit")
    ing = sub.add_parser("ingest")
    ing.add_argument("pdf", type=Path)
    ing.add_argument("metadata", type=Path)
    ext = sub.add_parser("extract")
    ext.add_argument("document_id")
    fetch = sub.add_parser("fetch-pilot", help="Download only the small official seed manifest")
    fetch.add_argument("--manifest", type=Path, default=Path("data/pilot_sources.json"))
    ev = sub.add_parser("evaluate")
    ev.add_argument("dataset", type=Path)
    ev.add_argument("--output", type=Path, default=Path("runtime/evaluation.json"))
    ev.add_argument("--allow-synthetic", action="store_true")
    ev.add_argument("--split-manifest", type=Path)
    ev.add_argument("--split", choices=["train","dev","test"], default="test")
    compile_cmd=sub.add_parser("compile-benchmark",help="Merge independently completed human review packets")
    compile_cmd.add_argument("questions",type=Path)
    compile_cmd.add_argument("first",type=Path)
    compile_cmd.add_argument("second",type=Path)
    compile_cmd.add_argument("--output",type=Path,required=True)
    compile_cmd.add_argument("--adjudication",type=Path)
    freeze_cmd=sub.add_parser("freeze-split")
    freeze_cmd.add_argument("dataset",type=Path)
    freeze_cmd.add_argument("--output",type=Path,required=True)
    freeze_cmd.add_argument("--development-family",action="append",default=[],
        help="Reserve a calibration/tuning family for development; repeat for each family")
    export = sub.add_parser("export")
    export.add_argument("--output", type=Path, default=Path("runtime/annotations.json"))
    args = p.parse_args()
    store = Store(args.db)
    if args.command == "demo":
        result = seed_demo(store)
    elif args.command == "coverage":
        result = coverage_report(store)
    elif args.command == "ingest":
        result = ingest_pdf(store, args.pdf, Document.model_validate_json(args.metadata.read_text(encoding="utf-8")))
    elif args.command == "extract":
        result = propose(store, args.document_id)
    elif args.command == "fetch-pilot":
        result = []
        folder = store.path.parent / "pdfs"
        folder.mkdir(exist_ok=True)
        for row in json.loads(args.manifest.read_text(encoding="utf-8")):
            from urllib.parse import urlparse
            url = row["source_url"]
            host = urlparse(url).hostname
            if host not in {"www.sebi.gov.in", "sebi.gov.in"} or urlparse(url).scheme != "https":
                raise ValueError("Pilot downloader accepts only HTTPS SEBI sources")
            path = folder / row.pop("local_filename")
            try:
                if not path.exists():
                    request = urllib.request.Request(url, headers={"User-Agent": "SEBI-Research-Pilot/0.1"})
                    with urllib.request.urlopen(request, timeout=30) as response:
                        if urlparse(response.url).hostname not in {"www.sebi.gov.in", "sebi.gov.in"}:
                            raise ValueError("Unexpected redirect host")
                        raw = response.read(25*1024*1024+1)
                    if len(raw) > 25*1024*1024 or not raw.startswith(b"%PDF"):
                        raise ValueError("Invalid PDF or over 25 MB")
                    path.write_bytes(raw)
                result.append(ingest_pdf(store, path, Document(**row)))
            except Exception as exc:
                result.append({"document_id": row["id"], "error": str(exc)})
        # A failed fetch is reported; never fabricate missing source content.
    elif args.command == "evaluate":
        result = evaluate(store, args.dataset, args.output, args.allow_synthetic,args.split_manifest,args.split)
    elif args.command == "compile-benchmark":
        result=compile_reviews(args.questions,args.first,args.second,store,args.output,args.adjudication)
    elif args.command == "freeze-split":
        result=freeze_split(args.dataset,args.output,store=store,development_families=args.development_family)
    else:
        result = {"documents": [d.model_dump(mode="json") for d in store.documents()],
                  "clauses": [c.model_dump(mode="json") for c in store.clauses()],
                  "amendments": [e.model_dump(mode="json") for e in store.amendments()], "audit": store.audit()}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        result = {"exported": str(args.output)}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
