"""Evaluate governed numeric-bound rules against UAD XML values.

The source rule remains the selected CSV row. Executable XPath and comparison
policy are governed separately in ``data/numeric-bound-bindings.ttl``.
"""

import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
from uuid import uuid4
from xml.etree import ElementTree as ET

from lxml import etree
from rdflib import Graph, Literal, Namespace, RDF

from app.models.common import Provenance
from app.models.enums import RuleType, Severity
from app.models.validation import Finding


B = Namespace("urn:uad36:numeric-bound-binding:")
BINDINGS = (
    Path(__file__).resolve().parents[2] / "data/numeric-bound-bindings.ttl"
)
NS = {"m": "http://www.mismo.org/residential/2009/schemas"}
SOURCE_COLUMNS = (
    "Message ID",
    "Unique ID",
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
    required = (
        "applicabilityXPath",
        "comparisonOperator",
        "element",
        "expectedDataLocation",
        "ruleId",
        "selectionXPath",
        "sourceFingerprint",
        "thresholdValue",
        "valueType",
        "violationKind",
    )
    bindings: dict[str, dict[str, str]] = {}
    for node in graph.subjects(RDF.type, B.Binding):
        record: dict[str, str] = {}
        for name in required:
            values = list(graph.objects(node, B[name]))
            if len(values) != 1 or not isinstance(values[0], Literal):
                raise ValueError(f"{node}: expected one literal {name}")
            record[name] = str(values[0])
        rule_id = record["ruleId"]
        if rule_id in bindings:
            raise ValueError(f"Duplicate numeric-bound binding: {rule_id}")
        bindings[rule_id] = record
    return bindings


def binding_for(row: dict[str, str]) -> dict[str, str] | None:
    record = load_bindings().get(row.get("Message ID"))
    if record is not None and fingerprint(row) != record["sourceFingerprint"]:
        raise ValueError(
            f"{row.get('Message ID')}: governed numeric-bound definition changed"
        )
    return record


def scalar_text(value) -> str:
    if isinstance(value, etree._Element):
        return "".join(value.itertext()).strip()
    return str(value).strip()


def typed_value(raw: str, value_type: str):
    if value_type == "decimal":
        try:
            return Decimal(raw)
        except InvalidOperation:
            return None
    if value_type == "date":
        try:
            return date.fromisoformat(raw)
        except ValueError:
            return None
    raise ValueError(f"Unsupported numeric-bound value type: {value_type}")


def compares(value, threshold, operator: str) -> bool:
    if operator == "lt":
        return value < threshold
    if operator == "le":
        return value <= threshold
    if operator == "eq":
        return value == threshold
    if operator == "gt":
        return value > threshold
    if operator == "ge":
        return value >= threshold
    raise ValueError(f"Unsupported numeric-bound operator: {operator}")


def violating_values(document, record: dict[str, str]) -> list[str]:
    tree = document.getroottree()
    applicability = record["applicabilityXPath"]
    if applicability and not tree.xpath(applicability, namespaces=NS):
        return []

    value_type = record["valueType"]
    threshold = typed_value(record["thresholdValue"], value_type)
    if threshold is None:
        raise ValueError(
            f"{record['ruleId']}: invalid governed threshold value"
        )

    violations = []
    for selected in tree.xpath(record["selectionXPath"], namespaces=NS):
        raw = scalar_text(selected)
        value = typed_value(raw, value_type)
        # Missing and malformed values are governed by other rule categories.
        if value is not None and compares(
            value, threshold, record["comparisonOperator"]
        ):
            violations.append(raw)
    return violations


def evaluate_numeric_bound(root, investor, row):
    record = binding_for(row)
    if record is None:
        return []

    document = etree.fromstring(ET.tostring(root, encoding="utf-8"))
    violations = violating_values(document, record)
    if not violations:
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
            violation_kind=record["violationKind"],
            data_location=record["expectedDataLocation"],
            observed_value=violations[0],
            expected_condition=row["Rule Logic"],
            source=Provenance(
                source_document="data/data-constraints.csv",
                source_version="UAD 3.6",
                source_section=row["Unique ID"],
            ),
            finding=row["Message Text"],
        )
    ]
