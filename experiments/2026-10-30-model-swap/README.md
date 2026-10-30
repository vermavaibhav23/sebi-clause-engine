# Exploratory SEBI retrieval and model-swap pilot

Recorded on 30 October 2026. This archive preserves a separate development
experiment; it does not evaluate the repository's FastAPI application or its
22-document research collection. The eight-PDF corpus has 70 pages, two document
families, and 72 AI-authored questions. Labels have not been independently reviewed.

## Result

Success means all reference evidence pages appear in the first five retrieved
pages. It is not generated-answer accuracy or a measure of legal validity.

| Method | Same 24 selected questions |
|---|---:|
| Publication-date-filtered BM25 | 15/24 (62.5%) |
| LaMini reranking of BM25 top ten | 13/24 (54.2%) |
| BM25 + LaMini reciprocal-rank fusion | 16/24 (66.7%) |
| BM25 with source-derived phase query expansion | 19/24 (79.2%) |
| Original + expanded BM25 reciprocal-rank fusion | 16/24 (66.7%) |

Across all 72 questions, phase expansion improved BM25 from 48/72 to 58/72,
with ten gains and no losses. The neural comparison ran only on the selected 24.
BM25's initial ten candidates contained complete reference evidence for only
16/24 questions, imposing a ceiling on reranking. Expansion searched the full
date-eligible corpus and used additional source-derived metadata.

The CPU run used an older instruction model, `MBZUAI/LaMini-Flan-T5-783M`, with
dynamic int8 linear layers. It is not a specialist relevance model or a current
state-of-the-art baseline. Of 240 query/page inputs, 113 exceeded the 512-token
limit and were truncated. Mean model inference was about 38 seconds per query.

These results justify investigating candidate retrieval and amendment links.
They do **not** establish novelty, publication readiness, or a win over TimelyRAG,
VersionRAG, UAFE, or any other published system. The subset was purposively chosen
from previously inspected data. Repeated clauses and dates are not independent
samples. The phase parser was developed on this corpus.

## Inspect and verify

- [Complete model-swap report](sebi_model_swap/report.txt)
- [Protocol fixed before the new scores](sebi_model_swap/protocol.txt)
- [Per-question retrieval results](sebi_model_swap/retrieval_predictions.csv)
- [All 240 neural scores and timings](sebi_model_swap/neural_pair_scores.csv)
- [Original pilot report and limitations](sebi_pilot/report.txt)
- [Research alternatives and prior-art overlap](sebi_model_swap/research_options.txt)

Run from the repository root with Python 3.11 or newer:

```sh
python experiments/2026-10-30-model-swap/verify_archive.py
```

This uses only the Python standard library, makes no network requests, and writes
no files. It checks frozen input hashes, evidence IDs, historical publication
cutoffs, all saved retrieval metrics, neural ordering/fusion, candidate ceilings,
and aggregate tables. It validates the recorded artifact's internal consistency;
it cannot establish that the AI-authored evidence labels are complete or correct.

## Contents and rerun boundaries

`sebi_model_swap/` contains the original frozen runner, protocol, manifests,
scores, summaries, and post-run audit/report scripts. `sebi_pilot/` supplies the
original extracted public-source text, question labels, phase metadata, parser,
and earlier controls. Source URLs and PDF SHA-256 values are in
`sebi_pilot/documents.json`. Raw PDFs and model weights are not included.
`sebi_pilot/first_run/` preserves the earlier run before the parser correction;
use the top-level pilot report for the final development results.

For historical integrity, the recorded `run.py` is byte-for-byte unchanged. It
contains the original machine's model-cache path and expects safetensors and
tokenizer/config snapshots at the revisions recorded in `manifest.json`. It is
not a portable command-line interface. A fresh inference run requires installing
the separate experiment dependencies, obtaining those model snapshots, adapting
the cache path in a **copy** of the archive, and recording new code/input hashes.
Do not overwrite this frozen run or present modified-code outputs as its result.

`requirements-experiment.txt` records the principal versions for the model-swap
runner, separate from the application's dependencies. Use a separate virtual
environment; weights remain subject to the model publisher's license. Reproducing
the earlier PDF extraction additionally requires `pypdf`, `requests`, `PyMuPDF`,
and `scikit-learn`, plus source downloads through `sebi_pilot/download.py` in a
working copy. PDF extraction can vary with package versions/source bytes.

No network, GPU, model download, or dependency installation is needed to inspect
the results or run `verify_archive.py`.
