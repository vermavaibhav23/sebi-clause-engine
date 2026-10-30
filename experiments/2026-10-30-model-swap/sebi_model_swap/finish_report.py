from pathlib import Path
import json
import pandas as pd
R=Path(__file__).resolve().parent
a=json.loads((R/'audit.json').read_text()); m=json.loads((R/'manifest.json').read_text())
s=pd.read_csv(R/'summary.csv'); p=pd.read_csv(R/'retrieval_predictions.csv')
lines=['SEBI MODEL-SWAP PILOT — 30 October 2026', '',
'Question: Does a different ranking model improve complete evidence retrieval?',
'This is a development experiment, not a publication or a published-baseline reproduction.', '',
'MATCHED 24-QUESTION SUBSET',
'Success means all reference evidence pages occur in the first five retrieved pages.',
'It does NOT mean the system generated a correct legal answer.', '']
for method,count in a['focused24_at5'].items():
    lines.append(f'{method}: {count}/24 ({count/24:.1%})')
lines+=['', 'ALL 72 QUESTIONS (NON-NEURAL METHODS ONLY)']
for r in s[(s.evaluation_set=='all72')&(s.k==5)].itertuples():
    lines.append(f'{r.method}: {round(r.all_required*72)}/72 ({r.all_required:.1%})')
lines+=['','PAIRED CHANGES VERSUS BM25 ON THE 24 QUESTIONS',json.dumps(a['paired_vs_BM25'],indent=2),
'',f"BM25 top10 candidate ceiling: {a['candidate_ceiling_at10']}/24.",
f"Truncated neural inputs: {a['truncated_pairs']}/240 pairs (512-token limit).",
f"Mean model inference per query: {a['mean_query_inference_seconds']:.1f} seconds.",
f"Total experiment runtime: {a['total_seconds']/60:.1f} minutes.",
'', 'WHAT RAN AND WHAT DID NOT',
'Local LaMini-Flan-T5-783M, dynamic int8 linear layers, CPU, two threads.',
'This is an older instruction model, not a specialized trained reranker or SOTA.',
'It scores a fixed yes/no relevance prompt for the same BM25 top10 candidates.',
'Pure model reranking and fixed reciprocal-rank fusion were both pre-specified.',
'The alternative expands queries with phase metadata extracted from source documents.',
'That metadata parser was developed on these documents and is an additional input advantage.',
'No gold answer or evidence list entered the model prompt or expansion.',
'No training or prompt tuning was performed after observing these results.',
'No TimelyRAG, VersionRAG, UAFE, BGE reranker or end-to-end generator was run here.',
'', 'LIMITATIONS',
'Eight selected historical PDFs, two families, assistant-authored reference labels.',
'The 24 queries are purposively chosen from previously inspected development data.',
'Repeated dates/clauses are correlated; no independent-sample significance claim.',
'Input truncation can hide relevant evidence; ranking has only ten initial candidates.',
'These results cannot establish whether specialist neural rerankers would work better.',
'A score improvement alone does not establish novelty, clinical/legal validity,',
'publication readiness, or superiority over a published paper.',
'', 'RESEARCH DECISION',
'Treat model swapping as an experiment, not the research contribution.',
'Use the observed evidence-linking failures to design an unseen-family evaluation.',
'For a different task, investigate selective amendment application: reduce undetected',
'errors across amendment chains at a fixed human-review budget. Structured edits and',
'verification already have prior art; a specific new method still needs justification.',
'See research_options.txt for verified papers, overlap, and reproduction gates.',
'', 'AUDIT',a['checks'],
'Artifacts: protocol.txt, run.py, pre_score_hashes.json, manifest.json,',
'retrieval_predictions.csv, neural_pair_scores.csv, summary.csv, by_family.csv,',
'candidate_ceiling.csv, audit.json. Prior pilot files were not modified.']
(R/'report.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines[:35]))
