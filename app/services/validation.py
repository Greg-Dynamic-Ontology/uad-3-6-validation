from hashlib import sha256
from uuid import uuid4
from xml.etree import ElementTree as ET

from rdflib import Graph, Literal, RDF, URIRef

from app.adapters.graph_store import graph_store
from app.core.namespaces import UAD
from app.models.common import Provenance
from app.models.enums import Investor, RuleType, Severity
from app.models.validation import (
    Finding,
    RdfArtifactSource,
    RdfProjectionArtifact,
    ValidationRequest,
    ValidationRun,
    ValidationSummary,
)
from app.services.required_data import NAMESPACE, evaluate_required_data


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

        if root is not None:
            findings.extend(
                evaluate_required_data(root, request.investor_scope)
            )

        rules = graph_store.list_rules()
        versions = {
            rule.provenance.source_version for rule in rules
        }
        versions.add("UAD 3.6")

        run = ValidationRun(
            run_id=f"VR-{uuid4().hex[:12]}",
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