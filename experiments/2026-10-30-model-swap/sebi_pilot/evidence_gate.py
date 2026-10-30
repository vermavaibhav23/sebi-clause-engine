"""Post-primary diagnostic: allow resolution only from retrieved source pages.
No hyperparameter search; explicitly exploratory and separate from main scores.
"""
from pathlib import Path
import json,sys
import pandas as pd
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import experiment as e
gold=json.loads((ROOT/'gold.json').read_text())
retr=pd.read_csv(ROOT/'retrieval_predictions.csv')
rows=[]
for q in gold:
    for k in [3,5]:
        rr=retr[(retr.id==q['id'])&(retr.method=='BM25_date_filter')&(retr.k==k)].iloc[0]
        got=set(rr.retrieved.split('|'))
        pool=[x for x in e.events if x['date']<=q['date'] and e.applies(x,q) and set(x['evidence'])<=got]
        event=max(pool,key=lambda x:(x['date'],x['scope']!='all'),default=None)
        pred=e.answer(event,q)
        rows.append(dict(id=q['id'],group=q['group'],k=k,expected=q['expected'],predicted=pred,correct=int(pred==q['expected']),abstained=event is None,evidence='' if event is None else '|'.join(event['evidence'])))
df=pd.DataFrame(rows);df.to_csv(ROOT/'exploratory_evidence_gate.csv',index=False)
print(df.groupby(['k','group'])[['correct','abstained']].mean().to_string())
print(df.groupby('k')[['correct','abstained']].mean().to_string())
