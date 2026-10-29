# SEBI Clause Evidence Engine

A local, CPU-only research prototype for **clause-level amendment resolution and evidence retrieval**. Python + FastAPI + SQLite + pdfplumber + BM25. No API key, GPU, vector database, or cloud service is required.

**Public repository contents:** source code, tests, research protocols, official source URL manifests, synthetic fixtures and blank/AI-draft review packets. Local databases, downloaded PDFs, environment files and completed human reviews are not included. Corpus counts below describe the development collection; a fresh clone must download and ingest sources. No independently verified benchmark or real-data performance claim is released.

## What is working

- PDF ingestion with immutable SHA-256 provenance, numbered clause segmentation and table-row extraction.
- Conservative amendment proposals, separate human review, and an append-only review audit.
- Reviewed replacement, insertion, deletion, full supersession and non-operative reference events.
- Date-specific snapshots with separate publication/knowledge and effective-date cutoffs.
- Preservation of unchanged clauses, sequential edits, and citations to original and amending evidence.
- Abstention on unresolved events, missing targets, conflicting edits and unreviewed corpus scope.
- Extractive evidence APIs, a small browser workbench and interactive OpenAPI documentation.
- Seven retrieval/comparison modes, including an independent validity-interval control and an experimental query-specific uncertainty gate.
- Independent annotation form, disagreement/adjudication workflow, family-level splits and paired cluster-bootstrap support.

**Research status:** the revised research database contains **22 official PDFs, 809 automatically extracted clause/table segments and 27 proposed relationships** (including references). There are **zero approved real events and zero independently verified QA labels**. Fifty AI-drafted questions and two blank review packets are ready. The collection is not certified complete. This is a validation platform, not a proven new algorithm or a finished publishable benchmark.

Start with the [practical review plan](docs/REVIEW_PLAN.md), [current study protocol](docs/STUDY_PROTOCOL_V2.md), [baseline specifications](docs/BASELINES.md) and [build status](docs/BUILD_STATUS.md). No synthetic score should be reported as a SEBI research result.

## Run on Windows

Open PowerShell in this project folder. Python 3.11 or newer is required. If the existing `.venv` works on this computer, skip installation.

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.venv\Scripts\python.exe -m pip install --no-deps -e .
```

Start the **synthetic demo**, kept separate from real circulars:

```powershell
.venv\Scripts\python.exe -m sebi_engine.cli --db runtime/demo.sqlite demo
$env:SEBI_DB = "runtime/demo.sqlite"
.venv\Scripts\python.exe -m uvicorn sebi_engine.api:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000> or <http://127.0.0.1:8000/docs>. Select `DEMO-BASE`, tick the reviewed-scope checkbox, and retrieve the disclosure threshold. On `2024-03-15` it is **10 units**; on `2024-04-02` it is **20 units**. Ask about retention to see **5 years** preserved. These are fictional test rules, not SEBI requirements. Stop the server with Ctrl+C.

Convenience scripts are also provided: `scripts/run-demo.ps1`, `scripts/run-pilot.ps1` and `scripts/run-research.ps1`. The research script defaults to port 8001; none changes PowerShell execution policy.

## Review the expanded research corpus

For a fresh clone, install the project as above, then rebuild the source collection from the explicit official manifests:

```powershell
.venv\Scripts\python.exe -m sebi_engine.cli --db runtime/research.sqlite fetch-pilot
.venv\Scripts\python.exe -m sebi_engine.cli --db runtime/research.sqlite fetch-pilot --manifest data/expanded_sources.json
.venv\Scripts\python.exe -c "from sebi_engine.store import Store; from sebi_engine.extract import propose; s=Store('runtime/research.sqlite'); [propose(s,d.id) for d in s.documents()]"
```

Inspect every download result for errors; source availability can change. These commands create machine proposals only. Review packets refer to the `numbered-v2` parse; confirm that source bytes and clause IDs match before using the supplied anchors. Keep completed reviewer exports in `reviews-private/`, outside the tracked blank templates.

The existing `runtime/research.sqlite` uses the revised numbered-clause parser; `runtime/sebi.sqlite` preserves the earlier parse. Do not reparse a frozen reviewed corpus in place.

```powershell
$env:SEBI_DB = "runtime/research.sqlite"
.venv\Scripts\python.exe -m uvicorn sebi_engine.api:app --host 127.0.0.1 --port 8001
```

Open <http://127.0.0.1:8001/annotate> for the independent reviewer form or <http://127.0.0.1:8001/> for the workbench. Each reviewer uses a separate profile or packet copy, reads official source PDFs and exports their own JSONL. The form saves locally, not to the server. It does not authenticate identities. Do not mark an AI-generated answer as independently reviewed.

Source manifests are `data/pilot_sources.json`, `data/collection_sources.json` and `data/expanded_sources.json`; collection provenance and failures are in `runtime/collection/inventory.json`. The expanded collection covers related KYC/KRA validation, cybersecurity and digital-onboarding topics. Some referenced predecessors still need collection or metadata review.

Collection/import scripts are `scripts/collect_official.py`, `scripts/import_collection.py` and `scripts/rebuild_research.py`. The prepared question and blank reviewer packets are under `data/review_packets/`; regeneration refuses to overwrite existing question packets. Follow the review plan before compiling labels or freezing splits.

## Work with the official seed corpus

```powershell
.venv\Scripts\python.exe -m sebi_engine.cli fetch-pilot
.venv\Scripts\python.exe -m sebi_engine.cli extract "SEBI/HO/MIRSD/SECFATF/P/CIR/2024/41"
.venv\Scripts\python.exe -m sebi_engine.cli coverage
$env:SEBI_DB = "runtime/sebi.sqlite"
.venv\Scripts\python.exe -m uvicorn sebi_engine.api:app --host 127.0.0.1 --port 8001
```

The source manifest is `data/pilot_sources.json`. Raw PDFs are retained under `runtime/pdfs/`. Repeated ingestion of the same circular and bytes is idempotent; different bytes under an existing ID are rejected. The downloader makes no source content up when a download fails.

The real May 2024 replacements have **unknown effective dates in the annotation**, deliberately. A deadline to update technical systems is not automatically an amendment commencement date. The UI will abstain while these proposals are unreviewed, even if the scope checkbox is checked. Do not approve them simply to obtain an answer.

`GET /coverage` lists missing-reference candidates. It scans modern identifiers only and does not certify completeness. The KYC master circular's appendix supplies additional older circulars for expansion; forward amendments must also be searched independently. See [pilot and research protocol](docs/RESEARCH_PROTOCOL.md).

`data/pilot_expansion_candidates.json` contains 29 extracted appendix rows as collection leads with page/clause anchors. These are not 29 downloaded or verified circulars; merged cells and identifiers require source review.

## API workflow

| Endpoint | Purpose |
|---|---|
| `POST /ingest` | Multipart PDF and explicit document metadata JSON |
| `GET /documents`, `GET /clauses?document_id=...` | Inspect imported sources and exact clause IDs |
| `POST /extract?document_id=...` | Propose typed amendments; no auto-approval |
| `GET /amendments`, `POST /amendments` | Inspect or manually create a proposal |
| `POST /amendments/{id}/review` | Correct target/operation/text/date, approve or reject, record rationale |
| `POST /resolve` | Resolve a bounded snapshot with provenance and issues |
| `POST /query` | Return extractive evidence or insufficient evidence |
| `GET /coverage`, `GET /audit` | Review corpus leads and annotation history |
| `POST /clauses/review-date` | Audit an original clause's initial date using same-document evidence |
| `GET /research-status` | Inspect current database counts and comparison modes |
| `GET /annotation-questions`, `GET /research-packet/{name}` | Read draft questions or download whitelisted packets |

Example query body:

```json
{"question":"What is the disclosure threshold?","as_of":"2024-04-02","known_at":"2024-04-02","scope_document_ids":["DEMO-BASE"],"scope_reviewed":true,"baseline":"clause","top_k":1}
```

Scope contains the **base documents whose provisions are being resolved**. Imported events targeting those bases are applied automatically. Do not select an amending circular as another base merely because it supplies evidence: that can duplicate operative text. After full supersession, the successor must be explicitly selected when its own provisions are needed; the engine does not invent a clause correspondence.

`as_of` asks which provisions apply on a date; `known_at` limits which published evidence is available. It defaults to `as_of`. A later `known_at` can support retrospective reconstruction, subject to reviewed effective dates. These are corpus-level dates, not personalized compliance advice.

For an amendment to a previously inserted provision, use the logical ID `insert::<insertion-event-id>`. Its insertion must already be approved and have an earlier effective date. Same-date conflicting operations are deliberately unresolved; ordering them requires further evidence.

## Tests and evaluation

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m sebi_engine.cli --db runtime/demo.sqlite evaluate data/synthetic_qa.jsonl --allow-synthetic --output runtime/synthetic-evaluation.json
.venv\Scripts\python.exe -m sebi_engine.cli export --output runtime/annotations.json
```

The three official-PDF integration tests skip when the seed PDFs have not been downloaded into `runtime/pdfs/`. A code-only checkout runs the remaining offline tests; the recorded 62-test development run included those PDFs.

The seven modes are ordinary BM25, recency-first, document supersession, independent interval filtering, a TimelyRAG-inspired reranker, whole-scope clause resolution and query-specific clause resolution. All are extractive and use the same top-k setting. The reranker is explicitly an adaptation, **not a faithful reproduction or a demonstrated improvement over TimelyRAG**. `score_amendments()` exposes exact event tuple precision/recall/F1, including dates; the extractor intentionally leaves dates for review.

Run `.venv\Scripts\python.exe scripts/run_research_checks.py` for four synthetic metadata conditions. Reports go to `runtime/research_checks/`. The clean fixture ties the strong interval baseline; an unobserved amendment defeats all modes. These counterexamples prevent overclaiming from the demo.

The CLI also provides `compile-benchmark`, `freeze-split` and evaluation with `--split-manifest`. Reserve every calibration family with repeated `--development-family` options when freezing splits. The compiler retains independent review hashes and requires separate adjudication for disagreements. Real evaluation remains pending human labels and a frozen corpus.

The evaluator rejects unverified real labels and requires two named reviewers. This is a data-schema check, not proof that review occurred. Actual source review and adjudication are required. Its substring-and-citation rubric is a software-level approximation; real answer correctness needs a prespecified human rubric. Metrics separate outdated **rule usage** from citation age and include unchanged-provision preservation, abstention and coverage. See `data/annotation_example.json` for a draft annotation worksheet.

## Important implementation boundaries

- Output is source **evidence**, not LLM-generated legal reasoning. BM25 term overlap alone does not establish that an answer is complete. Multi-hop synthesis, semantic adequacy calibration and a trained relevance gate are future work.
- Clause boundaries, repeated numbering, merged tables and footnotes need manual review. Table rows are extracted with page geometry, but table-cell amendment alignment and inherited multi-page headers are not solved.
- Extraction recognizes a small set of explicit English drafting patterns. References to absent documents appear in the coverage inventory, but extracting events from missing originals and discovering forward amendments remain manual.
- Scope completeness is a caller acknowledgement, not persistent independent certification. An undetected amendment cannot trigger the unresolved-event gate. Whole-scope gating can suppress unrelated answers; the experimental selective gate can instead miss relevant implicit dependencies. Neither makes an incomplete corpus complete.
- There is no OCR, authenticated multi-user workflow, automated legal effective-date inference, savings-clause reasoning, or production deployment hardening. Keep the server bound to loopback.
- Models permit the five operation types, but automatic extraction does not reliably populate every field (insertion text/new labels in particular). Review supplies these fields.
- Baselines are engineering controls, not claimed reproductions of SAT-Graph, Apofasi or TimelyRAG. The paper must add a relevant strong temporal comparison before claiming improvement over prior work.

The next milestone is independent review of the collected documents and drafted questions, followed by a frozen real-data evaluation. See [current protocol](docs/STUDY_PROTOCOL_V2.md) and [review plan](docs/REVIEW_PLAN.md). The [initial protocol](docs/RESEARCH_PROTOCOL.md) retains the literature comparison and six-month plan with current-state amendments.
