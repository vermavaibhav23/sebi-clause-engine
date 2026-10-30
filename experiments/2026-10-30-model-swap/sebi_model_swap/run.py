from pathlib import Path
import sys,os,re,json,time,hashlib
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent/'sebi_pilot'
sys.path.insert(0,str(BASE/'compat'));sys.path.append(str(BASE/'vendor'))
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';os.environ['HF_HOME']=str(ROOT/'cache')
import numpy as np,pandas as pd
from rank_bm25 import BM25Okapi

def tokens(s):return re.findall(r'[a-z]+|\d+(?:\.\d+)*',s.lower())
def norm(s):return re.sub(r'\s+',' ',s).strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
docs=json.loads((BASE/'documents.json').read_text(encoding='utf-8'))
pages=[dict(id=d['id']+':'+str(i+1),date=d['date'],text=norm(p)) for d in docs for i,p in enumerate(d['pages'])]
gold=json.loads((BASE/'gold.json').read_text())
phase_map=json.loads((BASE/'extracted_events.json').read_text())['phase_map']
phase_publication=next(d['date'] for d in docs if d['id']=='nom_feb')
chosen=set(range(6,11))|set(range(21,26))|set(range(41,46))|{51,52,54,56,57,59,60,62,69}
subset=[q for q in gold if int(q['id'][1:]) in chosen]
bm=BM25Okapi([tokens(p['text']) for p in pages])
rows=[];candidate_rows=[];pair_rows=[]
def rank(q,text=None):
    scores=bm.get_scores(tokens(text or q['question']))
    return [int(i) for i in np.argsort(-scores,kind='stable') if pages[i]['date']<=q['date']]
def fusion(a,b):
    score={i:0. for i in a}
    for order in [a,b]:
        for pos,i in enumerate(order):score[i]=score.get(i,0)+1/(60+pos+1)
    return sorted(score,key=lambda i:-score[i])
def expanded(q):
    text=q['question'];m=re.search(r'nomination clause (\d+(?:\.\d+)+)',text,re.I)
    if m and q['date']>=phase_publication:
        phase=phase_map.get(m.group(1))
        text+=' implementation circular come into effect'
        if phase:text+=' Phase '+phase+' implementation timeline deferred'
    return text
def record(q,method,order,evaluation_set):
    for k in [3,5]:
        got=[pages[i]['id'] for i in order[:k]];refs=set(q['evidence'])
        rows.append(dict(id=q['id'],group=q['group'],evaluation_set=evaluation_set,method=method,k=k,all_required=int(refs<=set(got)),required_page_recall=len(refs&set(got))/len(refs),retrieved='|'.join(got)))
def save():
    df=pd.DataFrame(rows);df.to_csv(ROOT/'retrieval_predictions.csv',index=False)
    df.groupby(['evaluation_set','method','k'])[['all_required','required_page_recall']].mean().to_csv(ROOT/'summary.csv')
    df.groupby(['evaluation_set','group','method','k'])[['all_required','required_page_recall']].mean().to_csv(ROOT/'by_family.csv')
    pd.DataFrame(pair_rows).to_csv(ROOT/'neural_pair_scores.csv',index=False)

def main():
    started=time.time();assert len(subset)==24
    frozen={str(p.name):sha(p) for p in [Path(__file__),ROOT/'protocol.txt',BASE/'gold.json',BASE/'documents.json']}
    (ROOT/'pre_score_hashes.json').write_text(json.dumps(frozen,indent=2))
    for q in gold:
        original=rank(q);alternative=rank(q,expanded(q))
        for name,order in [('BM25_date_filter',original),('phase_expansion_BM25',alternative),('phase_expansion_RRF',fusion(original,alternative))]:
            record(q,name,order,'all72')
            if q in subset:record(q,name,order,'focused24')
    save();print('Non-neural controls saved',flush=True)
    import torch
    from transformers import AutoTokenizer,AutoModelForSeq2SeqLM,AutoConfig
    torch.set_num_threads(2);torch.manual_seed(42)
    cache=Path('C:/Users/askvv/.cache/huggingface/hub/models--MBZUAI--LaMini-Flan-T5-783M/snapshots')
    model_dir=next(p.parent for p in cache.glob('*/model.safetensors') if p.stat().st_size>100000000)
    config_dir=next(p.parent for p in cache.glob('*/config.json'))
    print('Loading cached neural model',flush=True);loaded=time.time()
    tok=AutoTokenizer.from_pretrained(str(config_dir),local_files_only=True,use_fast=True)
    model=AutoModelForSeq2SeqLM.from_pretrained(str(model_dir),config=AutoConfig.from_pretrained(str(config_dir),local_files_only=True),local_files_only=True,use_safetensors=True,torch_dtype=torch.float32).eval()
    model=torch.ao.quantization.quantize_dynamic(model,{torch.nn.Linear},dtype=torch.qint8,inplace=True)
    yes=tok.encode('yes',add_special_tokens=False);no=tok.encode('no',add_special_tokens=False)
    assert len(yes)==len(no)==1
    model_load=time.time()-loaded;print('Loaded in',round(model_load,1),'s',flush=True)
    prompt_prefix='Decide whether the passage provides evidence needed to answer the question. Answer yes or no.\nQuestion: '
    for qi,q in enumerate(subset):
        original=rank(q)[:10];scores={};qtime=time.time()
        refs=set(q['evidence']);candidate_rows.append(dict(id=q['id'],all_required_at10=int(refs<={pages[i]['id'] for i in original})))
        for i in original:
            prompt=prompt_prefix+q['question']+'\nPassage (issued '+pages[i]['date']+'):\n'+pages[i]['text']
            ids=tok(prompt,add_special_tokens=True)['input_ids'];truncated=len(ids)>512
            x=tok(prompt,return_tensors='pt',truncation=True,max_length=512)
            tick=time.time()
            with torch.inference_mode():
                logits=model(**x,decoder_input_ids=torch.tensor([[model.config.decoder_start_token_id]])).logits[0,0,[yes[0],no[0]]]
                assert torch.isfinite(logits).all()
                score=float(torch.softmax(logits,dim=0)[0])
            scores[i]=score
            pair_rows.append(dict(id=q['id'],page=pages[i]['id'],yes_probability=score,input_tokens=len(ids),truncated=truncated,seconds=time.time()-tick))
        neural=sorted(original,key=lambda i:-scores[i])
        record(q,'LaMini_rerank',neural,'focused24')
        record(q,'BM25_LaMini_RRF',fusion(original,neural),'focused24')
        save();print(q['id'],f'{qi+1}/24',round(time.time()-qtime,1),'s',flush=True)
    pd.DataFrame(candidate_rows).to_csv(ROOT/'candidate_ceiling.csv',index=False)
    manifest=dict(model='MBZUAI/LaMini-Flan-T5-783M',weight_revision=model_dir.name,config_tokenizer_revision=config_dir.name,weight_sha256=sha(model_dir/'model.safetensors'),prompt_prefix=prompt_prefix,yes_token=yes,no_token=no,max_input_tokens=512,torch=torch.__version__,dtype='dynamic int8 linear layers; other weights float32',model_load_seconds=model_load,total_seconds=time.time()-started,queries=len(subset),pairs=len(pair_rows),truncated_pairs=sum(r['truncated'] for r in pair_rows),pre_score_hashes=frozen)
    (ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print(pd.read_csv(ROOT/'summary.csv').to_string(index=False),flush=True)
if __name__=='__main__':main()
