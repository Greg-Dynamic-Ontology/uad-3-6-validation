from uuid import uuid4
from app.adapters.graph_store import graph_store
from app.models.common import Provenance
from app.models.enums import Investor, RuleType, Severity
from app.models.validation import Finding, ValidationRequest, ValidationRun, ValidationSummary


class ValidationService:
    def __init__(self) -> None:
        self.runs: dict[str, ValidationRun] = {}
        self.findings: dict[str, Finding] = {}

    def validate(self, request: ValidationRequest) -> ValidationRun:
        findings: list[Finding] = []
        if not request.xml_text or not request.xml_text.strip().startswith("<"):
            findings.append(
                Finding(
                    finding_id=f"F-{uuid4().hex[:8]}",
                    severity=Severity.ERROR,
                    investor=request.investor_scope,
                    rule_type=RuleType.SCHEMA,
                    data_location="/",
                    observed_value="empty or non-XML payload",
                    expected_condition="A readable UAD 3.6 XML report package",
                    source=Provenance(
                        source_document="GSE trimmed UAD 3.6 schema",
                        source_version="UAD 3.6",
                        source_section="schema",
                    ),
                    finding="Submitted package is not a readable XML document.",
                    requires_human_review=False,
                )
            )

        rules = graph_store.list_rules()
        rule_set_versions = sorted({rule.provenance.source_version for rule in rules}) or ["UAD 3.6"]
        summary = self._summarize(findings)
        run = ValidationRun(
            run_id=f"VR-{uuid4().hex[:12]}",
            investor_scope=request.investor_scope,
            rule_set_versions=rule_set_versions,
            summary=summary,
            findings=findings,
        )
        self.runs[run.run_id] = run
        for finding in findings:
            self.findings[finding.finding_id] = finding
        return run

    def get_run(self, run_id: str) -> ValidationRun | None:
        return self.runs.get(run_id)

    def get_finding(self, finding_id: str) -> Finding | None:
        return self.findings.get(finding_id)

    @staticmethod
    def _summarize(findings: list[Finding]) -> ValidationSummary:
        summary = ValidationSummary()
        for finding in findings:
            if finding.severity == Severity.INFO:
                summary.info += 1
            elif finding.severity == Severity.WARNING:
                summary.warning += 1
            elif finding.severity == Severity.ERROR:
                summary.error += 1
            elif finding.severity == Severity.CRITICAL:
                summary.critical += 1
        return summary


validation_service = ValidationService()
