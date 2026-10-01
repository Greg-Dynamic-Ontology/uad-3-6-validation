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
from app.services.single_equality_required_data import binding_for, evaluate_single_equality
from app.services.required_structure_required_data import (
    binding_for as required_structure_binding_for,
    evaluate_required_structure,
)
from app.services.uniqueness_cardinality_required_data import (
    binding_for as uniqueness_cardinality_binding_for,
    evaluate_uniqueness_cardinality,
)
from app.services.numeric_bound_required_data import (
    binding_for as numeric_bound_binding_for,
    evaluate_numeric_bound,
)
from app.services.representation_restriction_required_data import (
    binding_for as representation_restriction_binding_for,
    evaluate_representation_restriction,
)
from app.services.existing_context_required_data import (
    binding_for as existing_context_binding_for,
    evaluate_existing_context_required,
)
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
    # Optional trigger path relative to the same subject property.
    trigger_subject_path: str | None = None
    severity: str = "Fatal"
    property_affected: str = "Subject"
    # Optional trigger path relative to the same valuation report.
    trigger_report_path: str | None = None

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

PROJECT_DETAIL_PATH = (
    "../VALUATION_ANALYSIS/PROPERTIES/PROPERTY/PROJECT/PROJECT_DETAIL/"
)

# Triggers default to the dependent container. Explicit cross-container
# bindings remain relative to the same subject property or valuation report.
# Keys preserve both source row identity and source rule identity.
CONDITIONAL_RULES = {
    ("1200.0003", "UAD1242"): ConditionalRule(
        element="GrossRentMultiplierFactorNumber",
        trigger="IncomeApproachIndicator",
        value="true",
        parent_path=(
            "../VALUATION_ANALYSIS/VALUATION_REPORT/APPROACH_TO_VALUE/"
            "INCOME_APPROACH/INCOME_APPROACH_DETAIL/"
        ),
        trigger_report_path="m:SCOPE_OF_WORK/m:SCOPE_OF_WORK_DETAIL/m:IncomeApproachIndicator",
        property_affected="N/A",
        severity="Fatal",
    ),
    ("1200.0004", "UAD1243"): ConditionalRule(
        element="ValueIndicatedByIncomeApproachAmount",
        trigger="IncomeApproachIndicator",
        value="true",
        parent_path=(
            "../VALUATION_ANALYSIS/VALUATION_REPORT/APPROACH_TO_VALUE/"
            "INCOME_APPROACH/INCOME_APPROACH_DETAIL/"
        ),
        trigger_report_path="m:SCOPE_OF_WORK/m:SCOPE_OF_WORK_DETAIL/m:IncomeApproachIndicator",
        property_affected="N/A",
        severity="Fatal",
    ),
    ("1200.0007", "UAD1762"): ConditionalRule(
        element="IncomeAnalysisCommentDescription",
        trigger="IncomeApproachIndicator",
        value="true",
        parent_path=(
            "../VALUATION_ANALYSIS/VALUATION_REPORT/APPROACH_TO_VALUE/"
            "INCOME_APPROACH/INCOME_APPROACH_DETAIL/"
        ),
        trigger_report_path="m:SCOPE_OF_WORK/m:SCOPE_OF_WORK_DETAIL/m:IncomeApproachIndicator",
        property_affected="N/A",
        severity="Fatal",
    ),
    ("1100.0026", "UAD1227"): ConditionalRule(
        element="DepreciatedCostDwellingsTotalAmount",
        trigger="CostApproachIndicator",
        value="true",
        parent_path=(
            "../VALUATION_ANALYSIS/VALUATION_REPORT/APPROACH_TO_VALUE/"
            "COST_APPROACH/COST_APPROACH_DETAIL/"
        ),
        trigger_report_path="m:SCOPE_OF_WORK/m:SCOPE_OF_WORK_DETAIL/m:CostApproachIndicator",
        property_affected="N/A",
        severity="Warning",
    ),
    ("1100.0032", "UAD1230"): ConditionalRule(
        element="SiteOtherImprovementsAsIsAmount",
        trigger="CostApproachIndicator",
        value="true",
        parent_path=(
            "../VALUATION_ANALYSIS/VALUATION_REPORT/APPROACH_TO_VALUE/"
            "COST_APPROACH/COST_APPROACH_DETAIL/"
        ),
        trigger_report_path="m:SCOPE_OF_WORK/m:SCOPE_OF_WORK_DETAIL/m:CostApproachIndicator",
        property_affected="N/A",
        severity="Fatal",
    ),
    ("1300.0001", "UAD1252"): ConditionalRule(
        element="ValueIndicatedByCostApproachAmount",
        trigger="CostApproachIndicator",
        value="true",
        parent_path=(
            "../VALUATION_ANALYSIS/VALUATION_REPORT/APPROACH_TO_VALUE/"
            "COST_APPROACH/COST_APPROACH_DETAIL/"
        ),
        trigger_report_path="m:SCOPE_OF_WORK/m:SCOPE_OF_WORK_DETAIL/m:CostApproachIndicator",
        property_affected="N/A",
        severity="Fatal",
    ),
    ("1100.0023", "UAD1761"): ConditionalRule(
        element="CostAnalysisCommentDescription",
        trigger="CostApproachIndicator",
        value="true",
        parent_path=(
            "../VALUATION_ANALYSIS/VALUATION_REPORT/APPROACH_TO_VALUE/"
            "COST_APPROACH/COST_APPROACH_DETAIL/"
        ),
        trigger_report_path="m:SCOPE_OF_WORK/m:SCOPE_OF_WORK_DETAIL/m:CostApproachIndicator",
        property_affected="N/A",
        severity="Fatal",
    ),
    ("2500.0031", "UAD1583"): ConditionalRule(
        element="ProjectAnalysisGroundRentIndicator",
        trigger="PropertyInProjectIndicator",
        value="true",
        parent_path=(
            "../VALUATION_ANALYSIS/PROPERTIES/PROPERTY/PROJECT/"
            "PROJECT_ANALYSIS/"
        ),
        trigger_subject_path="m:PROPERTY_DETAIL/m:PropertyInProjectIndicator",
        severity="Fatal",
    ),
    ("2500.0032", "UAD1584"): ConditionalRule(
        element="ProjectConditionAndQualityDescription",
        trigger="ProjectDeficiencyObservedIndicator",
        value="true",
        parent_path=(
            "../VALUATION_ANALYSIS/PROPERTIES/PROPERTY/PROJECT/"
            "PROJECT_ANALYSIS/"
        ),
        trigger_subject_path="m:PROJECT/m:PROJECT_ANALYSIS/m:ProjectDeficiencyObservedIndicator",
        severity="Warning",
    ),
    ("2500.0033", "UAD1585"): ConditionalRule(
        element="ProjectDeficiencyObservedIndicator",
        trigger="PropertyInProjectIndicator",
        value="true",
        parent_path=(
            "../VALUATION_ANALYSIS/PROPERTIES/PROPERTY/PROJECT/"
            "PROJECT_ANALYSIS/"
        ),
        trigger_subject_path="m:PROPERTY_DETAIL/m:PropertyInProjectIndicator",
        severity="Fatal",
    ),
    ("2500.0048", "UAD1590"): ConditionalRule(
        element="ProjectConversionIndicator",
        trigger="PropertyInProjectIndicator",
        value="true",
        parent_path=(
            "../VALUATION_ANALYSIS/PROPERTIES/PROPERTY/PROJECT/"
            "PROJECT_CONVERSION/"
        ),
        trigger_subject_path="m:PROPERTY_DETAIL/m:PropertyInProjectIndicator",
        severity="Fatal",
    ),
    ("2500.0055", "UAD1594"): ConditionalRule(
        element="ProjectCommercialSpaceIndicator",
        trigger="PropertyInProjectIndicator",
        value="true",
        parent_path=PROJECT_DETAIL_PATH,
        trigger_subject_path="m:PROPERTY_DETAIL/m:PropertyInProjectIndicator",
    ),
    ("2500.0058", "UAD1596"): ConditionalRule(
        element="ProjectCompletedIndicator",
        trigger="PropertyInProjectIndicator",
        value="true",
        parent_path=PROJECT_DETAIL_PATH,
        trigger_subject_path="m:PROPERTY_DETAIL/m:PropertyInProjectIndicator",
    ),
    ("2500.0060", "UAD1597"): ConditionalRule(
        element="ProjectDwellingUnitCount",
        trigger="PropertyInProjectIndicator",
        value="true",
        parent_path=PROJECT_DETAIL_PATH,
        trigger_subject_path="m:PROPERTY_DETAIL/m:PropertyInProjectIndicator",
    ),
    ("2500.0061", "UAD1598"): ConditionalRule(
        element="ProjectDwellingUnitsForSaleCount",
        trigger="PropertyInProjectIndicator",
        value="true",
        parent_path=PROJECT_DETAIL_PATH,
        trigger_subject_path="m:PROPERTY_DETAIL/m:PropertyInProjectIndicator",
    ),
    ("2500.0062", "UAD1599"): ConditionalRule(
        element="ProjectDwellingUnitsRentedCount",
        trigger="PropertyInProjectIndicator",
        value="true",
        parent_path=PROJECT_DETAIL_PATH,
        trigger_subject_path="m:PROPERTY_DETAIL/m:PropertyInProjectIndicator",
    ),
    ("2500.0064", "UAD1600"): ConditionalRule(
        element="ProjectDwellingUnitsSoldCount",
        trigger="PropertyInProjectIndicator",
        value="true",
        parent_path=PROJECT_DETAIL_PATH,
        trigger_subject_path="m:PROPERTY_DETAIL/m:PropertyInProjectIndicator",
    ),
    ("2500.0168", "UAD1615"): ConditionalRule(
        element="ProjectLegalStructureType",
        trigger="PropertyInProjectIndicator",
        value="true",
        parent_path=PROJECT_DETAIL_PATH,
        trigger_subject_path="m:PROPERTY_DETAIL/m:PropertyInProjectIndicator",
    ),
    ("0100.0034", "UAD1028"): ConditionalRule(
        element="AllPropertyRightsAppraisedIndicator",
        trigger="LandOwnedInCommonIndicator",
        value="false",
        parent_path=SALES_CONTRACT_DETAIL_PATH,
        trigger_subject_path="m:SITE/m:SITE_DETAIL/m:LandOwnedInCommonIndicator",
    ),
    ("0600.0018", "UAD1136"): ConditionalRule(
        element="SaleTypeOtherDescription",
        trigger="SaleType",
        value="Other",
        parent_path=SALES_CONTRACT_DETAIL_PATH,
    ),
    ("0200.0053", "UAD1046"): ConditionalRule(
        element="SubjectPropertyAmenitiesDefectsExistIndicator",
        trigger="PropertyAmenityExistsIndicator",
        value="true",
        parent_path=PROPERTY_DETAIL_PATH,
    ),
    ("0600.0005", "UAD1127"): ConditionalRule(
        element="SalesConcessionAmountKnownIndicator",
        trigger="SalesConcessionIndicator",
        value="true",
        parent_path=SALES_CONTRACT_DETAIL_PATH,
    ),
    ("0600.0010", "UAD1132"): ConditionalRule(
        element="SalesContractReviewedIndicator",
        trigger="SalesContractExistsIndicator",
        value="true",
        parent_path=SALES_CONTRACT_DETAIL_PATH,
    ),
    ("0600.0011", "UAD1133"): ConditionalRule(
        element="TotalSalesConcessionAmount",
        trigger="SalesConcessionAmountKnownIndicator",
        value="true",
        parent_path=SALES_CONTRACT_DETAIL_PATH,
    ),
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
        if binding_for(row) is not None:
            rules.append(row)
            continue
        if required_structure_binding_for(row) is not None:
            rules.append(row)
            continue
        if uniqueness_cardinality_binding_for(row) is not None:
            rules.append(row)
            continue
        if numeric_bound_binding_for(row) is not None:
            rules.append(row)
            continue
        if representation_restriction_binding_for(row) is not None:
            rules.append(row)
            continue
        if existing_context_binding_for(row) is not None:
            rules.append(row)
            continue
        if scoped_spec(row) is not None:
            verify_definition(row)
            rules.append(row)
            continue

        specification = conditional_spec(row)

        if specification is not None:
            expected = {
                "Primary Data Element": specification.element,
                "Rule Logic": specification.logic,
                "Severity": specification.severity,
                "Property Affected": specification.property_affected,
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
            row["Severity"] in {"Fatal", "Warning"}
            and row["Rule Logic"]
            == f"If {row['Primary Data Element']} is not provided"
        ):
            rules.append(row)

    if len({rule["Message ID"] for rule in rules}) != len(rules):
        raise ValueError("Required-data rule IDs must be unique.")

    valid_rules = []

    for rule in rules:
        if binding_for(rule) is not None:
            valid_rules.append(rule)
            continue
        if required_structure_binding_for(rule) is not None:
            valid_rules.append(rule)
            continue
        if uniqueness_cardinality_binding_for(rule) is not None:
            valid_rules.append(rule)
            continue
        if numeric_bound_binding_for(rule) is not None:
            valid_rules.append(rule)
            continue
        if representation_restriction_binding_for(rule) is not None:
            valid_rules.append(rule)
            continue
        if existing_context_binding_for(rule) is not None:
            valid_rules.append(rule)
            continue
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
        elif not (
            xml_path.startswith("../VALUATION_ANALYSIS/")
            or xml_path == "MESSAGE/"
        ):
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
        (part if part.startswith("@") else "m:" + part)
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

    An absent, blank, or nil trigger cannot satisfy a scalar equality.
    Requirements governing the trigger itself are evaluated independently.
    Ambiguous or structured condition inputs still raise an evaluation error.
    """
    identity = f"{rule['Unique ID']}/{rule['Message ID']}"
    specification = conditional_spec(rule)
    if specification is None:
        raise ValueError(f"{identity}: unsupported conditional rule")

    if context is None:
        raise ValueError(
            f"{identity}: cannot evaluate condition without its governed context"
        )

    trigger_path = (
        specification.trigger_report_path
        if specification.property_affected == "N/A"
        else specification.trigger_subject_path
    )
    parent_path = "/".join("m:" + part for part in remaining)
    containers = (
        context.findall(parent_path, NS)
        if parent_path
        else [context]
    )
    # A cross-container trigger can be evaluated even when the dependent
    # container is absent. A false condition requires no container; a true
    # condition still requires the missing dependent value.
    if len(containers) > 1 or (
        not containers and trigger_path is None
    ):
        raise ValueError(
            f"{identity}: expected one condition context, "
            f"found {len(containers)}"
        )

    container = containers[0] if containers else None
    dependents = (
        container.findall(f"{{{NAMESPACE}}}{specification.element}")
        if container is not None else []
    )
    # Supplied dependent data satisfies this presence requirement regardless
    # of the trigger. Missing/invalid triggers belong to their own rules.
    # Otherwise evaluate the equality without assuming a missing trigger value.
    if (
        len(dependents) == 1
        and not list(dependents[0])
        and has_value(dependents[0])
    ):
        return dependents
    if trigger_path is not None:
        # Never search globally: another property's or report's trigger
        # cannot establish applicability for this context.
        triggers = context.findall(trigger_path, NS)
    else:
        triggers = container.findall(
            f"{{{NAMESPACE}}}{specification.trigger}"
        )
    if not triggers:
        return None
    if len(triggers) != 1:
        raise ValueError(
            f"{identity}: expected one {specification.trigger}, "
            f"found {len(triggers)}"
        )

    trigger = triggers[0]
    if list(trigger):
        raise ValueError(
            f"{identity}: {specification.trigger} must have a scalar value"
        )
    if not has_value(trigger):
        return None

    if (trigger.text or "").strip() != specification.value:
        return None

    return dependents


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
        if binding_for(rule) is not None:
            findings.extend(evaluate_single_equality(root, investor, rule))
            continue
        if required_structure_binding_for(rule) is not None:
            findings.extend(
                evaluate_required_structure(root, investor, rule)
            )
            continue
        if uniqueness_cardinality_binding_for(rule) is not None:
            findings.extend(
                evaluate_uniqueness_cardinality(root, investor, rule)
            )
            continue
        if numeric_bound_binding_for(rule) is not None:
            findings.extend(evaluate_numeric_bound(root, investor, rule))
            continue
        if representation_restriction_binding_for(rule) is not None:
            findings.extend(
                evaluate_representation_restriction(root, investor, rule)
            )
            continue
        if existing_context_binding_for(rule) is not None:
            findings.extend(
                evaluate_existing_context_required(root, investor, rule)
            )
            continue
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

        if parts == ["MESSAGE"] and element_name.startswith("@"):
            attribute_name = element_name.removeprefix("@")
            if root.tag != f"{{{NAMESPACE}}}MESSAGE":
                raise ValueError(
                    f"Unsupported root path: {rule['Message ID']}"
                )
            if (root.get(attribute_name) or "").strip():
                continue

            findings.append(
                Finding(
                    finding_id=f"F-{uuid4().hex[:8]}",
                    severity=Severity(rule["Severity"].casefold()),
                    investor=investor,
                    rule_type=RuleType.APPENDIX_H,
                    rule_id=rule["Message ID"],
                    row_id=rule["Unique ID"],
                    primary_data_element=element_name,
                    property_affected=rule["Property Affected"],
                    violation_kind="MissingRequiredValue",
                    data_location=rule_path(rule),
                    nearest_existing_ancestor=".",
                    observed_value="missing, empty, or nil",
                    expected_condition=f"{element_name} must be provided.",
                    source=Provenance(
                        source_document="data/data-constraints.csv",
                        source_version="UAD 3.6",
                        source_section=rule["Unique ID"],
                    ),
                    finding=rule["Message Text"],
                )
            )
            continue

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
            elif specification is not None and specification.property_affected == "N/A":
                if parts[1] != "VALUATION_REPORT":
                    raise ValueError(
                        f"Unsupported report path: {rule['Message ID']}"
                    )
                contexts = analysis.findall("m:VALUATION_REPORT", NS)
                remaining = parts[2:]
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
                        + (
                            "within the same valuation report."
                            if specification.property_affected == "N/A"
                            else "within the same subject property."
                        )
                    )

                findings.append(
                    Finding(
                        finding_id=f"F-{uuid4().hex[:8]}",
                        severity=Severity(rule["Severity"].casefold()),
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
