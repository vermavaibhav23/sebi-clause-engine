# Practical independent-review plan

## What help to arrange

Start with **you and one CSE teammate** as two independent source annotators. Ask your project supervisor to coordinate the process. For disputed effective dates, regulatory scope and exceptions, arrange a **separate adjudicator with relevant regulatory/compliance knowledge**. A CSE faculty member can supervise methodology but should not be assumed to be a SEBI domain expert.

No one needs to certify the whole of SEBI law. The assignment is a bounded source audit for the selected questions and dates. If domain-informed adjudication is unavailable, keep disputed applicability labels unknown and narrow the paper to literal amendment extraction/source retrieval. Do not turn uncertain interpretation into gold through majority guessing.

## Materials already prepared

- 22 official PDFs, preserved with hashes; `runtime/collection/inventory.json` records collection evidence and failures for the expansion.
- 50 **AI-drafted questions** in `data/review_packets/questions.jsonl`.
- Two blank reviewer files; no agent-created answers are presented as human labels.
- A browser form at `http://127.0.0.1:8001/annotate` when the research server is running.
- Candidate amendment and document-date review queues in `data/review_packets/`.
- Separate original and revised parsing databases: `runtime/sebi.sqlite` and `runtime/research.sqlite`.

The 50 questions include paired dates, so they are **not 50 independent observations**. They cover a few linked KYC/KRA topics, including validation, cybersecurity and digital onboarding. Family assignments are deliberately left blank. Reviewer-assigned families may turn out to be too few or too connected for a meaningful held-out study.

## Suggested schedule

| Step | Who | Work and completion criterion |
|---|---|---|
| Scope meeting | You + supervisor | Agree historical cutoff, question scope, definition of applicability and exclusions; identify adjudicator |
| Calibration | Both annotators, then adjudicator | First label six questions separately and export the original drafts; then compare them, resolve disagreements and agree annotation rules |
| Independent pass | Annotator A and B separately | Read sources, inspect complete chains, label without viewing the other's answers or model predictions |
| Disagreement review | Separate adjudicator | Resolve supported disagreements with a cited rationale; retain uncertainty where evidence is insufficient |
| Freeze | You + supervisor | Preserve original review files, merge annotations, audit families, freeze corpus/dataset/splits |
| Evaluation | Code, then blinded human answer review | Run all modes on identical frozen inputs; adjudicate output correctness without method names |

Planning estimate: allow roughly 5–10 hours per annotator for 50 questions **after** the chain ledger is prepared, plus separate time for corpus completion and adjudication. This is an estimate to test during calibration, not a promise. Log actual minutes and difficult cases.

Use these six draft cases for calibration: `kyc-01-2024-05-13`, `kyc-01-2024-05-31`, `kyc-02-2024-05-31`, `kyc-05-2024-05-31`, `kyc-12-2022-07-28` and `kyc-20-2022-07-06`. Each annotator must save their own labels before seeing the other's. Preserve those original entries; disagreements go through the separate adjudication file. Do not rewrite the two original reviews into artificial agreement after discussion.

Calibration cases belong to development; exclude them and related family variants from confirmatory test claims. If a question needs rewriting, create a versioned packet and keep it in development; never reuse old hashes or describe a discussion-derived label as an independent assessment. If family grouping leaves no independent test set, collect more independent families rather than splitting paraphrases at random.

## Instructions for each annotator

1. Open the research review form in a separate browser profile or work from your own packet copy. Enter your own identifier and load your local draft. This interface is a convenience tool, not an authenticated reviewer identity system.
2. Read the question and both dates. `as_of` is the applicability date; `known_at` is the latest publication date allowed as evidence. They need not always mean the same thing.
3. Open the seed PDF anchors. Check actual wording, page boundaries, footnotes and tables. The anchors are discovery aids, not an answer key.
4. Follow predecessors, amendments, rescissions and relevant clarifications through the cutoff. Record missing documents. An unmodified clause in one amendment is not automatically current under every later instrument.
5. Decide whether the bounded evidence chain is complete for this question. If not, do not label a confident applicable answer; explain the missing dependency or uncertainty.
6. Identify the minimal applicable evidence. Copy exact internal clause IDs from `/clauses`, record concise answer facts and any obsolete/forbidden fact. An old original citation may remain valid; age alone is not a reason to mark it outdated.
7. Assign a family ID that groups the linked provisions, versions and date variants. Independently confirm the question category (changed, unchanged, dependent, date-sensitive, date extension or unanswerable); the AI draft category is not gold. Coordinate the family-definition scheme during calibration; final assignments must be audited before splitting.
8. State your rationale, effective-date evidence, exceptions and time spent. Mark complete only after genuine source review. Export JSONL backups after each session. The browser autosaves locally and does not upload annotations to the server.

The exact-fragment rubric is for reproducible screening. It does not replace semantic evaluation: synonymous phrasing can be correct, and a passage containing the right phrase can still give an incomplete or misleading answer. Before a paper, create a blinded output-adjudication pass with a factual correctness and sufficiency rubric.

## Handling dates and original clause applicability

Do not substitute publication for commencement. The master circular and individual clauses can have different applicability dates. For an initial clause date explicitly established in the same original document, use `POST /clauses/review-date`, record source clause IDs, and supply a rationale. Explicitly unknown dates may be recorded as null. An amendment changing a date must be a separate amendment event, preserving historical knowledge cutoffs.

The 2022 validation documents distinguish the originally stated July commencement, a June extension to August, and a July extension to November. These are annotation tasks: a date appearing in the text may describe the scheduled obligation, not the date on which the amendment instruction itself became operative.

The present source packet does not certify that every required circular is present. The coverage scanner is incomplete for old identifier formats, and a master appendix connects many families. The 22-document count is a collection milestone, not a completeness certificate.

## Merge and adjudicate without rewriting independent reviews

Use a fresh, versioned output name:

```powershell
.venv\Scripts\python.exe -m sebi_engine.cli --db runtime/research.sqlite compile-benchmark data/review_packets/questions.jsonl path/to/completed-a.jsonl path/to/completed-b.jsonl --output data/benchmark-v1.jsonl
```

Incomplete reviews fail validation. Disagreements create `benchmark-v1.conflicts.json` and do not create a benchmark. Each conflict includes an adjudication template and hashes of the original reviews. Have the separate adjudicator fill a JSONL file with the resolution, identity, attestation and rationale. Preserve A and B unchanged. Then:

```powershell
.venv\Scripts\python.exe -m sebi_engine.cli --db runtime/research.sqlite compile-benchmark data/review_packets/questions.jsonl path/to/completed-a.jsonl path/to/completed-b.jsonl --adjudication path/to/adjudications.jsonl --output data/benchmark-v1.jsonl
.venv\Scripts\python.exe -m sebi_engine.cli --db runtime/research.sqlite freeze-split data/benchmark-v1.jsonl --development-family YOUR_CALIBRATION_FAMILY --output data/split-v1.json
.venv\Scripts\python.exe -m sebi_engine.cli --db runtime/research.sqlite evaluate data/benchmark-v1.jsonl --split-manifest data/split-v1.json --split test --output runtime/real-test-v1.json
```

Replace `YOUR_CALIBRATION_FAMILY` with the actual adjudicated family ID and repeat `--development-family` for every family used during calibration or tuning. Those families are forced into development; the tool rejects a split with too few untouched families. Never rename related questions to evade this check.

Those commands are the workflow, **not commands that can currently produce real results**: completed human reviews do not exist yet. The compiler checks attestations and provenance; it cannot authenticate that review occurred.

## Short brief to give your supervisor

“I have a CPU-only SEBI amendment-resolution prototype and a 22-PDF source collection. I need help validating a 50-question pilot with two independent annotators and a separate domain-informed adjudicator for disputes. The research question concerns extraction errors, unchanged-provision preservation and abstention at useful coverage. I am not claiming a new temporal graph algorithm or superiority over published systems. Can the project arrange an adjudicator and approve the annotation/split protocol before we collect final results?”

This is a draft for you to use; no message has been sent.
