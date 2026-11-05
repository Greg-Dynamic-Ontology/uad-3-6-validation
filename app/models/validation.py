from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.schema_validation import SchemaValidationFinding
from app.models.common import Provenance, utc_now
from app.models.enums import Investor, RuleType, Severity


class Finding(BaseModel):
    finding_id: str
    severity: Severity
    investor: Investor
    rule_type: RuleType
    data_location: str | None = None
    nearest_existing_ancestor: str | None = None
    graph_resource_iri: str | None = None
    observed_value: str | None = None
    expected_condition: str | None = None
    rule_id: str | None = None
    row_id: str | None = None
    primary_data_element: str | None = None
    property_affected: str | None = None
    violation_kind: str | None = None
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
    fatal: int = 0


class RdfArtifactSource(BaseModel):
    package_name: str
    sha256: str


class RdfProjectionArtifact(BaseModel):
    artifact_type: str = "rdf-instance-graph"
    produced_by: str = "rdf-projection"
    source: RdfArtifactSource
    triple_count: int = Field(ge=0)


class GovernedSchemaAssessment(BaseModel):
    """XSD outcome for the same upload; separate from business findings."""
    schema_name: str
    schema_version: str
    sha256: str
    well_formed: bool
    schema_valid: bool
    findings: list[SchemaValidationFinding] = Field(default_factory=list)


class ConstraintSetIdentity(BaseModel):
    version: str
    source_document: str
    source_sheet: str
    sha256: str


class UnevaluatedConstraint(BaseModel):
    rule_id: str
    reason: str


class ValidationCoverage(BaseModel):
    """Completeness is relative to selected rules, not the whole workbook."""
    scope: str = "selected-constraints"
    source_rule_count: int
    selected_rule_ids: list[str]
    evaluated_rule_ids: list[str]
    not_evaluated: list[UnevaluatedConstraint]
    unselected_rule_ids: list[str]
    complete: bool
    constraint_set: ConstraintSetIdentity


class ValidationFailure(BaseModel):
    """Customer-facing explanation of processing failure and recovery action."""
    message: str
    suggested_action: str


class ValidationRun(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    package_name: str | None = None
    source_sha256: str | None = None
    schema_assessment: GovernedSchemaAssessment | None = Field(default=None, alias="schema")
    coverage: ValidationCoverage | None = None
    failure: ValidationFailure | None = None
    processing_status: str | None = None
    passed: bool | None = None
    run_id: str
    uad_version: str = "3.6"
    investor_scope: Investor
    rule_set_versions: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    summary: ValidationSummary
    findings: list[Finding] = Field(default_factory=list)
    artifacts: list[RdfProjectionArtifact] = Field(default_factory=list)


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