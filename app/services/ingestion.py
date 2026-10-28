from hashlib import sha256
from uuid import uuid4

from app.adapters.graph_store import graph_store
from app.adapters.iri import IriMintingService
from app.models.common import GraphResource, Provenance
from app.models.enums import Investor, RuleType, Severity
from app.models.ingestion import (
    IngestResponse,
    MappingIngestRequest,
    RulesIngestRequest,
    SchemaCandidateResource,
    SchemaIngestRequest,
)
from app.models.rules import ValidationRule
from app.services.schema_ingestion_gatekeeper import check_schema_candidate_xml


class IngestionService:
    def __init__(self) -> None:
        self.iri = IriMintingService()

    def ingest_schema(self, request: SchemaIngestRequest) -> IngestResponse:
        # Check XML syntax and schema root before creating or storing resources.
        # Metadata-only requests retain their existing behavior.
        if request.raw_text is not None:
            check_schema_candidate_xml(request.raw_text)
        provenance = Provenance(
            source_document=request.source_document,
            source_version=request.schema_version,
            source_section=request.source_section,
        )
        if request.raw_text is not None:
            # Each submission gets its own identity and provenance, including
            # repeated content. Hash the original text, not a reserialization.
            token = uuid4().hex
            candidate = SchemaCandidateResource(
                resource_id=f"schema-candidate:{token}",
                iri=self.iri.mint("schema-candidate", token),
                label=request.schema_name,
                provenance=provenance,
                raw_text=request.raw_text,
                content_sha256=sha256(request.raw_text.encode("utf-8")).hexdigest(),
            )
            graph_store.put_resource(candidate)
            return IngestResponse(
                message="Schema candidate accepted for analysis",
                resources_created=[candidate],
                provenance=provenance,
                candidate_id=candidate.resource_id,
                ingestion_status=candidate.ingestion_status,
            )

        resources = [
            GraphResource(
                resource_id="schema:root",
                iri=self.iri.mint("schema", "root"),
                resource_type="schema_element",
                label=request.schema_name,
                provenance=provenance,
            ),
            GraphResource(
                resource_id="datatype:string",
                iri=self.iri.mint("datatype", "string"),
                resource_type="datatype",
                label="string",
                provenance=provenance,
            ),
            GraphResource(
                resource_id="enum:placeholder",
                iri=self.iri.mint("enum", "placeholder"),
                resource_type="controlled_value",
                label="placeholder",
                provenance=provenance,
            ),
        ]
        for resource in resources:
            graph_store.put_resource(resource)
        return IngestResponse(message="Schema assets ingested", resources_created=resources, provenance=provenance)

    def ingest_mappings(self, request: MappingIngestRequest) -> IngestResponse:
        provenance = Provenance(
            source_document=request.source_document,
            source_version=request.source_version,
            source_section=request.source_section,
        )
        resources = [
            GraphResource(
                resource_id="predicate:placeholder-xlink",
                iri=self.iri.mint("relationship", "placeholder-xlink"),
                resource_type="xlink_predicate",
                label="placeholder-xlink",
                provenance=provenance,
            )
        ]
        for resource in resources:
            graph_store.put_resource(resource)
        return IngestResponse(message="Appendix A mapping assets ingested", resources_created=resources, provenance=provenance)

    def ingest_rules(self, request: RulesIngestRequest) -> IngestResponse:
        provenance = Provenance(
            source_document=request.source_document,
            source_version=request.source_version,
            source_section=request.source_section,
        )
        rules = [
            ValidationRule(
                rule_id="UAD36-AH-PLACEHOLDER-001",
                iri=self.iri.mint("rule", "UAD36-AH-PLACEHOLDER-001"),
                title="Placeholder Appendix H rule",
                rule_type=RuleType.APPENDIX_H,
                severity=Severity.ERROR,
                applies_to=Investor.BOTH,
                description="Placeholder rule for MVP scaffolding. Replace with parsed Appendix H rule.",
                provenance=provenance,
            )
        ]
        for rule in rules:
            graph_store.put_rule(rule)
        return IngestResponse(message="Appendix H rules ingested", rules_created=rules, provenance=provenance)


ingestion_service = IngestionService()
