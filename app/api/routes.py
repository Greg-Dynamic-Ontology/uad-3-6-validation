from fastapi import APIRouter, HTTPException
from app.adapters.graph_store import graph_store
from app.adapters.llm import llm_client
from app.models.enums import Investor
from app.models.ingestion import IngestResponse, MappingIngestRequest, RulesIngestRequest, SchemaIngestRequest
from app.models.validation import (
    ExplanationResponse,
    RevisionHistoryReviewRequest,
    RevisionHistoryReviewResponse,
    ValidationRequest,
    ValidationRun,
)
from app.services.ingestion import ingestion_service
from app.services.validation import validation_service

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "uad_version": "3.6"}


@router.post("/ingest/schema", response_model=IngestResponse)
def ingest_schema(request: SchemaIngestRequest) -> IngestResponse:
    return ingestion_service.ingest_schema(request)


@router.post("/ingest/mappings", response_model=IngestResponse)
def ingest_mappings(request: MappingIngestRequest) -> IngestResponse:
    return ingestion_service.ingest_mappings(request)


@router.post("/ingest/rules", response_model=IngestResponse)
def ingest_rules(request: RulesIngestRequest) -> IngestResponse:
    return ingestion_service.ingest_rules(request)


@router.get("/resources/{resource_id}")
def get_resource(resource_id: str):
    resource = graph_store.get_resource(resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource


@router.post("/validate/uad36", response_model=ValidationRun)
def validate_uad36(request: ValidationRequest) -> ValidationRun:
    request.investor_scope = Investor.BOTH
    return validation_service.validate(request)


@router.post("/validate/uad36/fannie", response_model=ValidationRun)
def validate_uad36_fannie(request: ValidationRequest) -> ValidationRun:
    request.investor_scope = Investor.FANNIE_MAE
    return validation_service.validate(request)


@router.post("/validate/uad36/freddie", response_model=ValidationRun)
def validate_uad36_freddie(request: ValidationRequest) -> ValidationRun:
    request.investor_scope = Investor.FREDDIE_MAC
    return validation_service.validate(request)


@router.get("/validation-runs/{run_id}", response_model=ValidationRun)
def get_validation_run(run_id: str) -> ValidationRun:
    run = validation_service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Validation run not found")
    return run


@router.post("/explain/finding/{finding_id}", response_model=ExplanationResponse)
def explain_finding(finding_id: str) -> ExplanationResponse:
    finding = validation_service.get_finding(finding_id)
    return ExplanationResponse(
        finding_id=finding_id,
        explanation=llm_client.explain_finding(finding, finding_id),
    )


@router.post("/review/revision-history", response_model=RevisionHistoryReviewResponse)
def review_revision_history(request: RevisionHistoryReviewRequest) -> RevisionHistoryReviewResponse:
    return RevisionHistoryReviewResponse(
        comments=llm_client.review_revision_history(
            request.revision_history_detail,
            request.related_finding_ids,
        )
    )


@router.get("/rules")
def list_rules():
    return {"rules": graph_store.list_rules()}


@router.get("/rules/{rule_id}")
def get_rule(rule_id: str):
    rule = graph_store.get_rule(rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.get("/schema/elements/{element_name}")
def get_schema_element(element_name: str):
    element = graph_store.find_schema_element(element_name)
    if element is None:
        raise HTTPException(status_code=404, detail="Schema element not found")
    return element
