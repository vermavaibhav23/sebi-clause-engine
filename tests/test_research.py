from datetime import date
import json
from pathlib import Path
import pytest
from sebi_engine.demo import seed_demo
from sebi_engine.store import Store
from sebi_engine.models import Amendment,Clause,Document,Query
from sebi_engine.search import answer
from sebi_engine.temporal import interval_distance
from sebi_engine.ingest import numbered_line
from sebi_engine.benchmark import compile_reviews,digest,freeze_split,write_jsonl
from sebi_engine.statistics import cluster_bootstrap
from sebi_engine.evaluate import evaluate
from sebi_engine.models import ClauseDateReview
from sebi_engine.service import review_clause_date
from sebi_engine.resolve import resolve


@pytest.fixture
def store(tmp_path):
    s=Store(tmp_path/"test.sqlite"); seed_demo(s); return s


def query(mode,question="disclosure threshold",when="2024-04-02"):
    return Query(question=question,as_of=when,baseline=mode,scope_document_ids=["DEMO-BASE"],scope_reviewed=True,top_k=1)


def uncertainty(store):
    e=next(e for e in store.amendments() if e.id=="demo-replace").model_dump()
    store.put_amendment(Amendment(**{**e,"id":"uncertain","status":"proposed","effective_date":None,"reviewer":None}))


def test_interval_control_matches_known_effect_boundaries(store):
    assert "10 units" in answer(store,query("interval",when="2024-03-31"))["answer"]
    assert "20 units" in answer(store,query("interval",when="2024-04-01"))["answer"]


def test_interval_control_preserves_unchanged_old_citation(store):
    result=answer(store,query("interval","records retained"))
    assert "5 years" in result["answer"]
    assert result["evidence"][0]["citations"][0]["document_id"]=="DEMO-BASE"


def test_interval_control_removes_deleted_provision(store):
    assert answer(store,query("interval","quarterly paper report","2024-06-01"))["status"]=="insufficient_evidence"


def test_interval_control_excludes_future_knowledge(store):
    q=query("interval"); q.known_at=date(2024,2,1)
    assert "10 units" in answer(store,q)["answer"]


def test_selective_gate_preserves_unrelated_answer(store):
    uncertainty(store)
    assert answer(store,query("clause","records retained"))["status"]=="insufficient_evidence"
    result=answer(store,query("clause_selective","records retained"))
    assert "5 years" in result["answer"] and result["out_of_query_issues"]


def test_selective_gate_blocks_relevant_uncertainty(store):
    uncertainty(store)
    assert answer(store,query("clause_selective"))["status"]=="insufficient_evidence"


def test_selective_gate_blocks_dependency_uncertainty(tmp_path):
    s=Store(tmp_path/"dep.sqlite")
    d=Document(id="BASE",title="Synthetic",kind="synthetic",publication_date="2024-01-01",effective_date="2024-01-01",sha256="x")
    s.ingest(d,[Clause(id="b1",document_id="BASE",label="1",text="Validation follows the conditions in paragraph 2.",page=1,end_page=1),
                Clause(id="b2",document_id="BASE",label="2",text="The deadline is ten days.",page=1,end_page=1)])
    s.put_amendment(Amendment(id="e",source_document_id="BASE",source_clause_id="b1",target_document_id="BASE",target_clause_id="b2",operation="replace",new_text="twenty days",evidence="Synthetic ambiguity"))
    q=Query(question="Validation conditions",as_of="2024-02-01",scope_document_ids=["BASE"],scope_reviewed=True,baseline="clause_selective",top_k=1)
    assert answer(s,q)["status"]=="insufficient_evidence"


def test_unknown_target_cannot_be_localized_away(store):
    e=next(e for e in store.amendments() if e.id=="demo-replace").model_dump()
    store.put_amendment(Amendment(**{**e,"id":"unknown","status":"proposed","target_document_id":"UNRESOLVED","target_clause_id":None}))
    assert answer(store,query("clause_selective","records retained"))["status"]=="insufficient_evidence"


def test_temporal_adapter_has_explicit_scores_and_label(store):
    result=answer(store,query("temporal_rerank"))
    assert "not a TimelyRAG reproduction" in result["notice"]
    assert 0<=result["evidence"][0]["temporal_affinity"]<=1


def test_expired_interval_has_positive_distance():
    assert interval_distance(date(2024,4,1),"2024-01-01","2024-04-01")==1


@pytest.mark.parametrize("text",["2011 SEBI KRA Regulations were amended", "9 and clause 13 were to come into effect", "180 days from the date"])
def test_parser_rejects_wrapped_reference_and_year(text):
    assert numbered_line(text) is None


@pytest.mark.parametrize("text,label",[("96. KRAs shall verify","96"),("2.1. Records of clients","2.1"),("2.10 Records of clients","2.10")])
def test_parser_retains_explicit_clause_labels(text,label):
    assert numbered_line(text)[1]==label


def review_packets(tmp_path):
    q={"id":"test","query":query("clause").model_dump(mode="json"),"stratum":"replacement"}
    base={"id":"test","question_sha256":digest(q),"human_attestation":True,"completed":True,
        "family_id":"synthetic-test-family","stratum":"changed","scope_complete":True,"should_abstain":False,"required_citation_ids":["DEMO-AMENDMENT:1"],
        "required_answer_fragments":["20 units"],"forbidden_answer_fragments":[],"outdated_citation_ids":[],
        "obsolete_answer_fragments":[],"rationale":"UNIT TEST ONLY: simulated completed reviews"}
    paths=[tmp_path/n for n in ["q.jsonl","a.jsonl","b.jsonl"]]
    for p,rows in zip(paths,[[q],[{**base,"reviewer":"synthetic-reviewer-a"}],[{**base,"reviewer":"synthetic-reviewer-b"}]]):
        write_jsonl(p,rows)
    return paths


def test_blank_reviews_cannot_create_gold(store,tmp_path):
    q,a,b=review_packets(tmp_path)
    row=json.loads(a.read_text()); row["human_attestation"]=False; write_jsonl(a,[row])
    with pytest.raises(ValueError,match="incomplete"):
        compile_reviews(q,a,b,store,tmp_path/"gold.jsonl")


def test_disagreement_does_not_silently_become_gold(store,tmp_path):
    q,a,b=review_packets(tmp_path)
    row=json.loads(b.read_text()); row["required_answer_fragments"]=["30 units"]; write_jsonl(b,[row])
    output=tmp_path/"gold.jsonl"
    result=compile_reviews(q,a,b,store,output)
    assert result["status"]=="needs_adjudication" and not output.exists()


def test_question_edits_invalidate_reviews(store,tmp_path):
    q,a,b=review_packets(tmp_path)
    row=json.loads(q.read_text()); row["query"]["question"]="Changed question"; write_jsonl(q,[row])
    with pytest.raises(ValueError,match="changed"):
        compile_reviews(q,a,b,store,tmp_path/"gold.jsonl")


def test_same_reviewer_cannot_count_twice(store,tmp_path):
    q,a,b=review_packets(tmp_path)
    row=json.loads(b.read_text()); row["reviewer"]="synthetic-reviewer-a"; write_jsonl(b,[row])
    with pytest.raises(ValueError,match="distinct"):
        compile_reviews(q,a,b,store,tmp_path/"gold.jsonl")


def test_successful_merge_keeps_review_hashes(store,tmp_path):
    q,a,b=review_packets(tmp_path)
    output=tmp_path/"gold.jsonl"; compile_reviews(q,a,b,store,output)
    assert json.loads(output.read_text())["review_provenance"]["question_sha256"]
    # The reviewers' confirmed category replaces the AI draft's "replacement" category.
    assert json.loads(output.read_text())["stratum"]=="changed"


def test_single_family_does_not_create_fake_heldout_split(store,tmp_path):
    q,a,b=review_packets(tmp_path)
    output=tmp_path/"gold.jsonl"; compile_reviews(q,a,b,store,output)
    with pytest.raises(ValueError,match="three independent"):
        freeze_split(output,tmp_path/"split.json")


def test_frozen_split_preserves_family_and_detects_dataset_changes(store,tmp_path):
    q,a,b=review_packets(tmp_path); gold=tmp_path/"gold.jsonl"; compile_reviews(q,a,b,store,gold)
    base=json.loads(gold.read_text()); rows=[]
    for i in range(6):
        rows.append({**base,"id":str(i),"family_id":f"fixture-family-{i//2}","query":{**base["query"],"question":f"Synthetic query topic {i//2}"}})
    write_jsonl(gold,rows); path=tmp_path/"split.json"; frozen=freeze_split(gold,path)
    assert frozen["question_assignments"]["0"]==frozen["question_assignments"]["1"]
    gold.write_text(gold.read_text()+"\n")
    with pytest.raises(ValueError,match="changed after"):
        evaluate(store,gold,tmp_path/"report.json",split_manifest=path)


def test_cluster_uncertainty_refuses_one_family():
    preds=[{"id":str(i),"mode":m,"family_id":"one","rubric_pass":m=="new"} for i in range(10) for m in ["new","old"]]
    assert cluster_bootstrap(preds,"new","old")["ci95"] is None


def test_calibration_families_cannot_enter_test(tmp_path):
    rows=[{"id":str(i),"label_status":"human_verified","family_id":f"fixture-{i}",
           "query":{"question":f"Synthetic topic {i}"}} for i in range(5)]
    path=tmp_path/"fixture.jsonl";write_jsonl(path,rows)
    frozen=freeze_split(path,tmp_path/"split.json",development_families=["fixture-0","fixture-1"])
    assert frozen["family_assignments"]["fixture-0"]=="dev"
    assert frozen["family_assignments"]["fixture-1"]=="dev"
    assert set(frozen["family_assignments"].values())=={"train","dev","test"}
    with pytest.raises(ValueError,match="too few untouched"):
        freeze_split(path,tmp_path/"invalid.json",development_families=[f"fixture-{i}" for i in range(4)])


def test_cluster_bootstrap_is_paired_and_reproducible():
    preds=[{"id":str(i),"mode":m,"family_id":str(i),"rubric_pass":i%2==0 or m=="new"} for i in range(8) for m in ["new","old"]]
    a=cluster_bootstrap(preds,"new","old",repetitions=100)
    assert a==cluster_bootstrap(preds,"new","old",repetitions=100)
    assert a["difference"]==.5


def test_provision_date_override_is_shared_by_both_resolvers(store):
    review_clause_date(store,ClauseDateReview(clause_id="DEMO-BASE:2",effective_date="2024-05-01",
        reviewer="synthetic-reviewer",evidence_clause_ids=["DEMO-BASE:2"],note="Synthetic delayed commencement test"))
    for mode in ["clause","interval"]:
        assert answer(store,query(mode,"records retained","2024-04-02"))["status"]=="insufficient_evidence"
        assert "5 years" in answer(store,query(mode,"records retained","2024-05-02"))["answer"]
    assert store.audit()[-1]["action"]=="initial_clause_date_review"


def test_later_document_cannot_rewrite_original_commencement(store):
    with pytest.raises(ValueError,match="same original document"):
        review_clause_date(store,ClauseDateReview(clause_id="DEMO-BASE:2",effective_date="2024-05-01",
            reviewer="synthetic-reviewer",evidence_clause_ids=["DEMO-AMENDMENT:1"],note="Not an initial date"))


def test_explicit_unknown_clause_date_overrides_document_default(store):
    review_clause_date(store,ClauseDateReview(clause_id="DEMO-BASE:2",effective_date=None,
        reviewer="synthetic-reviewer",evidence_clause_ids=["DEMO-BASE:2"],note="Synthetic unresolved initial date"))
    result=resolve(store,["DEMO-BASE"],date(2024,4,2))
    assert any(i["target_clause_id"]=="DEMO-BASE:2" for i in result["issues"])
    assert answer(store,query("clause_selective","records retained"))["status"]=="insufficient_evidence"


def test_adjudication_preserves_original_reviews(store,tmp_path):
    q,a,b=review_packets(tmp_path)
    row=json.loads(b.read_text()); row["required_answer_fragments"]=["30 units"]; write_jsonl(b,[row])
    left=json.loads(a.read_text());right=json.loads(b.read_text())
    fields=["family_id","stratum","scope_complete","should_abstain","required_citation_ids","required_answer_fragments",
            "forbidden_answer_fragments","outdated_citation_ids","obsolete_answer_fragments"]
    adj=tmp_path/"adjudication.jsonl"
    write_jsonl(adj,[{"id":"test","reviewer":"synthetic-third-reviewer","human_attestation":True,
        "rationale":"UNIT TEST ONLY: adjudicated synthetic source", "first_sha256":digest(left),"second_sha256":digest(right),
        "resolution":{k:left[k] for k in fields}}])
    output=tmp_path/"gold.jsonl"
    result=compile_reviews(q,a,b,store,output,adj)
    assert result["status"]=="compiled"
    assert json.loads(b.read_text())["required_answer_fragments"]==["30 units"]
    assert json.loads(output.read_text())["review_provenance"]["adjudicator"]=="synthetic-third-reviewer"


def test_reference_order_does_not_create_false_review_conflict(store,tmp_path):
    q,a,b=review_packets(tmp_path)
    for p,ids in [(a,["DEMO-AMENDMENT:1","DEMO-BASE:1"]),(b,["DEMO-BASE:1","DEMO-AMENDMENT:1"])]:
        row=json.loads(p.read_text());row["required_citation_ids"]=ids;write_jsonl(p,[row])
    assert compile_reviews(q,a,b,store,tmp_path/"gold.jsonl")["status"]=="compiled"


def test_research_api_and_review_form(tmp_path):
    from fastapi.testclient import TestClient
    from sebi_engine.api import create_app
    app=create_app(tmp_path/"api.sqlite"); seed_demo(app.state.store)
    with TestClient(app) as client:
        assert "Independent source review" in client.get("/annotate").text
        assert len(client.get("/research-status").json()["methods"])==7
        assert client.get("/research-packet/not-allowed.json").status_code==404
        assert client.post("/query",json=query("interval").model_dump(mode="json")).status_code==200
