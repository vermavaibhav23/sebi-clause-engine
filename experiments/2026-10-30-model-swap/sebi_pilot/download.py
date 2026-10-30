from pathlib import Path
import requests,json,hashlib
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parent
SOURCES=[
 ('ia_2020','2020-09-23','fees','sep-2020/1600874249403.pdf'),
 ('nom_jan','2025-01-10','nomination','jan-2025/1737459697644.pdf'),
 ('nom_feb','2025-02-28','nomination','feb-2025/1740743883077.pdf'),
 ('nom_jul','2025-07-30','nomination','jul-2025/1753876405008.pdf'),
 ('nom_dec','2025-12-11','nomination','dec-2025/1765451323097.pdf'),
 ('ia_jan','2025-01-08','fees','jan-2025/1736338642778.pdf'),
 ('ra_jan','2025-01-08','fees','jan-2025/1736338732932.pdf'),
 ('fees_apr','2025-04-02','fees','apr-2025/1743595614193.pdf'),
]
def main():
    (ROOT/'sources').mkdir(exist_ok=True)
    records=[]
    for name,date,topic,path in SOURCES:
        url='https://www.sebi.gov.in/sebi_data/attachdocs/'+path
        dest=ROOT/'sources'/f'{name}.pdf'
        if not dest.exists():
            r=requests.get(url,timeout=45);r.raise_for_status();assert r.content.startswith(b'%PDF');dest.write_bytes(r.content)
        pages=[p.extract_text(extraction_mode='layout') for p in PdfReader(dest).pages]
        (ROOT/'sources'/f'{name}.txt').write_text('\n'.join(f'\n=== PAGE {i+1} ===\n{p}' for i,p in enumerate(pages)),encoding='utf-8')
        records.append(dict(id=name,date=date,topic=topic,url=url,pages=pages,sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))
        print(name,len(pages),flush=True)
    (ROOT/'documents.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
