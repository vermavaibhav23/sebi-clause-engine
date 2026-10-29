"""Bounded official-source collector. Metadata is machine-drafted, never legal gold.

Discovers KYC circular pages from the NDML index, then downloads only SEBI PDFs.
Preserves each page/PDF, URLs, hashes, timestamps, and explicit failures.
"""
import argparse
import hashlib
import html
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, unquote
from urllib.request import Request, urlopen
import pdfplumber

INDEX = "https://kra.ndml.in/kra-web/jsps/menu/Downloads.htm"
ROOT = Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.current = [], None
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.current = [dict(attrs).get("href", ""), ""]
    def handle_data(self, data):
        if self.current is not None:
            self.current[1] += data
    def handle_endtag(self, tag):
        if tag == "a" and self.current is not None:
            self.links.append(self.current)
            self.current = None


def fetch(url, discovery=False):
    hosts = {"www.sebi.gov.in", "sebi.gov.in"}
    if discovery:
        hosts.add("kra.ndml.in")
    if urlparse(url).scheme != "https" or urlparse(url).hostname not in hosts:
        raise ValueError("Only explicit HTTPS discovery/SEBI sources allowed")
    with urlopen(Request(url, headers={"User-Agent": "SEBI-Research-Pilot/0.2"}), timeout=30) as response:
        if urlparse(response.url).hostname not in hosts:
            raise ValueError("Unexpected redirect")
        raw = response.read(25*1024*1024+1)
    if len(raw) > 25*1024*1024:
        raise ValueError("Source exceeds collection limit")
    return raw


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--discover", action="store_true")
    args=parser.parse_args()
    folder=ROOT/"runtime"/"collection"
    folder.mkdir(parents=True,exist_ok=True)
    sources=json.loads((ROOT/"data"/"collection_sources.json").read_text(encoding="utf-8"))
    if args.discover:
        raw=fetch(INDEX,True)
        (folder/"discovery-index.html").write_bytes(raw)
        links=Links(); links.feed(raw.decode("utf-8",errors="replace"))
        for url,title in links.links:
            if "sebi.gov.in/legal/circulars/" in url and any(x in title.lower() for x in ["kyc", "know your"]):
                sources.append({"url":url.split(" & ")[0].replace("http://","https://"),"title":title.strip(),"discovered_from":INDEX})
    # Selection is recorded before downloading; no silent drop of parser failures.
    sources=list({s["url"]:s for s in sources}.values())
    (folder/"selected_sources.json").write_text(json.dumps(sources,indent=2),encoding="utf-8")
    inventory=[]
    for source in sources:
        record={**source,"collected_at":datetime.now(timezone.utc).isoformat(),"label_status":"machine_draft"}
        try:
            source_key=hashlib.sha256(source["url"].encode()).hexdigest()[:16]
            cache=folder/(source_key+".source")
            raw=cache.read_bytes() if cache.exists() else fetch(source["url"])
            cache.write_bytes(raw)
            pdf_url=source["url"]
            if not raw.startswith(b"%PDF"):
                decoded=html.unescape(unquote(raw.decode("utf-8",errors="replace")))
                urls=re.findall(r'(?:https?://www\.sebi\.gov\.in)?/(?:cms/)?sebi_data/[^\s<>"\x27]+?\.pdf',decoded)
                if not urls:
                    raise ValueError("No PDF link found on official page")
                pdf_url=urljoin("https://www.sebi.gov.in",urls[0]).replace("http://","https://")
                pdf_cache=folder/(source_key+".pdf")
                raw=pdf_cache.read_bytes() if pdf_cache.exists() else fetch(pdf_url)
                pdf_cache.write_bytes(raw)
            if not raw.startswith(b"%PDF"):
                raise ValueError("Downloaded content is not PDF")
            sha=hashlib.sha256(raw).hexdigest()
            path=folder/(sha+".pdf")
            path.write_bytes(raw)
            with pdfplumber.open(io.BytesIO(raw)) as pdf:
                texts=[p.extract_text(x_tolerance=2) or "" for p in pdf.pages]
            header="\n".join(texts[0].splitlines()[:22])
            # Conservative header-only matching avoids taking a cited predecessor's ID.
            ids=re.findall(r'(?:SEBI/HO/[A-Za-z0-9/\-]+/20\d{2}/\d+|(?:CIR/MIRSD|MIRSD(?:/SE)?)/\s*(?:Cir-\s*)?\d+\s*/\s*20\d{2})',header,re.I)
            dates=re.findall(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})\s*,?\s*(20\d{2})',header,re.I)
            doc_id=source.get("id") or (re.sub(r"\s+","",ids[0]) if ids else None)
            pub=source.get("publication_date") or (datetime.strptime(" ".join(dates[0]),"%B %d %Y").date().isoformat() if dates else None)
            if not doc_id or not pub:
                raise ValueError("Header ID/date requires manual metadata review")
            record.update(id=doc_id,publication_date=pub,source_url=pdf_url,sha256=sha,
                filename=path.name,pages=len(texts),status="downloaded",effective_date=None,
                date_evidence="Publication date from header; effective date unreviewed",
                header=header)
            (folder/(sha+".txt")).write_text("\n\f\n".join(texts),encoding="utf-8")
        except Exception as exc:
            record.update(status="needs_attention",error=str(exc))
        inventory.append(record)
        (folder/"inventory.json").write_text(json.dumps(inventory,indent=2),encoding="utf-8")
        print(record.get("id",record["url"]),record["status"],flush=True)
    manifest=[]
    seen=set()
    for r in inventory:
        if r["status"]=="downloaded" and r["id"] not in seen:
            seen.add(r["id"])
            manifest.append({k:r[k] for k in ["id","title","publication_date","effective_date","source_url","date_evidence"]}|{"local_filename":r["filename"],"kind":"circular"})
    (ROOT/"data"/"expanded_sources.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(json.dumps({"downloaded_unique_documents":len(manifest),"needs_attention":sum(r["status"]!="downloaded" for r in inventory)}))


if __name__=="__main__":
    main()
