"""Assistant-authored closed-corpus reference set. Not expert-validated."""
from pathlib import Path
import json
OUT=Path(__file__).resolve().parent
questions=[]
def add(question,group,date,field,value,evidence,**slots):
    questions.append(dict(id=f'Q{len(questions)+1:03d}',question=question,group=group,date=date,field=field,expected=value,evidence=evidence,**slots))

# Independent expected schedule matrix, transcribed from the source chronology.
dates=['2025-02-15','2025-03-15','2025-08-01','2025-08-20','2025-12-20']
specs=[('2.1.4','II'),('2.13','II'),('3.1.1','II'),('3.6.2','II'),('3.2','III'),('3.4','III'),('3.5','III'),('3.10','III'),('2.11','I'),('2.14','I')]
values={'I':['2025-03-01']*5,'II':['2025-03-01','2025-06-01','2025-08-08','2025-08-08','2025-08-08'],'III':['2025-03-01','2025-09-01','2025-12-15','2025-12-15','DEFERRED_UNSPECIFIED']}
for clause,phase in specs:
    for i,date in enumerate(dates):
        ev=['nom_jan:7'] if i==0 or phase=='I' else ['nom_feb:6']
        if phase!='I' and i>=2:ev+=['nom_jul:2']
        if phase=='III' and i==4:ev=['nom_feb:6','nom_dec:2']
        qual='(a) and (b)' if clause=='3.1.1' else ''
        add(f'Based only on circulars issued by {date}, what implementation date is announced for nomination clause {clause}{qual}? Give an unspecified deferment if no date is set.', 'nomination',date,'schedule',values[phase][i],ev,clause=clause,entity='NOM',scope='all',consent=True)

for entity,label,old,old_ev in [('IA','investment adviser',6,['ia_2020:3']),('RA','research analyst',3,['ra_jan:8'])]:
    for date in ['2025-03-15','2025-04-02','2025-05-15']:
        after=date>='2025-04-02'
        add(f'On {date}, for a new non-accredited individual client who agrees, how many months of fees may a {label} collect in advance?', 'fees',date,'advance_months',12 if after else old,['fees_apr:2'] if after else old_ev,entity=entity,scope='retail',consent=True)
    for scope,desc in [('accredited','an accredited individual investor'),('corporate','a non-individual corporate client')]:
        add(f'On 2025-05-15, is the advance-fee period for a {label} serving {desc} governed by the one-year retail cap or bilaterally negotiated terms?', 'fees','2025-05-15','advance_months','NEGOTIATED',['fees_apr:2'],entity=entity,scope=scope,consent=True)
    add(f'On 2025-05-15, may a {label} collect advance fees from a new non-accredited individual client without the client agreeing?', 'fees','2025-05-15','advance_months','CLIENT_AGREEMENT_REQUIRED',['fees_apr:2'],entity=entity,scope='retail',consent=False)
    for date in ['2025-03-15','2025-05-15']:
        add(f'On {date}, what is the annual fixed fee cap in rupees per family for a {label} serving a new non-accredited individual client, excluding statutory charges?', 'fees',date,'fixed_fee',151000,[('ia_jan:8' if entity=='IA' else 'ra_jan:8')],entity=entity,scope='retail',consent=True)
for date in ['2025-03-15','2025-05-15']:
    add(f'On {date}, what percentage per annum is the Assets under Advice fee ceiling for an investment adviser serving a new non-accredited individual client?', 'fees',date,'aua_percent',2.5,['ia_jan:7'],entity='IA',scope='retail',consent=True)
    add(f'On {date}, what is the maximum breakage fee in months for an investment adviser on premature termination for a new non-accredited individual client?', 'fees',date,'breakage_months',3,['ia_2020:3'],entity='IA',scope='retail',consent=True)
    add(f'On {date}, how many months of breakage fees may a research analyst charge on premature termination for a new non-accredited individual client?', 'fees',date,'breakage_months',0,['ra_jan:8'],entity='RA',scope='retail',consent=True)
(OUT/'gold.json').write_text(json.dumps(questions,indent=2),encoding='utf-8')
print('Reference questions:',len(questions))
