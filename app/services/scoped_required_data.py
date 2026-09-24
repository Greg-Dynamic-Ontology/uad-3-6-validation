"""Explicit conditional/scoped requirements for IT-1R1's first slice.

Production definitions are checked against the governed CSV.
No fixture, test manifest, or expected-result graph is read here.
"""

from dataclasses import dataclass
from uuid import uuid4
from xml.etree.ElementTree import Element

from app.models.common import Provenance
from app.models.enums import Investor, RuleType, Severity
from app.models.validation import Finding


NAMESPACE = "http://www.mismo.org/residential/2009/schemas"
NS = {"m": NAMESPACE}
PROPERTY_PATH = "../VALUATION_ANALYSIS/PROPERTIES/PROPERTY/"


@dataclass(frozen=True)
class ScopedRule:
    element: str
    logic: str
    severity: str
    parent_path: str


SCOPED_RULES = {
    ("0100.0024", "UAD1021"): ScopedRule(
        element="PropertyEstateType",
        logic=(
            'If (PropertyInProjectIndicator = "false" or '
            'ProjectLegalStructureType = "Condominium"), '
            "and PropertyEstateType is not provided"
        ),
        severity="Fatal",
        parent_path=PROPERTY_PATH + "PROPERTY_DETAIL/",
    ),
    ("0100.0028", "UAD1024"): ScopedRule(
        element="PropertyGroundLeaseAnnualAmount",
        logic=(
            'If PropertyEstateType = "Leasehold" and '
            'LandOwnedInCommonIndicator = "false", '
            "and PropertyGroundLeaseAnnualAmount is not provided"
        ),
        severity="Fatal",
        parent_path=PROPERTY_PATH + "PROPERTY_GROUND_RENT/",
    ),
    ("0300.0012", "UAD1054"): ScopedRule(
        element="PropertyStructureBuiltYearEstimatedIndicator",
        logic=(
            'If ImprovementType = "Dwelling", and '
            "PropertyStructureBuiltYearEstimatedIndicator is not provided "
            "in a given instance of IMPROVEMENT_DETAIL"
        ),
        severity="Warning",
        parent_path=(
            PROPERTY_PATH
            + "IMPROVEMENTS/IMPROVEMENT/IMPROVEMENT_DETAIL/"
        ),
    ),
}


def scoped_spec(rule: dict[str, str]) -> ScopedRule | None:
    return SCOPED_RULES.get(
        (rule.get("Unique ID"), rule.get("Message ID"))
    )


def verify_definition(rule: dict[str, str]) -> ScopedRule:
    specification = scoped_spec(rule)
    if specification is None:
        raise ValueError(
            f"Unsupported scoped rule: {rule.get('Message ID')}"
        )

    expected = {
        "Primary Data Element": specification.element,
        "Rule Logic": specification.logic,
        "Severity": specification.severity,
        "Property Affected": "Subject",
        " xPath": specification.parent_path,
    }
    for field, value in expected.items():
        if rule.get(field) != value:
            raise ValueError(
                f"{rule['Unique ID']}/{rule['Message ID']}: "
                f"unsupported governed definition for {field}"
            )
    return specification


def _has_value(node: Element) -> bool:
    nil = node.get(
        "{http://www.w3.org/2001/XMLSchema-instance}nil", ""
    )
    return nil not in {"true", "1"} and bool((node.text or "").strip())


def _equals(
    context: Element,
    path: str,
    expected: str,
    identity: str,
) -> bool | None:
    nodes = context.findall(path, NS)
    if not nodes:
        return None
    if len(nodes) != 1:
        raise ValueError(
            f"{identity}: ambiguous condition input at {path}"
        )

    node = nodes[0]
    if list(node) or not _has_value(node):
        raise ValueError(
            f"{identity}: invalid condition input at {path}"
        )
    return (node.text or "").strip() == expected


def _combine(
    values: tuple[bool | None, ...],
    operator: str,
    identity: str,
) -> bool:
    # A decisive operand determines the result even if another is absent.
    if operator == "or":
        if True in values:
            return True
        if all(value is False for value in values):
            return False
    elif operator == "and":
        if False in values:
            return False
        if all(value is True for value in values):
            return True
    else:
        raise ValueError(f"Unsupported condition operator: {operator}")

    raise ValueError(
        f"{identity}: missing input prevents condition evaluation"
    )


def _path_from(
    ancestor: Element,
    node: Element,
    parents: dict[Element, Element],
    subject_count: int | None = None,
) -> str:
    parts = []
    while node is not ancestor:
        parent = parents[node]
        siblings = [
            child for child in parent if child.tag == node.tag
        ]
        name = "m:" + node.tag.removeprefix(f"{{{NAMESPACE}}}")

        if (
            subject_count is not None
            and node.tag == f"{{{NAMESPACE}}}PROPERTY"
            and node.get("ValuationUseType") == "SubjectProperty"
        ):
            if subject_count > 1:
                name += f"[{siblings.index(node) + 1}]"
            name += "[@ValuationUseType='SubjectProperty']"
        elif len(siblings) > 1:
            name += f"[{siblings.index(node) + 1}]"

        parts.append(name)
        node = parent

    return "/".join(reversed(parts))


def evaluate_scoped_rule(
    root: Element,
    investor: Investor,
    rule: dict[str, str],
) -> list[Finding]:
    specification = verify_definition(rule)
    identity = f"{rule['Unique ID']}/{rule['Message ID']}"
    parents = {
        child: parent for parent in root.iter() for child in parent
    }
    analyses = list(
        root.iter(f"{{{NAMESPACE}}}VALUATION_ANALYSIS")
    )
    if not analyses:
        raise ValueError(
            "The XML contains no UAD VALUATION_ANALYSIS context."
        )

    findings = []

    for analysis in analyses:
        subjects = analysis.findall(
            "m:PROPERTIES/m:PROPERTY"
            "[@ValuationUseType='SubjectProperty']",
            NS,
        )
        if not subjects:
            raise ValueError(
                f"{identity}: cannot evaluate without subject context"
            )

        for subject in subjects:
            rule_id = rule["Message ID"]

            # A present dependent value cannot violate a missing-data rule.
            # Do not demand unrelated condition inputs to establish that.
            if rule_id in {"UAD1021", "UAD1024"}:
                dependent_parent = specification.parent_path.removeprefix(
                    PROPERTY_PATH
                ).strip("/")
                lookup = "/".join(
                    "m:" + part
                    for part in dependent_parent.split("/")
                )
                existing_parents = subject.findall(lookup, NS)
                if len(existing_parents) == 1:
                    supplied = existing_parents[0].findall(
                        f"m:{specification.element}", NS
                    )
                    if supplied and all(
                        _has_value(node) for node in supplied
                    ):
                        continue

            if rule_id == "UAD1021":
                applies = _combine(
                    (
                        _equals(
                            subject,
                            "m:PROPERTY_DETAIL/"
                            "m:PropertyInProjectIndicator",
                            "false",
                            identity,
                        ),
                        _equals(
                            subject,
                            "m:PROJECT/m:PROJECT_DETAIL/"
                            "m:ProjectLegalStructureType",
                            "Condominium",
                            identity,
                        ),
                    ),
                    "or",
                    identity,
                )
                parent_path = "m:PROPERTY_DETAIL"

            elif rule_id == "UAD1024":
                applies = _combine(
                    (
                        _equals(
                            subject,
                            "m:PROPERTY_DETAIL/m:PropertyEstateType",
                            "Leasehold",
                            identity,
                        ),
                        _equals(
                            subject,
                            "m:SITE/m:SITE_DETAIL/"
                            "m:LandOwnedInCommonIndicator",
                            "false",
                            identity,
                        ),
                    ),
                    "and",
                    identity,
                )
                parent_path = "m:PROPERTY_GROUND_RENT"

            else:
                applies = None
                parent_path = (
                    "m:IMPROVEMENTS/m:IMPROVEMENT/"
                    "m:IMPROVEMENT_DETAIL"
                )

            if applies is False:
                continue

            containers = subject.findall(parent_path, NS)
            if rule_id != "UAD1054" and len(containers) > 1:
                raise ValueError(
                    f"{identity}: ambiguous dependent context"
                )

            # Missing property-level containers still mean missing data.
            # UAD1054 applies within existing improvement-detail instances.
            contexts = (
                containers
                if rule_id == "UAD1054"
                else (containers or [None])
            )

            for container in contexts:
                if rule_id == "UAD1054":
                    applies = _equals(
                        container,
                        "m:ImprovementType",
                        "Dwelling",
                        identity,
                    )
                    if applies is None:
                        raise ValueError(
                            f"{identity}: missing ImprovementType"
                        )
                    if not applies:
                        continue

                elements = (
                    container.findall(
                        f"m:{specification.element}", NS
                    )
                    if container is not None
                    else []
                )
                if elements and all(
                    _has_value(node) for node in elements
                ):
                    continue

                existing = (
                    container if container is not None else subject
                )
                location = (
                    "//m:VALUATION_ANALYSIS/"
                    + _path_from(
                        analysis, existing, parents, len(subjects)
                    )
                )
                if container is None:
                    location += "/" + parent_path
                location += "/m:" + specification.element

                nearest = None
                if not elements:
                    relative = _path_from(root, existing, parents)
                    nearest = "./" + relative if relative else "."

                findings.append(
                    Finding(
                        finding_id=f"F-{uuid4().hex[:8]}",
                        severity=Severity(
                            specification.severity.casefold()
                        ),
                        investor=investor,
                        rule_type=RuleType.APPENDIX_H,
                        rule_id=rule_id,
                        row_id=rule["Unique ID"],
                        primary_data_element=specification.element,
                        property_affected=rule["Property Affected"],
                        violation_kind="MissingRequiredValue",
                        data_location=location,
                        nearest_existing_ancestor=nearest,
                        observed_value="missing, empty, or nil",
                        expected_condition=specification.logic,
                        source=Provenance(
                            source_document="data/data-constraints.csv",
                            source_version="UAD 3.6",
                            source_section=rule["Unique ID"],
                        ),
                        finding=rule["Message Text"],
                    )
                )

    return findings