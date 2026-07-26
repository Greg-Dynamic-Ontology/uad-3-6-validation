"""Context shared by SchemaLoader helper methods."""

from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET

from app.models.schema_model import SchemaModel


@dataclass(slots=True)
class SchemaLoaderContext:
    """State shared by all schema loading passes."""

    path: Path
    tree: ET.ElementTree
    root: ET.Element
    schema: SchemaModel