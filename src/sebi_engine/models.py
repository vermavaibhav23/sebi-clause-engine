from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, model_validator


class Document(BaseModel):
    id: str = Field(min_length=1)
    title: str
    publication_date: date
    effective_date: date | None = None
    source_url: str = ""
    sha256: str = ""
    filename: str = ""
    kind: Literal["circular", "master", "draft", "synthetic"] = "circular"
    date_evidence: str = ""
    extractor_version: str = "unspecified"


class Clause(BaseModel):
    id: str
    document_id: str
    label: str
    text: str
    page: int = Field(ge=1)
    end_page: int = Field(ge=1)
    section: str = ""
    kind: Literal["clause", "table_row"] = "clause"
    bbox: list[float] | None = None
    initial_effective_date: date | None = None
    applicability_reviewed: bool = False
    applicability_note: str = ""
    applicability_reviewer: str = ""


class ClauseDateReview(BaseModel):
    clause_id: str
    effective_date: date | None
    reviewer: str = Field(min_length=1)
    evidence_clause_ids: list[str] = Field(min_length=1)
    note: str = Field(min_length=5)


class Amendment(BaseModel):
    id: str
    source_document_id: str
    source_clause_id: str
    target_document_id: str
    target_clause_id: str | None = None
    target_label: str | None = None
    operation: Literal["replace", "insert", "delete", "supersede", "reference"]
    effective_date: date | None = None
    new_text: str | None = None
    new_label: str | None = None
    evidence: str
    status: Literal["proposed", "approved", "rejected"] = "proposed"
    reviewer: str | None = None
    review_note: str = ""

    @model_validator(mode="after")
    def approval_requirements(self):
        if self.status == "approved":
            if not self.reviewer or not self.reviewer.strip():
                raise ValueError("Approved events require an identified reviewer")
            if self.operation != "reference" and self.effective_date is None:
                raise ValueError("An effective date is required; publication is not a substitute")
            if self.operation in {"replace", "delete", "insert"} and not self.target_clause_id:
                raise ValueError("Resolve the exact target clause before approval")
            if self.operation in {"replace", "insert"} and not (self.new_text or "").strip():
                raise ValueError("Replacement/insertion requires text")
            if self.operation == "insert" and not self.new_label:
                raise ValueError("Insertion requires a new clause label")
        return self


class Review(BaseModel):
    reviewer: str = Field(min_length=1)
    status: Literal["approved", "rejected"]
    effective_date: date | None = None
    target_document_id: str | None = None
    target_clause_id: str | None = None
    operation: Literal["replace", "insert", "delete", "supersede", "reference"] | None = None
    new_text: str | None = None
    new_label: str | None = None
    note: str = ""


class Query(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    as_of: date
    known_at: date | None = None
    scope_document_ids: list[str] = Field(default_factory=list)
    top_k: int = Field(default=4, ge=1, le=10)
    baseline: Literal["clause", "clause_selective", "ordinary", "recency", "document", "interval", "temporal_rerank"] = "clause"
    temporal_weight: float = Field(default=0.5, ge=0, le=1)
    candidate_pool: int = Field(default=100, ge=10, le=1000)
    scope_reviewed: bool = False
    # Explicit caller acknowledgement of a bounded, reviewed corpus; not legal completeness.
