# Baseline specification and comparison boundaries

All modes run on CPU and return extractive passages. They share the selected base-document scope, publication cutoff, query text and top-k. Results are not directly comparable to another paper's published score on a different dataset. The code uses no LLM judge and no API model.

| Mode | Inputs/behaviour | Important boundary |
|---|---|---|
| `ordinary` | BM25 on raw base and connected amendment clauses | Temporal applicability unresolved |
| `recency` | Publication-date-first ordering among lexical hits | Publication is not commencement |
| `document` | Raw retrieval after approved full supersession | Partial amendments do not discard the whole original |
| `interval` | Independently builds versions from reviewed events, then filters `[start,end)` | Strong structured temporal control; does not call `resolve()` |
| `temporal_rerank` | BM25 candidate pool plus interval-distance affinity | Explicit paper-inspired adaptation, not author-code reproduction |
| `clause` | Deterministic event projection, whole-scope uncertainty gate | One unresolved event can suppress unrelated answers |
| `clause_selective` | Projection plus query-specific uncertainty gate and explicit clause-reference traversal | Experimental heuristic; no guarantee that retrieval or dependency extraction is complete |

## Temporal reranking adaptation

Primary reference: [TimelyRAG preprint, Sections 3.1–3.3](https://arxiv.org/html/2609.11572). Author code inspected: [time_scores.py](https://github.com/kaist-dmlab/TimelyRAG/blob/main/time_scores.py), [alpha.py](https://github.com/kaist-dmlab/TimelyRAG/blob/main/alpha.py), [pipeline.py](https://github.com/kaist-dmlab/TimelyRAG/blob/main/pipeline.py).

Our independently written adaptation uses a BM25 candidate pool of 100, min-max-normalized semantic scores and temporal distances, exponential affinity with gamma=2, and a **fixed** temporal weight of 0.5. These are transparent starter settings, not tuned published hyperparameters. The API exposes weight and pool size; tune only on development data and freeze them before a test run.

The main temporal term is distance from query applicability date to a clause validity interval. Missing interval starts fall back to publication for this soft control only. Three auxiliary day-distance terms have weight 0.1. Publication is used as corpus availability (`DIT`), and `known_at` as query knowledge cutoff (`QIT`). An end date is exclusive: the first expired day incurs positive distance. Unknown base dates are excluded from the strict `interval` control.

Differences from the publication/released implementation:

- Fixed weighting replaces the paper's query-adaptive weighting and the repository's heuristic selection logic.
- We use explicit API dates and reviewed event metadata; no free-text temporal-expression normalization is reproduced.
- Author source code inspected uses point-time distance and additional scoring/gating machinery; the paper discusses intervals. Our code documents its interval convention rather than mixing both and calling that exact reproduction.
- We use the existing CPU BM25 implementation, not BGE-M3 or the author's full pipeline.
- We do not select a “best alpha” using test-question gold labels. Such oracle tuning is not a deployable baseline.
- The strict interval version index is a separate implementation; oracle/corrected metadata is shared by all structured modes in that input condition.

**Allowed claim:** comparison against a documented TimelyRAG-inspired control. **Not allowed:** “we beat TimelyRAG,” until a faithful reproduction/adaptation audit and matched real-data comparison are completed. Apofasi full-text capability verification remains outstanding.

## Candidate selective gate

The gate ranks both active and unresolved provisions; proposed replacement wording is included when ranking an uncertain target so uncertainty is not hidden merely by filtering it out. It checks selected provisions and explicit same-document paragraph/ clause references. Unknown targets and document-wide issues block globally. Ambiguous/missing references block; ranges are conservatively unresolved. Issues outside the selected dependency set are returned visibly as `out_of_query_issues`.

This is a measurable engineering hypothesis, not confirmed novelty. Lexical retrieval can miss necessary provisions, cross-document legal dependencies may be implicit, and unobserved amendments cannot be detected by a gate over observed events. The current gate is not a learned confidence estimator. Report one risk/coverage operating point per configuration; do not fabricate a smooth calibrated curve.

## Falsification checks already executable

`scripts/run_research_checks.py` creates disposable synthetic databases and compares clean metadata, known uncertainty, an unobserved amendment and a wrong effective date. It excludes the original unreviewed-scope checkbox case from comparison: rewarding only our policy gate for that UI-contract case would inflate the apparent advantage over other methods.

On the clean four-question fixture, the strict interval control and both clause modes pass the same rubric. With an unobserved amendment, all can use an obsolete rule. These are useful counterexamples to an overbroad superiority claim, **not real-corpus experimental results**. Published comparisons still require the reviewed dataset.
