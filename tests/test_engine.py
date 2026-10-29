from datetime import date
import json
import pytest
from fastapi.testclient import TestClient
from sebi_engine.api import create_app
from sebi_engine.demo import seed_demo
from sebi_engine.evaluate import evaluate, score_amendments
from sebi_engine.extract import propose
from sebi_engine.models import Amendment, Clause, Document, Query, Review
from sebi_engine.resolve import resolve
from sebi_engine.search import answer
from sebi_engine.service import review_event
from sebi_engine.store import Store
from sebi_engine.coverage import coverage_report


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "test.sqlite")
    seed_demo(s)
    return s


def snap(store, when, **kw):
    return resolve(store, ["DEMO-BASE"], date.fromisoformat(when), **kw)


def clause(result, id):
    return next(c for c in result["clauses"] if c["id"] == id)


def test_publication_is_not_effective_date(store):
    assert "10 units" in clause(snap(store,"2024-03-15"),"DEMO-BASE:1")["text"]
    assert "20 units" in clause(snap(store,"2024-04-01"),"DEMO-BASE:1")["text"]


def test_preserves_old_unchanged_clause_and_citation(store):
    c = clause(snap(store,"2024-04-02"),"DEMO-BASE:2")
    assert c["text"] == "Records must be retained for 5 years."
    assert c["history"] == [] and c["citations"][0]["document_id"] == "DEMO-BASE"


def test_before_publication_does_not_leak_future_event(store):
    r = snap(store,"2024-04-02",known_at=date(2024,2,1))
    assert "10 units" in clause(r,"DEMO-BASE:1")["text"]


def test_deletion_preserves_audit(store):
    c = clause(snap(store,"2024-06-01"),"DEMO-BASE:3")
    assert c["status"] == "deleted" and c["history"] == ["demo-delete"]


def test_unknown_scope_is_not_empty_success(store):
    assert resolve(store,["missing"],date(2024,1,1))["issues"][0]["reason"] == "missing_document"


def test_proposal_blocks_guess(store):
    event = store.amendments()[0].model_dump()
    event.update(id="uncertain", status="proposed", effective_date=None, reviewer=None)
    store.put_amendment(Amendment(**event))
    q = Query(question="disclosure threshold",as_of="2024-07-01",scope_document_ids=["DEMO-BASE"],scope_reviewed=True)
    assert answer(store,q)["status"] == "insufficient_evidence"


def test_rejection_does_not_change_validity(store):
    event = store.amendments()[0].model_dump()
    event.update(id="rejected", status="rejected", effective_date=None)
    store.put_amendment(Amendment(**event))
    assert snap(store,"2024-04-02")["issues"] == []


def test_conflicting_same_date_edits_are_unresolved(store):
    e = next(x for x in store.amendments() if x.id == "demo-replace").model_dump()
    e.update(id="conflict",new_text="The disclosure threshold is 30 units.")
    store.put_amendment(Amendment(**e))
    r = snap(store,"2024-04-02")
    assert clause(r,"DEMO-BASE:1")["status"] == "unresolved"
    assert any(i["reason"] == "conflicting_or_inactive_target" for i in r["issues"])


def test_insert_does_not_replace_anchor(store):
    e = next(x for x in store.amendments() if x.id == "demo-replace").model_dump()
    e.update(id="insert",operation="insert",target_clause_id="DEMO-BASE:2",new_label="2.1",new_text="Keep an electronic copy.")
    store.put_amendment(Amendment(**e))
    r=snap(store,"2024-04-02")
    assert clause(r,"insert::insert")["text"] == "Keep an electronic copy."
    assert "5 years" in clause(r,"DEMO-BASE:2")["text"]


def test_full_supersession_does_not_invent_replacement_text(store):
    e = next(x for x in store.amendments() if x.id == "demo-replace").model_dump()
    e.update(id="supersede",operation="supersede",target_clause_id=None,effective_date="2024-05-01")
    store.put_amendment(Amendment(**e))
    assert all(c["status"] == "superseded" for c in snap(store,"2024-05-02")["clauses"])


def test_idempotent_ingestion_and_immutable_bytes(store):
    d = store.documents()[0]
    assert store.ingest(d,[]) is False
    with pytest.raises(ValueError,match="different bytes"):
        store.ingest(d.model_copy(update={"sha256":"different"}),[])


def test_approval_requires_date_and_reviewer():
    with pytest.raises(ValueError):
        Amendment(id="x",source_document_id="a",source_clause_id="a:1",target_document_id="b",
                  operation="supersede",evidence="x",status="approved",reviewer="")


def test_review_checks_target_membership(store):
    e=next(x for x in store.amendments() if x.id=="demo-replace").model_dump()
    e.update(id="review",status="proposed")
    store.put_amendment(Amendment(**e))
    with pytest.raises(ValueError,match="Target clause"):
        review_event(store,"review",Review(reviewer="R1",status="approved",effective_date="2024-04-01",
                     target_clause_id="DEMO-AMENDMENT:1",note="checked"))


def test_review_is_audited(store):
    review_event(store,"demo-replace",Review(reviewer="R1",status="rejected",note="fixture"))
    audit = store.audit()[-1]
    assert audit["action"] == "amendment_review"
    assert json.loads(audit["payload"])["before"]["status"] == "approved"


def test_unreviewed_scope_abstains(store):
    q=Query(question="disclosure threshold",as_of="2024-04-02",scope_document_ids=["DEMO-BASE"])
    assert answer(store,q)["issues"] == [{"reason":"corpus_scope_not_reviewed"}]


def test_irrelevant_query_abstains(store):
    q=Query(question="cryptocurrency mining tariffs",as_of="2024-04-02",scope_document_ids=["DEMO-BASE"],scope_reviewed=True)
    assert answer(store,q)["status"] == "insufficient_evidence"


def test_replacement_cites_original_and_amending_source(store):
    c=clause(snap(store,"2024-04-02"),"DEMO-BASE:1")
    assert {x["document_id"] for x in c["citations"]} == {"DEMO-BASE","DEMO-AMENDMENT"}


def test_extract_replacement_without_auto_approval(store):
    d=Document(id="AMEND",title="Amendment",publication_date="2024-07-01",sha256="test")
    store.ingest(d,[Clause(id="AMEND:1",document_id="AMEND",label="1",text="Please refer to DEMO-BASE. Para 2 shall read as follows: Retain records for 7 years.",page=1,end_page=1)])
    r=propose(store,"AMEND")
    e=r["proposals"][0]
    assert e["target_clause_id"]=="DEMO-BASE:2" and e["status"]=="proposed"
    assert e["new_text"]=="Retain records for 7 years." and e["effective_date"] is None


def test_reference_is_not_an_amendment(store):
    d=Document(id="REF",title="Reference",publication_date="2024-07-01",sha256="ref")
    store.ingest(d,[Clause(id="REF:1",document_id="REF",label="1",text="Please refer to DEMO-BASE for context.",page=1,end_page=1)])
    assert propose(store,"REF")["proposals"][0]["operation"]=="reference"


def test_rejects_unverified_benchmark(store,tmp_path):
    data=tmp_path/"qa.jsonl"
    data.write_text(json.dumps({"id":"draft","label_status":"draft"}))
    with pytest.raises(ValueError,match="two named reviewers"):
        evaluate(store,data,tmp_path/"out.json")


def test_exact_amendment_metric():
    g={"source_document_id":"a","target_document_id":"b","operation":"replace","effective_date":"2024-01-01"}
    p={**g,"effective_date":"2024-02-01"}
    assert score_amendments([p],[g])["exact_f1"]==0


def test_api_queries_and_validation(tmp_path):
    app=create_app(tmp_path/"api.sqlite")
    seed_demo(app.state.store)
    with TestClient(app) as client:
        assert client.get("/health").status_code==200
        assert "Clause Evidence Engine" in client.get("/").text
        assert client.get("/openapi.json").status_code==200
        assert client.post("/query",json={"question":"x","as_of":"not-a-date"}).status_code==422
        r=client.post("/query",json={"question":"disclosure threshold","as_of":"2024-04-02",
                      "scope_document_ids":["DEMO-BASE"],"scope_reviewed":True,"top_k":1})
        assert r.status_code==200 and "20 units" in r.json()["answer"]


def test_invalid_pdf_rejected(tmp_path):
    with TestClient(create_app(tmp_path/"api.sqlite")) as client:
        r=client.post("/ingest",data={"metadata":json.dumps({"id":"a","title":"x","publication_date":"2024-01-01"})},files={"file":("x.pdf",b"not pdf","application/pdf")})
        assert r.status_code==422


def test_later_amendment_can_target_inserted_provision(store):
    template=next(x for x in store.amendments() if x.id=="demo-replace").model_dump()
    first={**template,"id":"insertion","operation":"insert","target_clause_id":"DEMO-BASE:2",
           "new_label":"2.1","new_text":"Store one copy."}
    store.put_amendment(Amendment(**first))
    second={**template,"id":"edit-insertion","target_clause_id":"insert::insertion",
            "effective_date":"2024-05-01","new_text":"Store two copies.","status":"proposed"}
    store.put_amendment(Amendment(**second))
    review_event(store,"edit-insertion",Review(reviewer="test-reviewer",status="approved",note="Synthetic fixture date and source checked"))
    assert clause(snap(store,"2024-05-02"),"insert::insertion")["text"]=="Store two copies."
    assert clause(snap(store,"2024-05-02"),"DEMO-BASE:2")["history"]==[]


def test_review_can_resolve_unknown_target_document(store):
    event=next(x for x in store.amendments() if x.id=="demo-replace").model_dump()
    event.update(id="unknown-target",target_document_id="UNRESOLVED",target_clause_id=None,status="proposed")
    store.put_amendment(Amendment(**event))
    updated=review_event(store,"unknown-target",Review(reviewer="test-reviewer",status="approved",
        target_document_id="DEMO-BASE",target_clause_id="DEMO-BASE:1",note="Synthetic target resolved"))
    assert updated.target_document_id=="DEMO-BASE"


def test_coverage_reports_missing_reference_without_inventing_an_event(store):
    d=Document(id="REF",title="Reference",publication_date="2024-07-01",sha256="ref")
    store.ingest(d,[Clause(id="REF:1",document_id="REF",label="1",text="Refer to SEBI/HO/MIRSD/DoP/P/CIR/2022/46.",page=1,end_page=1)])
    result=coverage_report(store)
    assert result["missing_reference_candidates"][0]["circular_id"]=="SEBI/HO/MIRSD/DoP/P/CIR/2022/46"
    assert len(store.amendments())==2


def test_synthetic_evaluation_records_reproducible_fingerprints(store,tmp_path):
    from pathlib import Path
    dataset=Path(__file__).parents[1]/"data"/"synthetic_qa.jsonl"
    output=tmp_path/"evaluation.json"
    evaluate(store,dataset,output,allow_synthetic=True)
    first=json.loads(output.read_text())
    evaluate(store,dataset,output,allow_synthetic=True)
    second=json.loads(output.read_text())
    assert first["synthetic"] is True
    assert first["corpus_sha256"]==second["corpus_sha256"]
    assert first["summary"]["clause"]["extractive_rubric_accuracy"]==1
    assert first["summary"]["clause"]["required_evidence_recall"]==1
    assert first["summary"]["clause"]["questions_with_required_evidence"]==3
