"""Conservative extraction: PDF geometry is evidence, not a claim of legal validity."""
import hashlib
import re
from pathlib import Path
import pdfplumber
from .models import Clause, Document
from .store import Store


NUMBER = re.compile(r"^\s*(\d{1,3}(?:\.\d{1,3})*)(\.\s+|\s+)(?=\S)(.*)$")


def numbered_line(line):
    match=NUMBER.match(line)
    # Integers need an explicit separator dot; nested 2.1 labels may omit it.
    # This rejects wrapped years and '9 and clause 13 ...' continuation lines.
    if match and ("." in match[1] or match[2].startswith(".")):
        return match
    return None


def extract_pdf(path: Path, document_id: str) -> tuple[list[Clause], list[str]]:
    clauses, warnings = [], []
    active = None
    section = "Preamble"
    counter = 0

    def flush():
        nonlocal active
        if active:
            active["text"] = "\n".join(active["lines"]).strip()
            del active["lines"]
            clauses.append(Clause(**active))
            active = None

    with pdfplumber.open(path) as pdf:
        if len(pdf.pages) > 500:
            raise ValueError("Pilot importer limits PDFs to 500 pages")
        for page_no, page in enumerate(pdf.pages, 1):
            text = page.extract_text(x_tolerance=2) or ""
            if len(text.strip()) < 20:
                warnings.append(f"Page {page_no}: little extractable text; OCR/manual review needed")
            if "TABLE OF CONTENTS" in text or text.count(".....") > 3:
                flush()
                continue
            for line in text.splitlines():
                line = line.strip()
                if not line or re.fullmatch(r"(?:Page )?\d+(?: of \d+)?", line, re.I):
                    continue
                if re.match(r"^(Section \d+:|Appendix|Annexure\s+[A-Z]:)", line):
                    flush()
                    section = line
                match = numbered_line(line)
                if match:
                    flush()
                    counter += 1
                    active = dict(id=f"{document_id}::p{page_no}:c{counter}",
                                  document_id=document_id, label=match[1],
                                  page=page_no, end_page=page_no, section=section,
                                  lines=[match[3]], kind="clause")
                elif active:
                    active["lines"].append(line)
                    active["end_page"] = page_no
            # Keep table rows separately with headers; extraction still requires visual review.
            for ti, table in enumerate(page.find_tables()):
                rows = table.extract()
                if not rows or len(rows) < 2:
                    continue
                headers = [str(c or "").replace("\n", " ") for c in rows[0]]
                for ri, row in enumerate(rows[1:], 1):
                    cells = [str(c or "").replace("\n", " ") for c in row]
                    row_text = " | ".join(f"{headers[i] or f'column {i+1}'}: {v}"
                                          for i, v in enumerate(cells) if i < len(headers))
                    clauses.append(Clause(id=f"{document_id}::p{page_no}:t{ti}:r{ri}",
                        document_id=document_id, label=f"table-{page_no}-{ti}-row-{ri}",
                        text=row_text, page=page_no, end_page=page_no, section=section,
                        kind="table_row", bbox=list(table.bbox)))
        flush()
    warnings.append("Automatically segmented clauses and table headers have not been human verified")
    return clauses, warnings


def ingest_pdf(store: Store, path: Path, document: Document):
    raw = path.read_bytes()
    if not raw.startswith(b"%PDF"):
        raise ValueError("Input is not a PDF")
    document = document.model_copy(update={"sha256": hashlib.sha256(raw).hexdigest(), "filename": path.name,
                                           "extractor_version":"numbered-v2"})
    clauses, warnings = extract_pdf(path, document.id)
    if not clauses:
        raise ValueError("No numbered clauses extracted; review PDF/OCR before importing")
    created = store.ingest(document, clauses)
    return {"document_id": document.id, "created": created, "clauses": len(clauses),
            "sha256": document.sha256, "warnings": warnings}
