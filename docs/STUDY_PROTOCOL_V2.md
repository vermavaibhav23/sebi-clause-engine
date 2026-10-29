# Study protocol v2 — prospective, not externally preregistered

Candidate title: **From PDF Amendments to Applicable Evidence: An Error-Propagation Study of SEBI Regulatory QA**.

Primary contribution candidate: a reproducible, independently annotated SEBI amendment corpus and an empirical study of how target, operation, date and missing-chain errors affect applicable-evidence retrieval, unchanged provisions and abstention. A query-specific uncertainty gate is an experimental mitigation, not a proven novel algorithm.

## Explicit hypotheses

- H1: With the same correct event inputs, clause resolution may offer little or no answer-quality advantage over a strong interval-filtering baseline. This is a legitimate outcome and must be reported.
- H2: With observed but unresolved amendments, query-specific gating may preserve more correct answers about unaffected provisions than whole-scope gating. Assess error as well as coverage; extra answers can be wrong.
- H3: Wrong or unobserved amendment data can defeat either temporal architecture. Measure error propagation and annotation/corpus-review effort instead of treating graph construction as an oracle.

Related literature and limits are in RESEARCH_PROTOCOL.md and BASELINES.md. SAT-Graph already supports component versioning and unchanged-component reuse. Its published discussion identifies dependence on accurate upstream data and further quantitative evaluation; that motivates H3, not a claim of exclusive novelty. TimelyRAG already targets overlapping amendments. FR-AMD overlaps amendment parsing benchmarks, and the published Legal Rule Auditor overlaps lifecycle filtering and validation. The remaining candidate is a domain-specific empirical study with independently reviewed sources and transferable failure analysis. The closest-work search must be refreshed before submission.

## Data and sampling

Current source collection: 22 official SEBI PDFs. Revised parser: 809 clause/table segments. This count is an extraction output, not verified clause count. There are 27 proposed relationships, including ordinary references; these are not 27 true amendments. No real event has been approved as human verified by the agent.

The collection spans validation/portability, KRA cybersecurity and digital-KYC support. It is broader than the initial validation subsection to include actual explicit partial modifications and temporal cases. Do not present all 22 as one complete validation-only chain. Official master consolidation connects several subtopics. Publication dates are header metadata; most effective dates remain unknown.

Fifty AI-drafted questions include paired dates and discovery anchors. Reviewers may reject misleading or redundant questions; freeze a version only after calibration. Keep calibration families out of a confirmatory test. A three-way split requires at least three genuinely independent families; the code refuses fewer. Five families is a minimum code guard for a bootstrap interval, not an assurance of adequate statistical power. More independent amendment families will probably be needed after the pilot.

## Experimental matrix to run after annotation

Use the same questions, source corpus and metadata-access budget across methods. Separate these input conditions explicitly:

1. **Automatic extraction:** all machine proposals, unknown fields retained, no gold targets/dates silently supplied. The current extractor's missing dates are failures/unknowns, not correct extraction.
2. **Human-corrected inputs:** reviewers resolve targets/operations/dates; all structured methods receive the same corrected inputs. Record correction time.
3. **Oracle upper bound:** use adjudicated event annotations where available; label as an upper bound, not an end-to-end competitor.
4. **Controlled corruption:** known target/date errors and omitted dependencies, labelled artificial. Do not infer natural error prevalence from injected errors.

The full real-data automatic-versus-corrected matrix cannot run yet because human labels and a reviewed event graph do not exist. Current stress checks implement only labelled synthetic conditions. Do not substitute them for the matrix.

## Outcomes and analysis

Primary outcome: applicable-answer correctness under a prespecified, blinded human rubric. Secondary outcomes: obsolete-rule usage, unchanged-provision preservation, required-evidence recall, abstention precision/recall, answered-case error, answer coverage, latency, memory and human correction effort. Exact event-tuple F1 includes source/target/operation/date; also report component errors.

The current evaluator's answer-fragment and citation rubric is a screening measure. It can be gamed by long passages and misses semantic nuances; use blinded human output adjudication for final answer correctness. Citation publication age is never a validity label. Preserve original citations as legitimate provenance when appropriate.

Use paired questions and family-cluster uncertainty, with test splits frozen by family. Do not count two dates/paraphrases of one question as independent evidence. Report each stratum and all failed cases. Disclose that corpus families share a master circular where applicable. No significance claim is justified from the four-question fixture or one connected family.

## Reproducibility controls implemented

- Official URLs, local bytes, SHA-256 hashes, collection inventory with timestamps and failures.
- Original parsing database preserved; revised parser uses a new research database and extractor version.
- Blank independent review packets, question hashes, original-review hashes and separate adjudication provenance.
- No silent overwrite of compiled benchmarks or frozen split files.
- Explicit calibration-family reservations keep practice/tuning examples and their variants out of test.
- Corpus and dataset fingerprints checked against a frozen split; source-file hashes recorded in evaluation reports.
- Fixed random seed for paired cluster bootstrap; too-few-family intervals suppressed.
- Separate labels for paper-inspired adaptation, synthetic software checks and human-labelled research data.

## Publication decision gate

Proceed to a benchmark/empirical paper only after independent labels, a defensible scope, strong baseline audit and useful real-data findings exist. If H2 fails, report the coverage/error tradeoff rather than inventing a success claim. If the corpus cannot support trustworthy applicability labels, narrow to explicit amendment extraction and source provenance. An engineering demo, a main-track algorithm paper and a journal article have different evidence requirements; select a specific venue after the results and contribution type are clear.

Current decision: **research infrastructure improved; publication readiness remains unestablished**. No guarantee of novelty, superior performance or acceptance is made.
