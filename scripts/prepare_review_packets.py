"""Create 50 AI-drafted questions and two BLANK independent review packets.

These are a feasibility workload, not 50 independent families or gold answers.
Never overwrites completed review files. Freeze questions before human review.
"""
import json
from pathlib import Path
from sebi_engine.store import Store
from sebi_engine.benchmark import digest,write_jsonl

ROOT=Path(__file__).resolve().parents[1]
store=Store(ROOT/"runtime"/"research.sqlite")
out=ROOT/"data"/"review_packets"
out.mkdir(exist_ok=True)
master="SEBI/HO/MIRSD/SECFATF/P/CIR/2023/169"
old="SEBI/HO/MIRSD/DoP/P/CIR/2022/46"
cyber="SEBI/HO/MIRSD/DOP/CIR/P/2019/111"
topics=[
    (master,"96","attributes","Which client-record attributes must KRAs verify, and within what period?","changed_candidate"),
    (master,"97","mobile","Must KRAs additionally verify the client's mobile number and email ID?","unchanged_candidate"),
    (master,"98","PAN exempt","Which attributes must KRAs verify for PAN-exempt records?","unchanged_candidate"),
    (master,"99","transact","Can a client transact when the required record attributes cannot be verified?","dependent_provision"),
    (master,"100","Validated Records","What conditions must a record satisfy to count as a Validated Record?","changed_candidate"),
    (master,"101","portability","Must a client repeat KYC when approaching another intermediary with validated records?","dependent_provision"),
    (master,"102","uniform","Who must follow uniform guidelines for verification and validation of attributes?","unchanged_candidate"),
    (master,"103","integrated","What integration is required between intermediaries and KRAs for document movement?","unchanged_candidate"),
    (master,"104","December","What deadline applies to verification of existing clients using non-Aadhaar OVDs?","date_sensitive"),
    (master,"106","one month","Within what period must a KRA take steps to redress an investor grievance?","unchanged_candidate"),
    (old,"9","180 days","From which date does the 180-day period for validating existing Aadhaar-based records run?","date_extension"),
    (old,"13","commence","On which date must validation of all new and existing KYC records commence?","date_extension"),
    (old,"8","2 days","What period is allowed for validating the Aadhaar-based KYC records of new clients?","unchanged_candidate"),
    (old,"10","dispatch","How and within what period must the KRA identifier be communicated to the client?","unchanged_candidate"),
    (old,"12","non-Aadhaar","When may a KRA validate KYC records based on a non-Aadhaar OVD?","date_sensitive"),
    (cyber,"11","critical","How should a KRA identify critical assets for its cybersecurity framework?","changed_candidate"),
    (cyber,"40","penetration","Which systems must be covered by a KRA's vulnerability assessment and penetration testing?","changed_candidate"),
    (cyber,"41","Remedial","What remediation and reporting obligations follow identified vulnerabilities?","changed_candidate"),
    (cyber,"42","commissioning","When is testing required before commissioning a new system?","changed_candidate"),
    (cyber,"51","Quarterly","How soon must a KRA report cyber incidents to SEBI?","changed_candidate"),
    (master,"35","consent","Is express client consent required before online KYC?","unchanged_candidate"),
    (master,"41","XML","How recent must an Aadhaar XML file or secure QR code be for offline verification?","unchanged_candidate"),
    (master,"42","voluntary","Is the client's use of Aadhaar mandatory or voluntary?","unchanged_candidate"),
    (master,"46","signature","Can an electronic signature be accepted instead of a wet signature?","unchanged_candidate"),
]
clauses=store.clauses(); docs={d.id:d for d in store.documents()}
questions=[]
for index,(doc,label,phrase,question,stratum) in enumerate(topics,1):
    candidates=[c for c in clauses if c.document_id==doc and c.label==label and phrase.casefold() in " ".join(c.text.split()).casefold()]
    if not candidates:
        raise ValueError(f"No source anchor for {doc} paragraph {label}")
    dates=["2022-06-23","2022-07-28"] if doc==old else ["2022-05-29","2022-07-06"] if doc==cyber else ["2024-05-13","2024-05-31"]
    for when in dates:
        questions.append({"id":f"kyc-{index:02d}-{when}","label_status":"ai_draft_not_gold",
            "stratum":stratum,"question_author":"AI draft; reviewers may reject or revise before freezing",
            "query":{"question":question,"as_of":when,"known_at":when,"scope_document_ids":[doc],"scope_reviewed":False,"top_k":3},
            "seed_source_anchors":[{"clause_id":c.id,"page":c.page,"source_url":docs[doc].source_url} for c in candidates],
            "review_instruction":"Seed anchors are discovery aids, not correct-answer labels. Audit intervening amendments, exceptions and dates; assign family_id independently."})
for key,question in [("negative-fee","What SEBI-prescribed fee must an investor pay for cryptocurrency mining approval?"),
                     ("missing-2026","Which KRA validation changes became applicable in October 2026?")]:
    questions.append({"id":key,"label_status":"ai_draft_not_gold","stratum":"unanswerable_candidate",
        "question_author":"AI draft","query":{"question":question,"as_of":"2026-10-29" if key=="missing-2026" else "2024-05-31",
            "scope_document_ids":[master],"scope_reviewed":False,"top_k":3},
        "seed_source_anchors":[],"review_instruction":"Determine whether the bounded corpus supports an answer; do not infer absence from a failed keyword search."})
qpath=out/"questions.jsonl"
if qpath.exists():
    raise SystemExit("Review packet already exists; create a versioned directory rather than overwrite questions or reviews")
write_jsonl(qpath,questions)
for reviewer in ["reviewer_a","reviewer_b"]:
    write_jsonl(out/(reviewer+".jsonl"),[{"id":q["id"],"question_sha256":digest(q),"reviewer":"",
        "human_attestation":False,"completed":False,"family_id":"","stratum":"","scope_complete":None,"should_abstain":None,
        "required_citation_ids":[],"required_answer_fragments":[],"forbidden_answer_fragments":[],
        "outdated_citation_ids":[],"obsolete_answer_fragments":[],"rationale":""} for q in questions])
write_jsonl(out/"amendment_review_queue.jsonl",[e.model_dump(mode="json") for e in store.amendments()])
write_jsonl(out/"document_date_review_queue.jsonl",[{"document_id":d.id,"publication_date":str(d.publication_date),
    "effective_date":str(d.effective_date) if d.effective_date else None,"date_evidence":d.date_evidence,
    "source_url":d.source_url,"status":"needs_independent_review","reviewer":"","note":""} for d in store.documents()])
print(json.dumps({"questions":len(questions),"gold_answers":0,"path":str(out)}))
