"""Evaluate governed required-structure bindings.

Production receives governed source rows from the configured source loader.
Executable bindings are read from data/required-structure-bindings.ttl.

A binding may define evaluationContextXPath to check required structures
independently within each applicable context. Test fixtures and expected
test results are never read by this module.
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
BINDINGS = (
    Path(__file__).resolve().parents[2]
    / "data/required-structure-bindings.ttl"
)
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
    required_fields = (
        "ruleId",
        "sourceFingerprint",
        "applicabilityXPath",
        "requiredStructureXPath",
        "expectedDataLocation",
        "element",
    )

    for node in graph.subjects(RDF.type, B.Binding):
        record = {}
        for name in required_fields:
            values = list(graph.objects(node, B[name]))
            if len(values) != 1 or not isinstance(values[0], Literal):
                raise ValueError(
                    f"{node}: expected one literal {name}"
                )
            record[name] = str(values[0])

        context_values = list(
            graph.objects(node, B.evaluationContextXPath)
        )
        if context_values:
            if (
                len(context_values) != 1
                or not isinstance(context_values[0], Literal)
                or not str(context_values[0]).strip()
            ):
                raise ValueError(
                    f"{node}: expected one nonblank literal "
                    "evaluationContextXPath"
                )
            record["evaluationContextXPath"] = str(
                context_values[0]
            )

        rule_id = record["ruleId"]
        if rule_id in bindings:
            raise ValueError(
                f"Duplicate required-structure binding: {rule_id}"
            )
        bindings[rule_id] = record

    return bindings


def binding_for(row: dict[str, str]) -> dict[str, str] | None:
    record = load_bindings().get(row.get("Message ID"))
    if (
        record is not None
        and fingerprint(row) != record["sourceFingerprint"]
    ):
        raise ValueError(
            f"{row.get('Message ID')}: "
            "governed required-structure definition changed"
        )
    return record


def _element_location(element) -> str:
    """Identify an existing MISMO element by its absolute indexed path."""
    ancestors = list(element.iterancestors())
    ancestors.reverse()
    steps = []

    for node in [*ancestors, element]:
        name = etree.QName(node)
        if name.namespace != NAMESPACE:
            raise ValueError(
                "Required-structure context locations must use "
                "the governed MISMO namespace."
            )

        position = 1 + sum(
            sibling.tag == node.tag
            for sibling in node.itersiblings(preceding=True)
        )
        steps.append(f"m:{name.localname}[{position}]")

    return "/" + "/".join(steps)


def _finding(row, record, investor, context=None):
    location = record["expectedDataLocation"]
    nearest_existing_ancestor = None

    if context is not None:
        nearest_existing_ancestor = _element_location(context)
        if not location.startswith("/"):
            location = (
                nearest_existing_ancestor
                + "/"
                + location
            )

    return Finding(
        finding_id=f"F-{uuid4().hex[:8]}",
        severity=Severity(row["Severity"].casefold()),
        investor=investor,
        rule_type=RuleType.APPENDIX_H,
        rule_id=row["Message ID"],
        row_id=row["Unique ID"],
        primary_data_element=record["element"],
        property_affected=row["Property Affected"],
        violation_kind="MissingRequiredStructure",
        data_location=location,
        nearest_existing_ancestor=nearest_existing_ancestor,
        observed_value="required container, collection, or value is absent",
        expected_condition=row["Rule Logic"],
        source=Provenance(
            source_document=row.get(
                "_source_document",
                "data/data-constraints.csv",
            ),
            source_version=row.get(
                "_source_version",
                "UAD 3.6",
            ),
            source_section=row["Unique ID"],
            source_sheet=row.get("_source_sheet"),
        ),
        finding=row["Message Text"],
    )


def evaluate_required_structure(root, investor, row):
    record = binding_for(row)
    if record is None:
        return []

    document = etree.fromstring(
        ET.tostring(root, encoding="utf-8")
    )
    tree = document.getroottree()
    applicability_xpath = record["applicabilityXPath"]
    context_xpath = record.get("evaluationContextXPath")

    if context_xpath is not None:
        if applicability_xpath:
            anchors = tree.xpath(
                applicability_xpath,
                namespaces=NS,
            )
            if not isinstance(anchors, list) or any(
                not isinstance(anchor, etree._Element)
                for anchor in anchors
            ):
                raise ValueError(
                    "A context-based binding's applicabilityXPath "
                    "must select XML elements."
                )
        else:
            anchors = [document]

        findings = []
        for anchor in anchors:
            contexts = anchor.xpath(
                context_xpath,
                namespaces=NS,
            )
            if not isinstance(contexts, list) or any(
                not isinstance(context, etree._Element)
                for context in contexts
            ):
                raise ValueError(
                    "evaluationContextXPath must select XML elements."
                )

            for context in contexts:
                matches = context.xpath(
                    record["requiredStructureXPath"],
                    namespaces=NS,
                )
                if not matches:
                    findings.append(
                        _finding(
                            row,
                            record,
                            investor,
                            context=context,
                        )
                    )

        return findings

    if applicability_xpath and not tree.xpath(
        applicability_xpath,
        namespaces=NS,
    ):
        return []

    matches = tree.xpath(
        record["requiredStructureXPath"],
        namespaces=NS,
    )
    if matches:
        return []

    return [_finding(row, record, investor)]