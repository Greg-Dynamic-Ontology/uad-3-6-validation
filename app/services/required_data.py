"""Evaluate unconditional Fatal required-data rules from the production CSV."""

import csv
import logging
from functools import lru_cache
from pathlib import Path
from uuid import uuid4
from xml.etree.ElementTree import Element

from app.models.common import Provenance
from app.models.enums import Investor, RuleType, Severity
from app.models.validation import Finding


ROOT = Path(__file__).resolve().parents[2]
RULE_FILE = ROOT / "data" / "data-constraints.csv"
NAMESPACE = "http://www.mismo.org/residential/2009/schemas"
NS = {"m": NAMESPACE}
logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def load_required_rules() -> tuple[dict[str, str], ...]:
    with RULE_FILE.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))

    rules = tuple(
        row
        for row in rows
        if row["Severity"] == "Fatal"
        and row["Rule Logic"]
        == f"If {row['Primary Data Element']} is not provided"
    )

    if len({rule["Message ID"] for rule in rules}) != len(rules):
        raise ValueError("Required-data rule IDs must be unique.")

    valid_rules = []

    for rule in rules:
        problem = None
        field = None
        property_scope = rule.get("Property Affected")
        xml_path = rule.get(" xPath")

        if not property_scope or not property_scope.strip():
            field = "Property Affected"
            problem = "Missing property context"
        elif property_scope not in {"Subject", "N/A"}:
            field = "Property Affected"
            problem = f"Unsupported property context: {property_scope}"
        elif not xml_path or not xml_path.strip():
            field = " xPath"
            problem = "Missing XML path"
        elif not xml_path.startswith("../VALUATION_ANALYSIS/"):
            field = " xPath"
            problem = f"Unsupported XML path: {xml_path}"

        if problem is not None:
            logger.error(
                "Required-data configuration error for row %s: %s",
                rule.get("Unique ID"),
                problem,
                extra={
                    "row_id": rule.get("Unique ID"),
                    "configuration_field": field,
                },
            )
            continue

        valid_rules.append(rule)

    return tuple(valid_rules)


def rule_path(rule: dict[str, str]) -> str:
    parts = rule[" xPath"].removeprefix("../").strip("/").split("/")
    parts.append(rule["Primary Data Element"])

    return "//" + "/".join(
        "m:" + part
        + (
            "[@ValuationUseType='SubjectProperty']"
            if part == "PROPERTY"
            and rule["Property Affected"] == "Subject"
            else ""
        )
        for part in parts
    )


def has_value(element: Element) -> bool:
    nil = element.get(
        "{http://www.w3.org/2001/XMLSchema-instance}nil", ""
    )
    return nil not in {"true", "1"} and bool(
        (element.text or "").strip()
    )


def nearest_existing_ancestor_path(
    root: Element,
    analysis: Element,
    data_location: str,
    parents: dict[Element, Element],
) -> str:
    """Find the deepest existing parent along the expected data path."""
    # Resolve within this analysis, excluding the missing/value element.
    steps = data_location.removeprefix("//").split("/")[1:-1]
    ancestor = analysis

    while steps:
        matches = analysis.findall("/".join(steps), NS)
        if matches:
            if len(matches) != 1:
                raise ValueError(
                    f"Ambiguous ancestor context for {data_location}"
                )
            ancestor = matches[0]
            break
        steps.pop()

    # Build a root-relative path to the actual node. Sibling positions
    # keep the ancestor identifiable even when surrounding nodes repeat.
    path_parts = []
    node = ancestor

    while node is not root:
        parent = parents[node]
        siblings = [
            child for child in parent if child.tag == node.tag
        ]
        name = node.tag
        namespace_prefix = f"{{{NAMESPACE}}}"

        if name.startswith(namespace_prefix):
            name = "m:" + name[len(namespace_prefix):]

        if len(siblings) > 1:
            name += f"[{siblings.index(node) + 1}]"

        path_parts.append(name)
        node = parent

    return "./" + "/".join(reversed(path_parts)) if path_parts else "."


def evaluate_required_data(
    root: Element,
    investor: Investor,
) -> list[Finding]:
    """Evaluate each rule separately for each valuation/property context."""
    findings: list[Finding] = []

    analyses = list(root.iter(f"{{{NAMESPACE}}}VALUATION_ANALYSIS"))
    if not analyses:
        raise ValueError(
            "The XML contains no UAD VALUATION_ANALYSIS context."
        )

    parents = {
        child: parent
        for parent in root.iter()
        for child in parent
    }

    for rule in load_required_rules():
        parts = rule[" xPath"].removeprefix("../").strip("/").split("/")
        element_name = rule["Primary Data Element"]

        for analysis in analyses:
            if rule["Property Affected"] == "Subject":
                if parts[1:3] != ["PROPERTIES", "PROPERTY"]:
                    raise ValueError(
                        f"Unsupported subject path: {rule['Message ID']}"
                    )

                contexts = analysis.findall(
                    "m:PROPERTIES/m:PROPERTY"
                    "[@ValuationUseType='SubjectProperty']",
                    NS,
                )
                remaining = parts[3:]
            else:
                contexts = [analysis]
                remaining = parts[1:]

            relative_path = "/".join(
                "m:" + part for part in remaining + [element_name]
            )

            # A missing subject container also means its required data
            # was not supplied.
            for context in contexts or [None]:
                elements = (
                    context.findall(relative_path, NS)
                    if context is not None
                    else []
                )

                if elements and all(has_value(node) for node in elements):
                    continue

                data_location = rule_path(rule)

                if (
                    rule["Property Affected"] == "Subject"
                    and context is not None
                    and len(contexts) > 1
                ):
                    # XPath positions count all PROPERTY siblings,
                    # including properties outside the subject scope.
                    siblings = [
                        child
                        for child in parents[context]
                        if child.tag == context.tag
                    ]
                    position = siblings.index(context) + 1
                    data_location = data_location.replace(
                        "m:PROPERTY[@ValuationUseType='SubjectProperty']",
                        f"m:PROPERTY[{position}]"
                        "[@ValuationUseType='SubjectProperty']",
                        1,
                    )

                ancestor_path = None
                if not elements:
                    ancestor_path = nearest_existing_ancestor_path(
                        root, analysis, data_location, parents
                    )

                findings.append(
                    Finding(
                        finding_id=f"F-{uuid4().hex[:8]}",
                        severity=Severity.FATAL,
                        investor=investor,
                        rule_type=RuleType.APPENDIX_H,
                        rule_id=rule["Message ID"],
                        row_id=rule["Unique ID"],
                        data_location=data_location,
                        nearest_existing_ancestor=ancestor_path,
                        observed_value="missing, empty, or nil",
                        expected_condition=(
                            f"{element_name} must be provided."
                        ),
                        source=Provenance(
                            source_document="data/data-constraints.csv",
                            source_version="UAD 3.6",
                            source_section=rule["Unique ID"],
                        ),
                        finding=rule["Message Text"],
                    )
                )

    return findings