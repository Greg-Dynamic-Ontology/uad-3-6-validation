from pydantic import BaseModel, Field
from app.models.common import Provenance
from app.models.enums import Investor, RuleType, Severity


class ValidationRule(BaseModel):
    rule_id: str
    iri: str
    title: str
    rule_type: RuleType
    severity: Severity = Severity.ERROR
    applies_to: Investor = Investor.BOTH
    description: str | None = None
    source_expression: str | None = None
    status: str = "active"
    provenance: Provenance


class RuleListResponse(BaseModel):
    rules: list[ValidationRule] = Field(default_factory=list)
