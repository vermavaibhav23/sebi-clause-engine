# Build verification — 29 October 2026, version 0.2.0

## Verified software and data preparation

- **62 tests passed** in the final run, including downloaded-PDF integration, temporal boundaries, unchanged provisions, uncertainty gates, independent annotation merge, adjudication, calibration-family exclusion and API checks.
- The browser review page was opened and question navigation exercised. It displays 50 draft questions, dated source anchors, blank review fields and 0 completed human reviews. Preview: `review-preview.png`.
- The research server runs locally at `http://127.0.0.1:8001/`, with the reviewer form at `/annotate` and API docs at `/docs`.
- `runtime/research.sqlite` contains **22 official SEBI PDFs, 809 auto-extracted clause/table segments and 27 proposed relationships**, including non-operative references. These counts are not extraction-accuracy claims. **Zero real events are approved.**
- `runtime/sebi.sqlite` preserves the earlier parse of the expanded corpus. Collection inventories retain failures and missing metadata rather than silently manufacturing documents.
- The revised parser fixes observed false boundaries caused by wrapped years and clause references. It has regression coverage; general extraction accuracy still requires annotation.
- Seven extractive modes share the evaluation interface. The temporal reranker is a documented paper-inspired adaptation, not a published-system reproduction.
- Independent review packets, source/question hashes, separate adjudication provenance, frozen family splits, paired cluster-bootstrap support and explicitly labelled synthetic stress conditions are implemented.
- Initial clause-date reviews preserve source text and audit the reviewer/evidence. Later amendments must remain separate events rather than rewriting original dates.

One dependency warning remains: Starlette deprecates its httpx-based TestClient adapter. It did not cause a test failure.

## What the controlled checks actually show

`runtime/research_checks/summary.json` records four conditions, each with four fictional questions in one family. The unreviewed-scope UI-policy case is excluded from comparisons to avoid artificially favouring our gate.

| Condition | Observed behaviour | Interpretation |
|---|---|---|
| Clean reviewed inputs | Interval and both clause modes tie on the fixture rubric | No demonstrated advantage over the strong interval control |
| Known unresolved event | Whole-scope gate abstains broadly; selective gate retains one answer; interval does better on this fixture | Coverage tradeoff, not a uniform improvement |
| Amendment absent from event data | All modes can return an obsolete rule | Missing amendments defeat reasoning over observed events |
| Wrong effective date | Structured modes make a temporal error | Accurate metadata is a substantive dependency |

These are software falsification checks, **not SEBI accuracy results**. No statistical or publication claim is based on them.

## Publication readiness

The deliverable is now a more reproducible research-validation platform. It is **not yet a validated publishable result**, and it has not been shown to outperform recent published work.

Required human work: two independent source reviews, domain-informed adjudication where interpretation is needed, a reviewed event/date/chain ledger, and audited family definitions. The 50 questions are drafts and may need revision or rejection. The 22 documents are not a completeness certificate.

Required experimental work: a frozen real benchmark with enough independent families, a justified published-method comparison, automatic-versus-corrected extraction conditions, blinded semantic answer assessment and correction-effort measurement. Bootstrap intervals are suppressed for too few families; this does not make small samples adequate.

Current defensible contribution candidate: **an independently annotated SEBI benchmark and an empirical study of amendment extraction errors propagating into applicable-evidence retrieval**. SAT-Graph, TimelyRAG, existing SEBI lineage software, Legal Rule Auditor and FR-AMD overlap major components. No claim of first temporal graph, first amendment benchmark or novel abstention mechanism is supported.

See `REVIEW_PLAN.md` for roles, calibration, reviewer instructions, conflict handling and merge commands; `STUDY_PROTOCOL_V2.md` for hypotheses and decision gates; `RESEARCH_PROTOCOL.md` for the literature comparison.
