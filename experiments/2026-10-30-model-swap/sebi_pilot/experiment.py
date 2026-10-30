"""Exploratory retrieval and structured-resolution micro-pilot; see protocol.txt."""
from pathlib import Path
import sys,json,re,hashlib,time,datetime,platform
ROOT=Path(__file__).resolve().parent
sys.path.append(str(ROOT/'vendor'))
import numpy as np,pandas as pd,pymupdf
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer

def norm(s):return re.sub(r'\s+',' ',s).strip()
def tokens(s):return re.findall(r'[a-z]+|\d+(?:\.\d+)*',s.lower())
def iso(s):
    s=re.sub(r'[^A-Za-z0-9 ]',' ',s);s=norm(s)
    return datetime.datetime.strptime(s,'%B %d %Y').date().isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

docs={d['id']:d for d in json.loads((ROOT/'documents.json').read_text(encoding='utf-8'))}
pages=[dict(id=d['id']+':'+str(i+1),doc=d['id'],date=d['date'],text=norm(p)) for d in docs.values() for i,p in enumerate(d['pages'])]
page_by={p['id']:p for p in pages}
def txt(doc,p):return page_by[f'{doc}:{p}']['text']
events=[]
def event(doc,p,entity,field,value,scope='all',target='ALL',evidence=None,consent=False):
    events.append(dict(id=f'E{len(events):03d}',doc=doc,date=docs[doc]['date'],entity=entity,field=field,value=value,scope=scope,target=target,evidence=evidence or [f'{doc}:{p}'],requires_consent=consent,text=txt(doc,p)))

# Extract the merged-cell phase table from geometry, forward-filling phase cells.
pdf=pymupdf.open(ROOT/'sources/nom_feb.pdf')
phase_map={};phase_dates={};phase=None
for row in pdf[5].find_tables().tables[0].extract():
    cells=[str(x or '') for x in row]
    p=next((re.search(r'Phase\s+(III|II)\b',x) for x in cells if re.search(r'Phase\s+(III|II)\b',x)),None)
    if p:phase=p.group(1)
    if phase:
        for cell in cells:
            if re.search(r'June|September',cell):phase_dates[phase]=iso(cell)
            if 'Clause' in cell:
                phase_map['.'.join(re.findall(r'\d+',cell))]=phase

date_pattern=r'([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})'
initial=iso(re.search(r'come into effect from\s+'+date_pattern,txt('nom_jan',7)).group(1))
event('nom_jan',7,'NOM','schedule',initial)
for phase,value in phase_dates.items():event('nom_feb',6,'NOM','schedule',value,target=phase)
for phase in ['II','III']:
    match=re.search(r'implementation of Phase '+phase+r'\b.{0,150}?(?:to|till)\s+'+date_pattern,txt('nom_jul',2))
    assert match,phase
    event('nom_jul',2,'NOM','schedule',iso(match.group(1)),target=phase,evidence=['nom_feb:6','nom_jul:2'])
assert 'further date to be notified' in txt('nom_dec',2)
phase=re.search(r'Phase\s+(III|II)\b',txt('nom_dec',1)).group(1)
event('nom_dec',2,'NOM','schedule','DEFERRED_UNSPECIFIED',target=phase,evidence=['nom_feb:6','nom_dec:2'])

wordnum={'one':1,'two':2,'three':3,'2':2,'1':1}
def quantity(pattern,text,mult=1):
    m=re.search(pattern,text,re.I);assert m,pattern
    return wordnum[m.group(1).lower()]*mult
event('ia_2020',3,'IA','advance_months',quantity(r'advance shall not exceed fees for (\w+) quarters',txt('ia_2020',3),3),consent=True)
event('ia_2020',3,'IA','breakage_months',quantity(r'breakage fee of not greater than (\w+) quarter',txt('ia_2020',3),3))
event('ia_2020',3,'IA','fixed_fee',int(re.search(r'INR\s+([\d,]+)',txt('ia_2020',3)).group(1).replace(',','')))
event('ia_2020',3,'IA','aua_percent',float(re.search(r'(\d+\.\d+) percent',txt('ia_2020',3)).group(1)))
for entity,doc in [('IA','ia_jan'),('RA','ra_jan')]:
    pattern=r'shall not exceed\s+₹([\d,]+)' if entity=='IA' else r'maximum of\s+₹([\d,]+)'
    value=int(re.search(pattern,txt(doc,8)).group(1).replace(',',''))
    event(doc,8,entity,'fixed_fee',value,scope='retail')
    if entity=='IA':event(doc,7,entity,'aua_percent',float(re.search(r'(\d+\.\d+) per cent',txt(doc,7)).group(1)),scope='retail')
    else:
        event(doc,8,entity,'advance_months',quantity(r'advance shall not exceed fees for more than (\w+) quarter',txt(doc,8),3),consent=True)
        assert 'shall not charge any breakage fee' in txt(doc,8)
        event(doc,8,entity,'breakage_months',0)
    for field in ['advance_months']:
        value=quantity(r'advance shall not exceed fees for a period of (\w+) year',txt('fees_apr',2),12)
        event('fees_apr',2,entity,field,value,scope='retail',consent=True)
        assert 'bilaterally negotiated contractual terms' in txt('fees_apr',2)
        for scope in ['accredited','corporate']:event('fees_apr',2,entity,field,'NEGOTIATED',scope=scope)

def applies(e,q,scope=True,mapping=True):
    if e['entity']!=q['entity'] or e['field']!=q['field']:return False
    if q['entity']=='NOM':
        target=phase_map.get(q['clause'],'I') if mapping else 'I'
        return e['target'] in ['ALL',target]
    return not scope or e['scope'] in ['all',q['scope']]
def answer(e,q,enforce_consent=True):
    if e is None:return 'NO_EVIDENCE'
    if enforce_consent and e['requires_consent'] and not q['consent']:return 'CLIENT_AGREEMENT_REQUIRED'
    return e['value']

def main():
    start=time.time()
    gold=json.loads((ROOT/'gold.json').read_text())
    assert len(gold)==72 and len(phase_map)==11
    for q in gold:
        assert all(x in page_by for x in q['evidence'])
        assert all(page_by[x]['date']<=q['date'] for x in q['evidence'])
    (ROOT/'extracted_events.json').write_text(json.dumps(dict(phase_map=phase_map,events=events),indent=2))
    freeze={p.name:sha(p) for p in [ROOT/'gold.json',ROOT/'protocol.txt',Path(__file__)]}
    (ROOT/'pre_score_hashes.json').write_text(json.dumps(freeze,indent=2))
    bm=BM25Okapi([tokens(p['text']) for p in pages])
    dense_available=(ROOT/'page_embeddings.npy').exists() and (ROOT/'query_embeddings.npy').exists()
    if dense_available:
        emb=np.load(ROOT/'page_embeddings.npy');qe=np.load(ROOT/'query_embeddings.npy')
        assert emb.shape[0]==len(pages) and qe.shape[0]==len(gold)
    tf=TfidfVectorizer(ngram_range=(1,2),sublinear_tf=True)
    te=tf.fit_transform([p['text'] for p in pages]);tq=tf.transform([q['question'] for q in gold])
    structured=[];retrieval=[]
    ebm=BM25Okapi([tokens(e['text']) for e in events])
    # Flatten phase changes into a plain effective-dated table: deliberately
    # simple, strong control using the same extracted source information.
    table=[]
    for clause in sorted(set(q.get('clause','') for q in gold)-{''}):
        for e in events:
            if e['entity']=='NOM' and e['target'] in ['ALL',phase_map.get(clause,'I')]:table.append(e|{'clause':clause})
    table += [e for e in events if e['entity']!='NOM']
    (ROOT/'flat_control_table.json').write_text(json.dumps(table,indent=2))
    for qi,q in enumerate(gold):
        scores=bm.get_scores(tokens(q['question']))
        orders={'BM25':np.argsort(-scores,kind='stable'),'TFIDF_sparse_control':np.argsort(-(te@tq[qi].T).toarray().ravel(),kind='stable')}
        orders['BM25_date_filter']=np.array([i for i in orders['BM25'] if pages[i]['date']<=q['date']])
        if dense_available:
            ds=emb@qe[qi];orders['dense_MiniLM']=np.argsort(-ds,kind='stable')
            fusion=np.zeros(len(pages))
            for name in ['BM25','dense_MiniLM']:
                order=orders[name];fusion[order]+=1/(60+np.arange(1,len(order)+1))
            orders['hybrid_RRF']=np.argsort(-fusion,kind='stable')
            orders['hybrid_date_filter']=np.array([i for i in orders['hybrid_RRF'] if pages[i]['date']<=q['date']])
        for method,order in orders.items():
            for k in [3,5]:
                got=[pages[i]['id'] for i in order[:k]];hit=set(got)&set(q['evidence'])
                retrieval.append(dict(id=q['id'],group=q['group'],method=method,k=k,required_page_recall=len(hit)/len(q['evidence']),all_required=int(set(q['evidence'])<=set(got)),future_page_fraction=sum(page_by[p]['date']>q['date'] for p in got)/len(got),retrieved='|'.join(got)))
        es=ebm.get_scores(tokens(q['question']))
        eligible=[i for i,e in enumerate(events) if applies(e,q)]
        def latest(ids):return max(ids,key=lambda i:(events[i]['date'],events[i]['scope']!='all'),default=None)
        def lexical(ids):return max(ids,key=lambda i:es[i],default=None)
        dated=[i for i in eligible if events[i]['date']<=q['date']]
        methods={
            'relevance_common_reader':lexical(eligible),
            'date_filter_common_reader':lexical(dated),
            'phase_scope_resolver':latest(dated),
            'resolver_without_phase_mapping':latest([i for i,e in enumerate(events) if e['date']<=q['date'] and applies(e,q,mapping=False)]),
            'resolver_without_scope':latest([i for i,e in enumerate(events) if e['date']<=q['date'] and applies(e,q,scope=False)]),
        }
        for method,idx in methods.items():
            e=None if idx is None else events[idx]
            value=answer(e,q)
            structured.append(dict(id=q['id'],group=q['group'],method=method,expected=q['expected'],predicted=value,correct=int(value==q['expected']),event='' if e is None else e['id'],evidence='' if e is None else '|'.join(e['evidence'])))
        pool=[e for e in table if e['date']<=q['date'] and e['entity']==q['entity'] and e['field']==q['field'] and (e.get('clause')==q.get('clause') if q['entity']=='NOM' else e['scope'] in ['all',q['scope']])]
        e=max(pool,key=lambda e:(e['date'],e['scope']!='all'),default=None)
        value=answer(e,q)
        structured.append(dict(id=q['id'],group=q['group'],method='simple_dated_table',expected=q['expected'],predicted=value,correct=int(value==q['expected']),event='' if e is None else e['id'],evidence='' if e is None else '|'.join(e['evidence'])))
    s=pd.DataFrame(structured);r=pd.DataFrame(retrieval)
    s.to_csv(ROOT/'structured_predictions.csv',index=False);r.to_csv(ROOT/'retrieval_predictions.csv',index=False)
    ss=s.groupby(['method','group']).correct.agg(['sum','count','mean']);rs=r.groupby(['method','k','group'])[['required_page_recall','all_required','future_page_fraction']].mean()
    ss.to_csv(ROOT/'structured_summary.csv');rs.to_csv(ROOT/'retrieval_summary.csv')
    (ROOT/'run_manifest.json').write_text(json.dumps(dict(seconds=time.time()-start,python=platform.python_version(),questions=len(gold),pages=len(pages),documents=len(docs),events=len(events),pre_score_sha256=freeze,independent_families=2,generator_evaluated=False,dense_available=dense_available),indent=2))
    print(ss.to_string());print(rs.to_string())
if __name__=='__main__':main()
