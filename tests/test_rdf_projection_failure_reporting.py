"""Acceptance test for IT-4R4S1 RDF projection failure reporting."""

from fastapi.testclient import TestClient
from rdflib import Literal, RDF

from app.core.namespaces import UAD
from app.main import app
from app.services.rdf_projection import RdfProjector
from app.services.validation import validation_service


client = TestClient(app, raise_server_exceptions=False)


def test_rdf_projection_failure_is_recorded_and_stops_the_pipeline(
    monkeypatch,
) -> None:
    """A projection failure is reported and no dependent stage runs."""

    technical_message = "projection engine could not create a graph"

    def fail_projection(
        self,
        *,
        xml_bytes: bytes,
        source_name: str,
    ):
        raise RuntimeError(technical_message)

    monkeypatch.setattr(RdfProjector, "project", fail_projection)

    response = client.post(
        "/validate/uad36/pipeline",
        data={"pipeline": "rdf-projection"},
        files={
            "file": (
                "appraisal.xml",
                b'<MESSAGE xmlns="https://example.com/uad#" />',
                "application/xml",
            )
        },
    )

    assert response.status_code == 200

    report = response.json()
    run_id = report["run_id"]

    assert report["status"] == "failed"
    assert report["stages"] == [
        {
            "name": "rdf-projection",
            "status": "failed",
            "error": {
                "code": "RDF_PROJECTION_FAILED",
                "business_message": (
                    "The appraisal could not be prepared for validation."
                ),
            },
        }
    ]

    validation_run = validation_service.get_run(run_id)
    assert validation_run is not None
    assert validation_run.artifacts == []

    execution_graph = validation_service.get_execution_graph(run_id)
    assert execution_graph is not None

    pipeline_runs = set(
        execution_graph.subjects(RDF.type, UAD.PipelineRun)
    )
    assert len(pipeline_runs) == 1
    pipeline_run = pipeline_runs.pop()
    assert (pipeline_run, UAD.executionStatus, UAD.Failed) in execution_graph

    stage_executions = set(
        execution_graph.objects(pipeline_run, UAD.hasStageExecution)
    )
    assert len(stage_executions) == 1
    stage_execution = stage_executions.pop()
    assert (
        stage_execution,
        RDF.type,
        UAD.RdfProjectionExecution,
    ) in execution_graph
    assert (
        stage_execution,
        UAD.executionStatus,
        UAD.Failed,
    ) in execution_graph

    errors = set(execution_graph.objects(stage_execution, UAD.hasError))
    assert len(errors) == 1
    error = errors.pop()
    assert (
        error,
        UAD.errorCode,
        Literal("RDF_PROJECTION_FAILED"),
    ) in execution_graph
    assert (
        error,
        UAD.businessMessage,
        Literal("The appraisal could not be prepared for validation."),
    ) in execution_graph
    assert (
        error,
        UAD.technicalMessage,
        Literal(technical_message),
    ) in execution_graph
