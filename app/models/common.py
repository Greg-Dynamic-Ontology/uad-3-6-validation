from datetime import datetime, timezone
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Provenance(BaseModel):
    source_document: str
    source_version: str
    source_section: str
    ingestion_timestamp: datetime = Field(default_factory=utc_now)


class GraphResource(BaseModel):
    resource_id: str
    iri: str
    resource_type: str
    label: str | None = None
    source_xml_location: str | None = None
    provenance: Provenance
