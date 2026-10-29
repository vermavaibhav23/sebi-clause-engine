# Research validation and pilot protocol

**Revision notice:** this is the initial rationale and six-month plan. [STUDY_PROTOCOL_V2.md](STUDY_PROTOCOL_V2.md), [BASELINES.md](BASELINES.md) and [REVIEW_PLAN.md](REVIEW_PLAN.md) define the current experiment and annotation workflow.

Working title: **Evaluating Clause-Level Amendment Resolution for Evidence-Grounded QA on SEBI Circulars**.

Problem statement: regulatory QA can retrieve a genuine passage that no longer expresses the applicable rule. A partial amendment changes specific provisions while leaving others intact. This project evaluates how errors in extracting and applying those changes affect date-specific evidence retrieval, and whether explicit uncertainty handling reduces incorrect rule usage while retaining useful answer coverage.

## Honest verdict

The backend is a feasible six-month engineering project on an 8 GB laptop with no GPU. A carefully annotated corpus and error-propagation study could support a research paper. Temporal graphs, clause versioning, amendment operations and SEBI retrieval are already established ideas. Their combination is not sufficient proof of method novelty. Publication is contingent on sound data, meaningful comparisons, results and venue review.

The **candidate contribution** is a reproducible empirical evaluation of *raw-PDF amendment extraction errors propagating into clause applicability and QA*, including unchanged-provision controls and incomplete-chain abstention. Compare human-corrected events, automatically extracted events and reviewed/gated events under identical retrieval conditions. This is primarily a benchmark/empirical contribution until experiments establish something more.

## Literature comparison

Sources were inspected during the build on 29 October 2026. Full methods/limitations were read where accessible; unavailable full text is explicitly marked. Venue statements attributed to authors are not independent proceedings verification.

| Work | Status and primary source | Verified scope and consequence for this project |
|---|---|---|
| SAT-Graph RAG | Published JURIX 2025 paper, DOI [10.3233/FAIA251598](https://journals.sagepub.com/doi/pdf/10.3233/FAIA251598); [extended preprint](https://arxiv.org/html/2505.00039) | Versions norms/components using causal amendment actions and preserves unchanged components. This is close conceptual prior work. The paper's evaluation is qualitative; quantitative evaluation and accurate upstream extraction remain challenges. The extended paper discusses error propagation and heterogeneous segmentation. |
| SAT-Graph implementation | [Author repository](https://github.com/hmartim/sat-graph-api) | An API specification; ingestion/parsing/persistence are consumer responsibilities. It is not evidence that a complete raw-PDF amendment extraction benchmark already ships. We have not reproduced it. |
| Apofasi | IEEE ISCAIE 2026 proceedings record, DOI [10.1109/ISCAIE68866.2026.11576429](https://ieeexplore.ieee.org/abstract/document/11576429) | Official abstract describes a temporal knowledge graph, planner, hybrid vector/graph retrieval, deterministic temporal mask and a 320-query evaluation. Full text was inaccessible during this build; exact amendment granularity and table handling remain unverified. Do not claim it lacks them. No paper-associated implementation was verified. |
| TimelyRAG | [2026 arXiv preprint](https://arxiv.org/html/2609.11572), [author implementation](https://github.com/kaist-dmlab/TimelyRAG) | Temporal validity intervals and semantic/time-aware reranking; synthetic benchmark. Real-world versioned-document evaluation is stated as future work. This supports a real-document evaluation direction, not novelty of temporal filtering. Repository configuration is not directly the lightweight CPU pipeline implemented here. |
| Asking for an Old Friend: Temporal Statutory QA | [2026 paper](https://arxiv.org/html/2605.23497); author metadata reports ICAIL 2026 acceptance | Temporal statute retrieval with RAG-kNN and RAG-ToC; 312 expert-accepted questions from a larger generated pool. Already evaluates temporal retrieval on real statutes. A real corpus alone is insufficient differentiation; partial amendment extraction errors and SEBI-specific annotation must justify the study. |
| FiscalQA | [2026 paper](https://arxiv.org/html/2608.09393); author metadata reports ICML 2026 AI4Law workshop acceptance | Versioned fiscal corpus and 209 scored questions. Public scoring/corpus resources exist; the production retriever is not fully released. Its divergence-based question selection motivates reporting balanced changed and unchanged cases rather than only cases chosen to defeat current-text retrieval. |
| Existing SEBI RAG | [Public implementation](https://github.com/opnsrcntrbtr/sebi-circular-rag), not a peer-reviewed paper | Code inspected in lineage/pipeline modules already represents amends/supersedes/references and provides time-aware handling. Do not claim that no open SEBI tool handles amendments. The open question is the end-to-end accuracy and exact provision-preservation behavior under a shared benchmark. |
| Legal Rule Auditor | Published in *Computers* 15(8), 471 (24 July 2026), [paper](https://www.mdpi.com/2073-431X/15/8/471), [author implementation](https://github.com/amakremi/LegalAuditRAG) | Lifecycle/temporal filtering, ontology constraints, output validation and audit trails already exist. The paper proposes broader domain evaluation and multiple independent annotators as future work. Its repository supplies source laws, queries and results; it has not been reproduced here. Governance/abstention alone is not our novelty. |
| FR-AMD | August 2026 open dataset release; [author's release report](https://frtracker.app/blog/fr-amd-open-benchmark), [deposit DOI](https://doi.org/10.5281/zenodo.22096638). Peer-reviewed status not established. | Reports 26,824 Federal Register amendment instructions with document splits, abstained cases and machine-based validation. The release explicitly lacks a human labeling campaign and reserves a human-verified tier for later work. Direct deposit access failed during this audit; these are release-report claims, not a verified dataset inspection. Do not claim the first amendment extraction benchmark. |

**Established:** temporal retrieval, legal version graphs, action-based modifications, preservation of unchanged components and SEBI circular lineage.

**Explicit limitations supporting investigation:** TimelyRAG's real-document extension; SAT-Graph's dependence on reliable upstream inputs and need for further quantitative evaluation. These are grounded starting points, not proof nobody has investigated this issue elsewhere.

**Inferred gap:** the inspected sources do not establish a shared, independently verified SEBI benchmark measuring extraction-to-resolution error propagation, unchanged provisions, ambiguous dates and missing chains together. This is a bounded literature-search finding, not proof of absence. FR-AMD and Legal Rule Auditor substantially overlap individual parts. Different national data alone is weak novelty: the study must reveal a transferable failure taxonomy or a useful quantified error/coverage tradeoff. Check Apofasi's full text and new releases before making a novelty claim.

**Unvalidated hypothesis:** clause-level resolution with uncertainty-aware abstention will reduce obsolete rule usage compared with the specified baselines at useful, matched coverage. It may fail because extraction/segmentation errors or an overly broad abstention gate dominate.

## Concrete official example

Narrow subject: **KYC Registration Agencies, client validation and portability**.

- [11 August 2023 circular](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2023/1691757155740.pdf), ID `SEBI/HO/MIRSD/FATF/P/CIR/2023/0144`: paragraph 13 specifies 1 September 2023 commencement and rescinds an earlier circular. This provides a real publication/effective-date difference; the earlier 2022/46 circular has now been imported, with June/July 2022 extensions.
- [12 October 2023 KYC master circular](https://www.sebi.gov.in/sebi_data/attachdocs/oct-2023/1697120943335.pdf), ID `SEBI/HO/MIRSD/SECFATF/P/CIR/2023/169`: supplies the base provisions and an appendix of older source circulars.
- [14 May 2024 amendment](https://www.sebi.gov.in/sebi_data/attachdocs/may-2024/1715693926598.pdf), ID `SEBI/HO/MIRSD/SECFATF/P/CIR/2024/41`: explicitly replaces master paragraphs 96 and 100. Paragraph 97's mobile/email verification requirement is not replaced by this circular.

For a date after the amendment is established to apply, a query about paragraph 96 should use its replacement, while a query about paragraph 97 should retain the older source. Blanket discarding of the master circular would lose paragraph 97. A genuine document-level supersession baseline should not blanket-discard it for a partial amendment either; test this instead of constructing a weak baseline.

The 2024 document's technical-system deadline is not automatically an effective date. That date remains unlabelled in the seed data. None of these statements asserts the rule's present-day status after subsequent amendments outside the corpus.

## Pilot dataset plan and decision gate

Current state: **22 official PDFs, 809 auto-extracted segments, 27 proposed relationships and 50 draft questions**. These are review inputs, not gold labels. The complete-chain criterion is still not met. Related KRA cybersecurity and digital-KYC topics supplement the validation examples.

1. Begin with the KYC master appendix and follow every relevant predecessor and later amendment for the KRA validation/portability subsection. Use official SEBI pages and PDFs; store source URLs, download timestamps in the collection log, hashes, publication dates and the exact effective-date evidence. Include several adjacent KYC chains only if needed to reach 20–30 meaningful connected documents. Do not pad with unrelated circulars.
2. Freeze a documented cutoff. A proposed historical audit window is through 31 May 2024, but this is not a legal commencement assumption. Search forward to that cutoff, not just backward references. Include master consolidation, delayed effect and explicitly unchanged controls. Exclude draft proposals as authority.
3. Create a chain ledger: circular ID, original clause key, operation, affected scope, source passage/page, date, date rationale, predecessor/successor, exceptions/savings provisions, and unresolved questions. Every expected edge must be backed by text or marked unknown.
4. Prepare 40–60 questions across changed rules, unchanged rules, just-before/after effect, missing-chain cases, ambiguous dates and negative queries. Suggested target allocation: 16 changed, 12 unchanged, 10 date-sensitive and 12 unanswerable/ambiguous; allow overlap labels but report strata separately. These numbers are a sampling plan, not observations.
5. Two reviewers independently label answers and applicable evidence. Seek domain-informed adjudication for legal interpretation. AI may draft a question or suggest a citation; it cannot verify a label. Record disagreements, resolution, reviewer IDs and whether interpretation remains uncertain. Remove or classify uncertain cases as abstention cases.
6. Keep both document-original and logical provision IDs. Old evidence is acceptable if its provision remains applicable. For replacements, store the old and new text plus operation evidence. Distinguish tables, nested clauses, partial sentences and entire-provision replacements.
7. Deliberately hide a known required document only in a labelled **controlled missing-chain experiment**. Do not present that as the natural missing-document prevalence. The resolver should be told which known dependency is missing; undiscovered amendments are a separate failure mode.

Continue beyond the pilot only if chains are reviewable, a reasonable answerable subset survives adjudication, and at least one substantive failure survives a strong temporal baseline. Failure to improve is still reportable empirical evidence if design is sound; it does not support an improved-method claim. If interpretation cannot be grounded, narrow the study to *amendment extraction and resolution correctness* instead of general QA.

## Baselines, experiments and leakage safeguards

**Implemented controls:** seven modes specified in [BASELINES.md](BASELINES.md), including an independent interval control and a documented temporal-reranking adaptation. Shared corpus and top-k; extractive outputs for all. The document baseline removes only full supersession. It preserves a partially amended document and can still retrieve stale clauses.

**Required before paper submission:** audit the temporal adaptation against the nearest feasible published approach on matched data. Read Apofasi in full when obtainable. Use an oracle event graph as an upper-bound input condition, not a competing end-to-end system. The current implementation is not a SAT-Graph or Legal Rule Auditor reproduction.

Experiments:

- Evaluate clause boundaries, operation class, target resolution and effective-date extraction against independently reviewed annotations. Report exact event-tuple F1 plus component-level precision/recall and errors by operation. Unknown dates count as missing predictions, not correct automatic extractions.
- Compare oracle events, unreviewed automatic extraction and reviewed events to isolate error propagation. Do not silently give a proposed method human-corrected inputs while competitors receive noisy text.
- Measure answer correctness with a human rubric; outdated **rule usage**; required-evidence precision/recall; unchanged-provision preservation; appropriate abstention and answer coverage. Report risk-coverage curves when a calibrated gate exists. The current hard gate has only one operating point.
- Include full-chain versus controlled missing-chain conditions and changed versus unchanged strata. Record latency, peak memory, corpus size and dependency versions on the actual laptop.
- Report paired per-question differences and uncertainty clustered by amendment family. Forty to sixty pilot questions are for feasibility; they do not justify broad claims or fine-grained significance estimates. Increase independent amendment families before confirmatory evaluation.

Split at the **amendment-family** level, so related versions, clauses and paraphrased questions do not cross train/dev/test. Freeze split manifests before tuning parsing or thresholds. Keep later-dated texts inaccessible to historical-knowledge queries. Separate retrospective applicable-date evaluation from what was known then. Report manual correction time and use the same allowed evidence for all modes. Keep extraction-gold data separate from retrieval inputs except in explicitly labelled oracle experiments. Re-run the entire frozen benchmark rather than publishing selected successes.

## Architecture and remaining engineering

Single process: PDF import → immutable source store → clause/table extraction → amendment proposals → reviewed event log → date-specific clause projection → BM25 retrieval → extractive response with provenance. SQLite stores JSON-validated records and audit events; the browser is a thin client of FastAPI. Deterministic resolution is isolated from retrieval so it can be tested independently.

Modules: `ingest.py` (PDF/provenance), `extract.py` (drafting patterns), `coverage.py` (audit leads), `service.py` (review validation), `resolve.py` (event projection), `search.py` (retrieval/abstention), `evaluate.py` (reproducible scoring), `api.py`/`cli.py` (interfaces), `store.py` (persistence). Models and schemas are in `models.py`.

Prioritized next changes after annotation: reviewed clause/table alignment; durable scope review with evidence; extraction confidence/calibration; strong temporal baseline; optional small CPU embedding model only if BM25 misses relevant evidence. Keep a fixed retriever across temporal comparisons. No generative model is needed to test applicability correctness. Add generation later only with a separate correctness and grounding evaluation.

## Six-month plan

| Phase | Deliverable and exit condition |
|---|---|
| Weeks 1–2 | Literature audit, three-source smoke test, define target scope; no unsupported novelty claim |
| Weeks 3–4 | 20–30 connected documents and 40–60 pilot questions; independent annotation and chain-completeness assessment |
| Month 2 | Improve segmentation and event extraction using development families; freeze target/operation/date schema |
| Month 3 | Resolve repeated amendments, tables and exceptions in the chosen scope; review workflow and correctness tests |
| Month 4 | Add strong temporal baselines and controlled input-quality experiments; freeze test split and evaluation rubric |
| Month 5 | Run adjudicated evaluation, paired uncertainty analysis, failure taxonomy, memory/latency measurements |
| Month 6 | Reproducibility package, artifact documentation, dissertation and appropriately scoped paper submission |

An empirical paper or tool/demo paper is the honest initial target. IEEE is a publisher, not an acceptance criterion; choose an actual venue based on its scope and artifact expectations after the evidence is available. No acceptance or performance improvement is guaranteed.
