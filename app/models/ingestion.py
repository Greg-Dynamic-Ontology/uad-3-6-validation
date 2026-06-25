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


class IngestResponse(BaseModel):
    message: str
    resources_created: list[GraphResource] = Field(default_factory=list)
    rules_created: list[ValidationRule] = Field(default_factory=list)
    provenance: Provenance
