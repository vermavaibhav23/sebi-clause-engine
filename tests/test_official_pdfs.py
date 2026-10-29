"""Offline integration checks on downloaded PDFs. These are not human gold labels."""
import json
from pathlib import Path
import pytest
from sebi_engine.models import Document, Query
from sebi_engine.ingest import ingest_pdf
from sebi_engine.extract import propose
from sebi_engine.search import answer
from sebi_engine.store import Store

ROOT=Path(__file__).parents[1]
MASTER="SEBI/HO/MIRSD/SECFATF/P/CIR/2023/169"
AMEND="SEBI/HO/MIRSD/SECFATF/P/CIR/2024/41"


@pytest.fixture(scope="module")
def official(tmp_path_factory):
    rows=json.loads((ROOT/"data"/"pilot_sources.json").read_text())
    if not all((ROOT/"runtime"/"pdfs"/r["local_filename"]).exists() for r in rows):
        pytest.skip("Run fetch-pilot to enable real-PDF integration checks; no test downloads")
    store=Store(tmp_path_factory.mktemp("official")/"test.sqlite")
    for row in rows:
        metadata={k:v for k,v in row.items() if k!="local_filename"}
        ingest_pdf(store,ROOT/"runtime"/"pdfs"/row["local_filename"],Document(**metadata))
    return store


def test_real_partial_amendment_proposals(official):
    result=propose(official,AMEND)
    events=[e for e in result["proposals"] if e["operation"]=="replace"]
    assert {e["target_label"] for e in events}=={"96","100"}
    assert all(e["status"]=="proposed" and e["effective_date"] is None for e in events)
    assert all(e["target_document_id"]==MASTER for e in events)
    assert propose(official,AMEND)["created"]==0


def test_unchanged_97_is_present_in_source(official):
    matches=[c for c in official.clauses() if c.document_id==MASTER and c.label=="97"]
    assert len(matches)==1
    assert "mobile number and email" in matches[0].text
    # This check establishes a parsed source passage, not current legal applicability.


def test_real_corpus_does_not_answer_through_unreviewed_changes(official):
    propose(official,AMEND)
    result=answer(official,Query(question="Which attributes do KRAs verify?",as_of="2024-05-31",
        scope_document_ids=[MASTER],scope_reviewed=True))
    assert result["status"]=="insufficient_evidence"
    assert any(i["reason"]=="unreviewed_amendment" for i in result["issues"])
