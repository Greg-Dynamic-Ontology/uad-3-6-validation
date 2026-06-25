from pydantic import BaseModel, Field
from app.models.common import Provenance, utc_now
from app.models.enums import Investor, RuleType, Severity
from datetime import datetime


class Finding(BaseModel):
    finding_id: str
    severity: Severity
    investor: Investor
    rule_type: RuleType
    data_location: str | None = None
    graph_resource_iri: str | None = None
    observed_value: str | None = None
    expected_condition: str | None = None
    rule_id: str | None = None
    source: Provenance | None = None
    finding: str
    requires_human_review: bool = False
    advisory: bool = False
    confidence: float | None = None


class ValidationRequest(BaseModel):
    package_name: str = "uploaded-uad36-package.xml"
    xml_text: str | None = None
    investor_scope: Investor = Investor.BOTH


class ValidationSummary(BaseModel):
    info: int = 0
    warning: int = 0
    error: int = 0
    critical: int = 0


class ValidationRun(BaseModel):
    run_id: str
    uad_version: str = "3.6"
    investor_scope: Investor
    rule_set_versions: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    summary: ValidationSummary
    findings: list[Finding] = Field(default_factory=list)


class ExplanationResponse(BaseModel):
    finding_id: str
    explanation: str
    authoritative_result_unchanged: bool = True
    advisory: bool = True


class RevisionHistoryReviewRequest(BaseModel):
    revision_history_detail: str
    related_finding_ids: list[str] = Field(default_factory=list)


class RevisionHistoryReviewResponse(BaseModel):
    comments: list[str]
    advisory: bool = True
    deterministic_failure: bool = False
