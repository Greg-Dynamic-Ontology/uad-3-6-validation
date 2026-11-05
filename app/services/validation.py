from hashlib import sha256
import re
from uuid import uuid4
from xml.etree import ElementTree as ET

from rdflib import Graph, Literal, RDF, URIRef

from app.adapters.graph_store import graph_store
from app.core.namespaces import UAD
from app.models.common import Provenance
from app.models.enums import Investor, RuleType, Severity
from app.models.validation import (
    Finding,
    ConstraintSetIdentity,
    GovernedSchemaAssessment,
    UnevaluatedConstraint,
    ValidationCoverage,
    ValidationFailure,
    RdfArtifactSource,
    RdfProjectionArtifact,
    ValidationRequest,
    ValidationRun,
    ValidationSummary,
)
from app.services.required_data import NAMESPACE, ROOT, evaluate_required_data, load_required_rules
from app.services.gse_constraint_sources import read_active_compliance_workbook_rows
from app.services.xml_schema_validator import (
    UAD36_SCHEMA_PATH, UAD36_SCHEMA_VERSION, validate_uad36_xml_bytes,
)


EXECUTION_NAMESPACE = "https://dynamicontology.com/uad36/execution/"


class _AppraisalTreeBuilder(ET.TreeBuilder):
    def doctype(self, name, pubid, system):
        raise ValueError("DOCTYPE declarations are not supported.")


class ValidationService:
    def __init__(self) -> None:
        self.runs: dict[str, ValidationRun] = {}
        self.findings: dict[str, Finding] = {}
        self.execution_graphs: dict[str, Graph] = {}

    def validate(self, request: ValidationRequest) -> ValidationRun:
        findings: list[Finding] = []
        root = None
        xml_bytes = (request.xml_text or "").encode("utf-8")
        failure = None
        blocked_reason = None
        schema_assessment = None
        try:
            schema_report = validate_uad36_xml_bytes(
                package_name=request.package_name, xml_bytes=xml_bytes,
            )
            schema_assessment = GovernedSchemaAssessment(
                schema_name=schema_report.schema_name,
                schema_version=UAD36_SCHEMA_VERSION,
                sha256=sha256(UAD36_SCHEMA_PATH.read_bytes()).hexdigest(),
                well_formed=schema_report.well_formed,
                schema_valid=schema_report.schema_valid,
                findings=schema_report.findings,
            )
        except Exception as error:
            # An unavailable validator is not an XSD rejection of the upload.
            failure = ValidationFailure(
                message="XML Schema validation could not complete because the validation service is unavailable.",
                suggested_action="Please retry the same file. If the problem continues, contact support.",
            )
            blocked_reason = f"XML Schema validation unavailable: {type(error).__name__}: {error}"
        outcomes: list[dict[str, str]] = []
        coverage = None

        try:
            if not request.xml_text or not request.xml_text.strip():
                raise ValueError("The XML payload is empty.")

            parser = ET.XMLParser(target=_AppraisalTreeBuilder())
            root = ET.fromstring(request.xml_text, parser=parser)

            if not any(
                True
                for _ in root.iter(
                    f"{{{NAMESPACE}}}VALUATION_ANALYSIS"
                )
            ):
                raise ValueError(
                    "The XML contains no UAD VALUATION_ANALYSIS context."
                )

        except (ET.ParseError, ValueError) as error:
            root = None
            failure = ValidationFailure(
                message="The uploaded file could not be parsed as a readable UAD appraisal XML document.",
                suggested_action="Correct or re-export the XML file, then upload and submit the corrected file through the same validation path.",
            )
            blocked_reason = f"The upload could not be parsed as UAD XML: {error}"
            findings.append(
                Finding(
                    finding_id=f"F-{uuid4().hex[:8]}",
                    severity=Severity.ERROR,
                    investor=request.investor_scope,
                    rule_type=RuleType.SCHEMA,
                    data_location="/",
                    observed_value=str(error),
                    expected_condition=(
                        "A readable UAD 3.6 XML report package "
                        "containing VALUATION_ANALYSIS"
                    ),
                    source=Provenance(
                        source_document="GSE trimmed UAD 3.6 schema",
                        source_version="UAD 3.6",
                        source_section="schema",
                    ),
                    finding=(
                        "Submitted package is not a readable "
                        "UAD 3.6 appraisal XML document."
                    ),
                    requires_human_review=False,
                )
            )

        source = read_active_compliance_workbook_rows(
            configuration_path=ROOT / "config/configuration.ttl",
        )
        selected = sorted(row["Message ID"] for row in load_required_rules())
        if root is not None and schema_assessment is not None:
            try:
                findings.extend(evaluate_required_data(
                    root, request.investor_scope, evaluation_coverage=outcomes,
                ))
            except Exception as error:
                # An evaluator-wide failure must leave no apparent successful coverage.
                outcomes = [{
                    "rule_id": rule_id, "status": "not_evaluated",
                    "reason": f"{type(error).__name__}: {error}",
                } for rule_id in selected]
        else:
            outcomes = [{
                "rule_id": rule_id, "status": "not_evaluated",
                "reason": blocked_reason or "The required XML assessment is unavailable.",
            } for rule_id in selected]
        evaluated = sorted(item["rule_id"] for item in outcomes if item["status"] == "evaluated")
        unavailable = [UnevaluatedConstraint(
            rule_id=item["rule_id"], reason=item["reason"],
        ) for item in outcomes if item["status"] == "not_evaluated"]
        accounted = set(evaluated) | {item.rule_id for item in unavailable}
        unavailable.extend(UnevaluatedConstraint(
            rule_id=rule_id, reason="The selected rule produced no evaluation outcome.",
        ) for rule_id in selected if rule_id not in accounted)
        version = re.search(r"\bv(\d+(?:\.\d+)*)\b", source.worksheet_name)
        coverage = ValidationCoverage(
            source_rule_count=len(source.rows), selected_rule_ids=selected,
            evaluated_rule_ids=evaluated, not_evaluated=unavailable,
            unselected_rule_ids=sorted({row["Message ID"] for row in source.rows} - set(selected)),
            complete=not unavailable,
            constraint_set=ConstraintSetIdentity(
                version=version.group(1) if version else "unversioned",
                source_document=str(source.workbook_path),
                source_sheet=source.worksheet_name,
                sha256=sha256(source.workbook_path.read_bytes()).hexdigest(),
            ),
        )

        if coverage.not_evaluated and failure is None:
            failure = ValidationFailure(
                message="Validation could not complete all selected checks. Any available schema results and business-rule findings are incomplete.",
                suggested_action="Please retry the same file. If the problem continues, contact support and quote the validation run ID.",
            )

        rules = graph_store.list_rules()
        versions = {
            rule.provenance.source_version for rule in rules
        }
        versions.add("UAD 3.6")

        run = ValidationRun(
            run_id=f"VR-{uuid4().hex[:12]}",
            package_name=request.package_name,
            source_sha256=sha256(xml_bytes).hexdigest(),
            schema_assessment=schema_assessment,
            coverage=coverage,
            failure=failure,
            processing_status=(
                "failed" if root is None else
                "incomplete" if failure is not None or not coverage.complete else "completed"
            ),
            passed=(
                root is not None and schema_assessment is not None and schema_assessment.schema_valid
                and coverage is not None and coverage.complete
                and not any(f.severity in {Severity.FATAL, Severity.ERROR, Severity.CRITICAL} for f in findings)
            ),
            investor_scope=request.investor_scope,
            rule_set_versions=sorted(versions),
            summary=self._summarize(findings),
            findings=findings,
        )
        self.runs[run.run_id] = run

        for finding in findings:
            self.findings[finding.finding_id] = finding

        return run

    def get_run(self, run_id: str) -> ValidationRun | None:
        return self.runs.get(run_id)

    def record_rdf_projection(
        self,
        *,
        package_name: str,
        xml_bytes: bytes,
        triple_count: int,
    ) -> ValidationRun:
        """Record an RDF artifact and its source appraisal traceability."""
        run = ValidationRun(
            run_id=f"VR-{uuid4().hex[:12]}",
            investor_scope=Investor.BOTH,
            summary=ValidationSummary(),
            artifacts=[
                RdfProjectionArtifact(
                    source=RdfArtifactSource(
                        package_name=package_name,
                        sha256=sha256(xml_bytes).hexdigest(),
                    ),
                    triple_count=triple_count,
                )
            ],
        )
        self.runs[run.run_id] = run
        return run

    def record_rdf_projection_failure(
        self,
        *,
        technical_message: str,
        error_code: str = "RDF_PROJECTION_FAILED",
        business_message: str = (
            "The appraisal could not be prepared for validation."
        ),
    ) -> ValidationRun:
        """Record a failed projection as the run's authoritative RDF state."""
        run = ValidationRun(
            run_id=f"VR-{uuid4().hex[:12]}",
            investor_scope=Investor.BOTH,
            summary=ValidationSummary(error=1),
        )
        self.runs[run.run_id] = run

        pipeline_run = URIRef(
            f"{EXECUTION_NAMESPACE}{run.run_id}"
        )
        stage_execution = URIRef(
            f"{EXECUTION_NAMESPACE}{run.run_id}/rdf-projection"
        )
        error = URIRef(
            f"{EXECUTION_NAMESPACE}{run.run_id}/rdf-projection/error"
        )

        execution_graph = Graph()
        execution_graph.add(
            (pipeline_run, RDF.type, UAD.PipelineRun)
        )
        execution_graph.add(
            (pipeline_run, UAD.executionStatus, UAD.Failed)
        )
        execution_graph.add(
            (pipeline_run, UAD.hasStageExecution, stage_execution)
        )
        execution_graph.add(
            (stage_execution, RDF.type, UAD.RdfProjectionExecution)
        )
        execution_graph.add(
            (stage_execution, UAD.executionStatus, UAD.Failed)
        )
        execution_graph.add(
            (stage_execution, UAD.hasError, error)
        )
        execution_graph.add(
            (error, UAD.errorCode, Literal(error_code))
        )
        execution_graph.add(
            (error, UAD.businessMessage, Literal(business_message))
        )
        execution_graph.add(
            (error, UAD.technicalMessage, Literal(technical_message))
        )

        self.execution_graphs[run.run_id] = execution_graph
        return run

    def get_execution_graph(self, run_id: str) -> Graph | None:
        """Return the authoritative pipeline-execution RDF graph."""
        return self.execution_graphs.get(run_id)

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
            elif finding.severity == Severity.FATAL:
                summary.fatal += 1

        return summary


validation_service = ValidationService()