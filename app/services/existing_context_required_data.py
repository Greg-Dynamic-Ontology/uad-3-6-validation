"""Evaluate required values within existing applicable XML contexts."""

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


B = Namespace("urn:uad36:existing-context-required-binding:")
BINDINGS = (
    Path(__file__).resolve().parents[2]
    / "data/existing-context-required-bindings.ttl"
)
NS = {"m": "http://www.mismo.org/residential/2009/schemas"}
XSI_NIL = "{http://www.w3.org/2001/XMLSchema-instance}nil"
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
    fields = (
        "contextXPath",
        "element",
        "expectedDataLocation",
        "requiredValueRelativeXPath",
        "ruleId",
        "sourceFingerprint",
        "violationKind",
    )
    bindings: dict[str, dict[str, str]] = {}
    for node in graph.subjects(RDF.type, B.Binding):
        record = {}
        for name in fields:
            values = list(graph.objects(node, B[name]))
            if len(values) != 1 or not isinstance(values[0], Literal):
                raise ValueError(f"{node}: expected one literal {name}")
            record[name] = str(values[0])
        rule_id = record["ruleId"]
        if rule_id in bindings:
            raise ValueError(
                f"Duplicate existing-context binding: {rule_id}"
            )
        bindings[rule_id] = record
    return bindings


def binding_for(row: dict[str, str]) -> dict[str, str] | None:
    record = load_bindings().get(row.get("Message ID"))
    if record is not None and fingerprint(row) != record["sourceFingerprint"]:
        raise ValueError(
            f"{row.get('Message ID')}: governed existing-context definition "
            "changed"
        )
    return record


def has_value(value) -> bool:
    if isinstance(value, etree._Element):
        if value.get(XSI_NIL, "") in {"true", "1"}:
            return False
        return bool("".join(value.itertext()).strip())
    return bool(str(value).strip())


def evaluate_existing_context_required(root, investor, row):
    record = binding_for(row)
    if record is None:
        return []

    document = etree.fromstring(ET.tostring(root, encoding="utf-8"))
    contexts = document.getroottree().xpath(
        record["contextXPath"], namespaces=NS
    )
    missing = []
    for context in contexts:
        if not isinstance(context, etree._Element):
            raise ValueError(
                f"{record['ruleId']}: context XPath must select XML elements"
            )
        values = context.xpath(
            record["requiredValueRelativeXPath"], namespaces=NS
        )
        if not values or not all(has_value(value) for value in values):
            missing.append(context)

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
            nearest_existing_ancestor=record["contextXPath"],
            observed_value="missing, empty, or nil in an existing context",
            expected_condition=row["Rule Logic"],
            source=Provenance(
                source_document="data/data-constraints.csv",
                source_version="UAD 3.6",
                source_section=row["Unique ID"],
            ),
            finding=row["Message Text"],
        )
        for _ in missing
    ]
