from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field, computed_field


def utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class SchemaValidationStatus(StrEnum):
    """Overall outcome of XML Schema validation."""

    PASSED = "passed"
    FAILED = "failed"


class SchemaFindingSeverity(StrEnum):
    """Severity assigned to an XML or XML Schema validation finding."""

    WARNING = "warning"
    ERROR = "error"


class SchemaValidationFinding(BaseModel):
    """A single problem reported while parsing or validating an XML document."""

    severity: SchemaFindingSeverity = SchemaFindingSeverity.ERROR
    message: str

    line: int | None = Field(default=None, ge=1)
    column: int | None = Field(default=None, ge=1)

    error_code: str | None = None
    data_location: str | None = None


class SchemaValidationSummary(BaseModel):
    """Counts of findings produced during schema validation."""

    warning_count: int = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)

    @computed_field
    @property
    def finding_count(self) -> int:
        return self.warning_count + self.error_count


class SchemaValidationReport(BaseModel):
    """
    Structured result of validating one XML document against one XML Schema.

    A report is produced for successful validation, failed validation, and
    malformed XML. This allows every validation attempt to leave persistent
    engineering evidence.
    """

    report_id: str

    package_name: str
    schema_name: str
    schema_version: str | None = None

    created_at: datetime = Field(default_factory=utc_now)

    well_formed: bool
    status: SchemaValidationStatus

    summary: SchemaValidationSummary
    findings: list[SchemaValidationFinding] = Field(default_factory=list)

    @computed_field
    @property
    def schema_valid(self) -> bool:
        """
        Return True only when the XML is well formed and schema validation
        completed without errors.
        """
        return (
            self.well_formed
            and self.status == SchemaValidationStatus.PASSED
            and self.summary.error_count == 0
        )