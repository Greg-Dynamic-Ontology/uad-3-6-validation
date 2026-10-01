"""Evaluate governed uniqueness and cardinality bindings.

Production reads source rows from the supplied CSV and executable policy from
``data/uniqueness-cardinality-bindings.ttl``. Test fixtures and expected test
results are never read here.
"""

import hashlib
import json
from collections import Counter
from functools import lru_cache
from pathlib import Path
from uuid import uuid4
from xml.etree import ElementTree as ET

from lxml import etree
from rdflib import Graph, Literal, Namespace, RDF

from app.models.common import Provenance
from app.models.enums import RuleType, Severity
from app.models.validation import Finding


B = Namespace("urn:uad36:uniqueness-cardinality-binding:")
BINDINGS = (
    Path(__file__).resolve().parents[2]
    / "data/uniqueness-cardinality-bindings.ttl"
)
NAMESPACE = "http://www.mismo.org/residential/2009/schemas"
NS = {
    "m": NAMESPACE,
    "xlink": "http://www.w3.org/1999/xlink",
}
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
def load_bindings() -> dict[str, dict[str, object]]:
    graph = Graph().parse(BINDINGS, format="turtle")
    bindings: dict[str, dict[str, object]] = {}
    required = (
        "ruleId",
        "sourceFingerprint",
        "evaluationMode",
        "selectionXPath",
        "scopeXPath",
        "memberXPath",
        "governedCount",
        "expectedDataLocation",
        "element",
        "violationKind",
    )
    for node in graph.subjects(RDF.type, B.Binding):
        record: dict[str, object] = {}
        for name in required:
            values = list(graph.objects(node, B[name]))
            if len(values) != 1 or not isinstance(values[0], Literal):
                raise ValueError(f"{node}: expected one literal {name}")
            record[name] = values[0].toPython()
        governed_values = list(graph.objects(node, B.governedValue))
        if not all(isinstance(item, Literal) for item in governed_values):
            raise ValueError(f"{node}: governedValue must be a literal")
        record["governedValues"] = tuple(
            sorted(str(item) for item in governed_values)
        )
        rule_id = str(record["ruleId"])
        if rule_id in bindings:
            raise ValueError(
                f"Duplicate uniqueness/cardinality binding: {rule_id}"
            )
        bindings[rule_id] = record
    return bindings


def binding_for(row: dict[str, str]) -> dict[str, object] | None:
    record = load_bindings().get(row.get("Message ID"))
    if record is not None and fingerprint(row) != record["sourceFingerprint"]:
        raise ValueError(
            f"{row.get('Message ID')}: governed uniqueness/cardinality "
            "definition changed"
        )
    return record


def scalar_value(value) -> str:
    if isinstance(value, etree._Element):
        return "".join(value.itertext()).strip()
    return str(value).strip()


def has_duplicate_values(values, governed_values=()) -> bool:
    allowed = set(governed_values)
    normalized = [scalar_value(value) for value in values]
    normalized = [value for value in normalized if value]
    if allowed:
        normalized = [value for value in normalized if value in allowed]
    return any(count > 1 for count in Counter(normalized).values())


def violates(document, record: dict[str, object]) -> bool:
    mode = str(record["evaluationMode"])
    count = int(record["governedCount"])
    selection = str(record["selectionXPath"])
    scope_path = str(record["scopeXPath"])
    member_path = str(record["memberXPath"])
    governed_values = tuple(record["governedValues"])
    tree = document.getroottree()

    if mode == "max-count-global":
        return len(tree.xpath(selection, namespaces=NS)) > count
    if mode == "exact-count-global":
        return len(tree.xpath(selection, namespaces=NS)) != count
    if mode == "unique-value-global":
        return has_duplicate_values(
            tree.xpath(selection, namespaces=NS)
        )

    scopes = tree.xpath(scope_path, namespaces=NS)
    if mode == "max-count-per-scope":
        return any(
            len(scope.xpath(member_path, namespaces=NS)) > count
            for scope in scopes
        )
    if mode == "exact-count-per-scope":
        return any(
            len(scope.xpath(member_path, namespaces=NS)) != count
            for scope in scopes
        )
    if mode == "unique-value-per-scope":
        return any(
            has_duplicate_values(scope.xpath(member_path, namespaces=NS))
            for scope in scopes
        )
    if mode == "unique-governed-values-per-scope":
        return any(
            has_duplicate_values(
                scope.xpath(member_path, namespaces=NS), governed_values
            )
            for scope in scopes
        )
    if mode == "as-is-exclusive-per-scope":
        for scope in scopes:
            conditions = scope.xpath(member_path, namespaces=NS)
            conclusion_types = [
                scalar_value(value)
                for condition in conditions
                for value in condition.xpath(
                    ".//m:PropertyValuationConditionalConclusionType",
                    namespaces=NS,
                )
            ]
            if "AsIs" in conclusion_types and len(conditions) > count:
                return True
        return False

    raise ValueError(f"Unsupported evaluation mode: {mode}")


def evaluate_uniqueness_cardinality(root, investor, row):
    record = binding_for(row)
    if record is None:
        return []

    document = etree.fromstring(ET.tostring(root, encoding="utf-8"))
    if not violates(document, record):
        return []

    return [
        Finding(
            finding_id=f"F-{uuid4().hex[:8]}",
            severity=Severity(row["Severity"].casefold()),
            investor=investor,
            rule_type=RuleType.APPENDIX_H,
            rule_id=row["Message ID"],
            row_id=row["Unique ID"],
            primary_data_element=str(record["element"]),
            property_affected=row["Property Affected"],
            violation_kind=str(record["violationKind"]),
            data_location=str(record["expectedDataLocation"]),
            observed_value="prohibited duplicate or occurrence count",
            expected_condition=row["Rule Logic"],
            source=Provenance(
                source_document="data/data-constraints.csv",
                source_version="UAD 3.6",
                source_section=row["Unique ID"],
            ),
            finding=row["Message Text"],
        )
    ]
