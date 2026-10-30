from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import experiment as e
assert e.phase_map['3.6.2']=='II' and e.phase_map['3.6.1']=='III'
assert len(e.docs)==8 and len(e.pages)==70
assert all(x['evidence'] and all(y in e.page_by for y in x['evidence']) for x in e.events)
assert not any('expected' in x for x in e.events)
gold=json.loads((ROOT/'gold.json').read_text())
assert len(gold)==len({q['id'] for q in gold})==72
for q in gold:
    assert all(e.page_by[p]['date']<=q['date'] for p in q['evidence'])
print('PASS: table geometry, unique questions, evidence existence, chronology, corpus counts, no gold-value field in extracted events.')
