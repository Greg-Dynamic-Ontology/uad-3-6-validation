"""Evaluate supported required-data rules from the production CSV.

Supports Fatal unconditional requirements, explicitly mapped
single-equality requirements, and selected conditional/scoped rules
with their governed severity.

RDF test definitions are never read by this module.
"""

import csv
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from uuid import uuid4
from xml.etree.ElementTree import Element

from app.models.common import Provenance
from app.models.enums import Investor, RuleType, Severity
from app.models.validation import Finding
from app.services.scoped_required_data import (
    evaluate_scoped_rule,
    scoped_spec,
    verify_definition,
)


ROOT = Path(__file__).resolve().parents[2]
RULE_FILE = ROOT / "data" / "data-constraints.csv"
NAMESPACE = "http://www.mismo.org/residential/2009/schemas"
NS = {"m": NAMESPACE}
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConditionalRule:
    element: str
    trigger: str
    value: str
    parent_path: str

    @property
    def logic(self) -> str:
        return (
            f'If {self.trigger} = "{self.value}" and '
            f"{self.element} is not provided"
        )


PROPERTY_DETAIL_PATH = (
    "../VALUATION_ANALYSIS/PROPERTIES/PROPERTY/PROPERTY_DETAIL/"
)
SALES_CONTRACT_DETAIL_PATH = (
    "../VALUATION_ANALYSIS/PROPERTIES/PROPERTY/"
    "SALES_CONTRACTS/SALES_CONTRACT/SALES_CONTRACT_DETAIL/"
)

# Each trigger and dependent element share the declared parent context.
# Keys preserve both source row identity and source rule identity.
CONDITIONAL_RULES = {
    ("0100.0053", "UAD1022"): ConditionalRule(
        element="PropertyEstateTypeOtherDescription",
        trigger="PropertyEstateType",
        value="Other",
        parent_path=PROPERTY_DETAIL_PATH,
    ),
    ("0600.0006", "UAD1128"): ConditionalRule(
        element="SalesConcessionIndicator",
        trigger="SalesContractReviewedIndicator",
        value="true",
        parent_path=SALES_CONTRACT_DETAIL_PATH,
    ),
    ("0600.0008", "UAD1129"): ConditionalRule(
        element="SalesContractAmount",
        trigger="SalesContractReviewedIndicator",
        value="true",
        parent_path=SALES_CONTRACT_DETAIL_PATH,
    ),
    ("0600.0009", "UAD1130"): ConditionalRule(
        element="SalesContractDate",
        trigger="SalesContractReviewedIndicator",
        value="true",
        parent_path=SALES_CONTRACT_DETAIL_PATH,
    ),
    ("0600.0017", "UAD1135"): ConditionalRule(
        element="SaleType",
        trigger="SalesContractReviewedIndicator",
        value="true",
        parent_path=SALES_CONTRACT_DETAIL_PATH,
    ),
}


def conditional_spec(
    rule: dict[str, str],
) -> ConditionalRule | None:
    return CONDITIONAL_RULES.get(
        (rule.get("Unique ID"), rule.get("Message ID"))
    )


def is_conditional_rule(rule: dict[str, str]) -> bool:
    return (
        conditional_spec(rule) is not None
        or scoped_spec(rule) is not None
    )


@lru_cache(maxsize=1)
def load_required_rules() -> tuple[dict[str, str], ...]:
    with RULE_FILE.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))

    rules = []
    for row in rows:
        if scoped_spec(row) is not None:
            verify_definition(row)
            rules.append(row)
            continue

        specification = conditional_spec(row)

        if specification is not None:
            expected = {
                "Primary Data Element": specification.element,
                "Rule Logic": specification.logic,
                "Severity": "Fatal",
                "Property Affected": "Subject",
                " xPath": specification.parent_path,
            }
            for field, value in expected.items():
                if row.get(field) != value:
                    raise ValueError(
                        f"{row['Unique ID']}/{row['Message ID']}: "
                        f"unsupported governed definition for {field}"
                    )
            rules.append(row)

        elif (
            row["Severity"] == "Fatal"
            and row["Rule Logic"]
            == f"If {row['Primary Data Element']} is not provided"
        ):
            rules.append(row)

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


def conditional_elements(
    context: Element | None,
    remaining: list[str],
    rule: dict[str, str],
) -> list[Element] | None:
    """Return dependent elements when true; None when false.

    Missing or ambiguous condition inputs raise an evaluation error.
    They are not silently interpreted as false.
    """
    identity = f"{rule['Unique ID']}/{rule['Message ID']}"
    specification = conditional_spec(rule)
    if specification is None:
        raise ValueError(f"{identity}: unsupported conditional rule")

    if context is None:
        raise ValueError(
            f"{identity}: cannot evaluate condition without subject context"
        )

    parent_path = "/".join("m:" + part for part in remaining)
    containers = (
        context.findall(parent_path, NS)
        if parent_path
        else [context]
    )
    if len(containers) != 1:
        raise ValueError(
            f"{identity}: expected one condition context, "
            f"found {len(containers)}"
        )

    container = containers[0]
    triggers = container.findall(
        f"{{{NAMESPACE}}}{specification.trigger}"
    )
    if len(triggers) != 1:
        raise ValueError(
            f"{identity}: expected one {specification.trigger}, "
            f"found {len(triggers)}"
        )

    trigger = triggers[0]
    if list(trigger) or not has_value(trigger):
        raise ValueError(
            f"{identity}: {specification.trigger} must have "
            "one nonblank, non-nil scalar value"
        )

    if (trigger.text or "").strip() != specification.value:
        return None

    return container.findall(
        f"{{{NAMESPACE}}}{rule['Primary Data Element']}"
    )


def nearest_existing_ancestor_path(
    root: Element,
    analysis: Element,
    data_location: str,
    parents: dict[Element, Element],
) -> str:
    """Find the deepest existing parent along the expected data path."""
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

    return (
        "./" + "/".join(reversed(path_parts))
        if path_parts
        else "."
    )


def evaluate_required_data(
    root: Element,
    investor: Investor,
) -> list[Finding]:
    """Evaluate rules within each valuation and subject-property context."""
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

    for rule in sorted(
        load_required_rules(), key=lambda row: row["Unique ID"]
    ):
        if scoped_spec(rule) is not None:
            findings.extend(
                evaluate_scoped_rule(root, investor, rule)
            )
            continue

        parts = (
            rule[" xPath"].removeprefix("../").strip("/").split("/")
        )
        element_name = rule["Primary Data Element"]
        specification = conditional_spec(rule)

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

            for context in contexts or [None]:
                if specification is not None:
                    elements = conditional_elements(
                        context, remaining, rule
                    )
                    if elements is None:
                        continue
                else:
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
                    # Count all PROPERTY siblings, including comparables.
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

                expected_condition = (
                    f"{element_name} must be provided."
                )
                if specification is not None:
                    expected_condition = (
                        f'{element_name} must be provided when '
                        f'{specification.trigger} = "{specification.value}" '
                        "in the same subject-property XML context."
                    )

                findings.append(
                    Finding(
                        finding_id=f"F-{uuid4().hex[:8]}",
                        severity=Severity.FATAL,
                        investor=investor,
                        rule_type=RuleType.APPENDIX_H,
                        rule_id=rule["Message ID"],
                        row_id=rule["Unique ID"],
                        primary_data_element=element_name,
                        property_affected=rule["Property Affected"],
                        violation_kind="MissingRequiredValue",
                        data_location=data_location,
                        nearest_existing_ancestor=ancestor_path,
                        observed_value="missing, empty, or nil",
                        expected_condition=expected_condition,
                        source=Provenance(
                            source_document="data/data-constraints.csv",
                            source_version="UAD 3.6",
                            source_section=rule["Unique ID"],
                        ),
                        finding=rule["Message Text"],
                    )
                )

    return findings