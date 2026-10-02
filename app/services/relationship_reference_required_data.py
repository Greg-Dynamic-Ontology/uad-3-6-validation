"""Evaluate governed relationship and reference-integrity bindings."""

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


B = Namespace("urn:uad36:relationship-reference-binding:")
BINDINGS = (
    Path(__file__).resolve().parents[2]
    / "data/relationship-reference-bindings.ttl"
)
NS = {
    "m": "http://www.mismo.org/residential/2009/schemas",
    "xlink": "http://www.w3.org/1999/xlink",
}
X = "{http://www.w3.org/1999/xlink}"
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


def fingerprint(row):
    return hashlib.sha256(
        json.dumps(
            [row.get(key) for key in SOURCE_COLUMNS],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


@lru_cache(maxsize=1)
def load_bindings():
    graph = Graph().parse(BINDINGS, format="turtle")
    fields = (
        "applicabilityXPath",
        "arcrole",
        "element",
        "evaluationMode",
        "expectedDataLocation",
        "otherEndpointElement",
        "ruleId",
        "sourceFingerprint",
        "targetAxis",
        "targetXPath",
        "violationKind",
    )
    bindings = {}
    for node in graph.subjects(RDF.type, B.Binding):
        record = {}
        for name in fields:
            values = list(graph.objects(node, B[name]))
            if len(values) != 1 or not isinstance(values[0], Literal):
                raise ValueError(f"{node}: expected one literal {name}")
            record[name] = str(values[0])
        rule_id = record["ruleId"]
        if rule_id in bindings:
            raise ValueError(f"Duplicate relationship binding: {rule_id}")
        bindings[rule_id] = record
    return bindings


def binding_for(row):
    record = load_bindings().get(row.get("Message ID"))
    if record is not None and fingerprint(row) != record["sourceFingerprint"]:
        raise ValueError(
            f"{row.get('Message ID')}: governed relationship definition changed"
        )
    return record


def relationship_key(node):
    return (
        node.get(X + "arcrole", ""),
        node.get(X + "from", ""),
        node.get(X + "to", ""),
    )


def label_index(document):
    result = {}
    for node in document.iter():
        label = node.get(X + "label")
        if label:
            result.setdefault(label, []).append(node)
    return result


def endpoint_has_element(index, label, expected):
    if label not in index:
        return False
    return not expected or any(
        etree.QName(node).localname == expected for node in index[label]
    )


def violations(document, record):
    relationships = [
        node
        for node in document.iter()
        if etree.QName(node).localname == "RELATIONSHIP"
    ]
    index = label_index(document)
    mode = record["evaluationMode"]

    if mode == "unique-relationship-key":
        counts = Counter(relationship_key(node) for node in relationships)
        return [key for key, count in counts.items() if count > 1]
    if mode == "from-endpoint-resolves":
        return [
            node for node in relationships
            if node.get(X + "from", "") not in index
        ]
    if mode == "to-endpoint-resolves":
        return [
            node for node in relationships
            if node.get(X + "to", "") not in index
        ]
    if mode != "required-link-per-target":
        raise ValueError(f"Unsupported relationship mode: {mode}")

    if record["applicabilityXPath"] and not document.getroottree().xpath(
        record["applicabilityXPath"], namespaces=NS
    ):
        return []
    targets = document.getroottree().xpath(
        record["targetXPath"], namespaces=NS
    )
    axis = record["targetAxis"]
    endpoint = X + axis
    other = X + ("from" if axis == "to" else "to")
    missing = []
    for target in targets:
        label = target.get(X + "label", "")
        matches = [
            relation for relation in relationships
            if relation.get(X + "arcrole") == record["arcrole"]
            and relation.get(endpoint) == label
            and endpoint_has_element(
                index,
                relation.get(other, ""),
                record["otherEndpointElement"],
            )
        ]
        if not label or not matches:
            missing.append(target)
    return missing


def evaluate_relationship_reference(root, investor, row):
    record = binding_for(row)
    if record is None:
        return []
    document = etree.fromstring(ET.tostring(root, encoding="utf-8"))
    invalid = violations(document, record)
    if not invalid:
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
            observed_value="relationship or reference integrity violation",
            expected_condition=row["Rule Logic"],
            source=Provenance(
                source_document="data/data-constraints.csv",
                source_version="UAD 3.6",
                source_section=row["Unique ID"],
            ),
            finding=row["Message Text"],
        )
    ]
