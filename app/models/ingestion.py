from typing import Literal

from pydantic import BaseModel, Field
from app.models.common import GraphResource, Provenance
from app.models.rules import ValidationRule


class SchemaIngestRequest(BaseModel):
    schema_name: str
    schema_version: str = "UAD 3.6"
    source_document: str = "GSE trimmed UAD 3.6 schema"
    source_section: str = "schema"
    raw_text: str | None = None


class MappingIngestRequest(BaseModel):
    mapping_name: str = "Appendix A mappings"
    source_version: str = "UAD 3.6"
    source_document: str = "UAD 3.6 Appendix A"
    source_section: str = "Appendix A"
    raw_text: str | None = None


class RulesIngestRequest(BaseModel):
    rule_set_name: str = "Appendix H rules"
    source_version: str = "UAD 3.6"
    source_document: str = "UAD 3.6 Appendix H"
    source_section: str = "Appendix H"
    raw_text: str | None = None


class SchemaCandidateResource(GraphResource):
    """Submitted XML retained for later analysis, not a validated schema model."""

    resource_type: Literal["xml_schema_candidate"] = "xml_schema_candidate"
    raw_text: str
    content_sha256: str
    ingestion_status: Literal["accepted_for_analysis"] = "accepted_for_analysis"


class IngestResponse(BaseModel):
    message: str
    resources_created: list[GraphResource] = Field(default_factory=list)
    rules_created: list[ValidationRule] = Field(default_factory=list)
    provenance: Provenance
    candidate_id: str | None = None
    ingestion_status: Literal["accepted_for_analysis"] | None = None
