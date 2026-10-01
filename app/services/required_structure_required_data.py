"""Evaluate governed required-structure bindings.

Production reads the rule rows from the supplied CSV and the independently
governed bindings in ``data/required-structure-bindings.ttl``. Test fixtures
and expected test results are never read by this module.
"""

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from uuid import uuid4
from xml.etree import ElementTree as ET

from lxml import etree
from rdflib import Graph, Literal, Namespace, RDF

from app.models.common import Provenance
from app.models.enums import RuleType, Severity
from app.models.validation import Finding


B = Namespace("urn:uad36:required-structure-binding:")
BINDINGS = Path(__file__).resolve().parents[2] / "data/required-structure-bindings.ttl"
NAMESPACE = "http://www.mismo.org/residential/2009/schemas"
NS = {"m": NAMESPACE}
SOURCE_COLUMNS = (
    "Unique ID",
    "Message ID",
    "Primary Data Element",
    "Rule Logic",
    "Severity",
    "Property Affected",
    " xPath",
    "Message Text",
)


def fingerprint(row: dict[str, str]) -> str:
    return hashlib.sha256(
        json.dumps(
            [row.get(key) for key in SOURCE_COLUMNS],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


@lru_cache(maxsize=1)
def load_bindings() -> dict[str, dict[str, str]]:
    graph = Graph().parse(BINDINGS, format="turtle")
    bindings: dict[str, dict[str, str]] = {}
    fields = (
        "ruleId",
        "sourceFingerprint",
        "applicabilityXPath",
        "requiredStructureXPath",
        "expectedDataLocation",
        "element",
    )
    for node in graph.subjects(RDF.type, B.Binding):
        record = {}
        for name in fields:
            values = list(graph.objects(node, B[name]))
            if len(values) != 1 or not isinstance(values[0], Literal):
                raise ValueError(f"{node}: expected one literal {name}")
            record[name] = str(values[0])
        rule_id = record["ruleId"]
        if rule_id in bindings:
            raise ValueError(f"Duplicate required-structure binding: {rule_id}")
        bindings[rule_id] = record
    return bindings


def binding_for(row: dict[str, str]) -> dict[str, str] | None:
    record = load_bindings().get(row.get("Message ID"))
    if record is not None and fingerprint(row) != record["sourceFingerprint"]:
        raise ValueError(
            f"{row.get('Message ID')}: governed required-structure definition changed"
        )
    return record


def evaluate_required_structure(root, investor, row):
    record = binding_for(row)
    if record is None:
        return []

    document = etree.fromstring(ET.tostring(root, encoding="utf-8"))
    if record["applicabilityXPath"] and not document.getroottree().xpath(
        record["applicabilityXPath"], namespaces=NS
    ):
        return []
    matches = document.getroottree().xpath(
        record["requiredStructureXPath"], namespaces=NS
    )
    if matches:
        return []

    return [
        Finding(
            finding_id=f"F-{uuid4().hex[:8]}",
            severity=Severity(row["Severity"].casefold()),
            investor=investor,
            rule_type=RuleType.APPENDIX_H,
            rule_id=row["Message ID"],
            row_id=row["Unique ID"],
            primary_data_element=record["element"],
            property_affected=row["Property Affected"],
            violation_kind="MissingRequiredStructure",
            data_location=record["expectedDataLocation"],
            observed_value="required container, collection, or value is absent",
            expected_condition=row["Rule Logic"],
            source=Provenance(
                source_document="data/data-constraints.csv",
                source_version="UAD 3.6",
                source_section=row["Unique ID"],
            ),
            finding=row["Message Text"],
        )
    ]
