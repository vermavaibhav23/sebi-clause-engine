from pathlib import Path
import json,hashlib
import pandas as pd
R=Path(__file__).resolve().parent; B=R.parent/'sebi_pilot'
f=pd.read_csv(R/'retrieval_predictions.csv'); p=pd.read_csv(R/'neural_pair_scores.csv')
m=json.loads((R/'manifest.json').read_text())
assert len(f)==672 and len(p)==240 and p.id.nunique()==24
assert not p.duplicated(['id','page']).any()
for name,directory in [('run.py',R),('protocol.txt',R),('gold.json',B),('documents.json',B)]:
    assert hashlib.sha256((directory/name).read_bytes()).hexdigest()==m['pre_score_hashes'][name]
gold={q['id']:q for q in json.loads((B/'gold.json').read_text())}
docs={d['id']:d for d in json.loads((B/'documents.json').read_text(encoding='utf-8'))}
for row in f.itertuples():
    got=row.retrieved.split('|'); q=gold[row.id]
    assert len(got)==row.k and len(set(got))==row.k
    assert all(docs[g.rsplit(':',1)[0]]['date']<=q['date'] for g in got)
    assert row.all_required==int(set(q['evidence'])<=set(got))
focused=f[(f.evaluation_set=='focused24')&(f.k==5)].pivot(index='id',columns='method',values='all_required')
base=focused['BM25_date_filter']
result={'checks':'PASS: row counts, frozen inputs, no duplicate model pairs, publication-date filtering, evidence metrics',
        'focused24_at5':{c:int(focused[c].sum()) for c in focused},
        'paired_vs_BM25':{c:{'wins':int(((focused[c]==1)&(base==0)).sum()),'losses':int(((focused[c]==0)&(base==1)).sum())} for c in focused if c!='BM25_date_filter'},
        'candidate_ceiling_at10':int(pd.read_csv(R/'candidate_ceiling.csv').all_required_at10.sum()),
        'truncated_pairs':int(p.truncated.sum()),'mean_query_inference_seconds':float(p.groupby('id').seconds.sum().mean()),
        'total_seconds':m['total_seconds']}
(R/'audit.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
