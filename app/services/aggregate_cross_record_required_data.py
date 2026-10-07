"""Evaluate eight CSV-governed aggregate and cross-record requirements.

Counts and sums remain within their owning property or improvement.
Additional comparison rows are compared within each valuation analysis.
RDF test manifests and fixture paths are never runtime inputs.
"""

import hashlib
import json
from decimal import Decimal
from uuid import uuid4
from xml.etree import ElementTree as ET

from lxml import etree

from app.models.common import Provenance
from app.models.enums import RuleType, Severity
from app.models.validation import Finding
from app.services.value_consistency_required_data import (
    child_text,
    decimal,
    location,
    text,
)


NS = {"m": "http://www.mismo.org/residential/2009/schemas"}
SOURCE_COLUMNS = (
    "Message ID", "Unique ID", "Primary Data Element", "Rule Logic",
    "Severity", "Property Affected", " xPath", "Message Text",
)
FINGERPRINTS = {
    "UAD1011": "4cb2ac514aa085795b35779981b8abe1cdcfbc3149a91606cfe61b1d8ce47f7e",
    "UAD1016": "3c0422d0a5985ae6c1e657e4119a3d03481650bd1fbe2849d95e14bee030bea3",
    "UAD1019": "c94fce7ed56cf537fdd299944f6d663aaddde43bb7c7b759d5355515d79f2146",
    "UAD1086": "a29eba5b13db2f9d673620f1be2b0339842e56e1c084a63c7f0b12c6ce364833",
    "UAD1250": "7f66ebfb5348c5aad26a8f13652d5fd10371ff29a328ba56d824bdd2fad363d1",
    "UAD1455": "8565dcf4bf2e9d178e6135c9eb8c4b3e66dc69b46872fa6c9f0279c0cdbfe1d8",
    "UAD1461": "514b0f1e30d0e97eefcaa24e9957e0f4192f0e50ae06c75e0999284393467956",
    "UAD1693": "110ec70fb17dec3c40d0a43ef1b341aec31d71c084163525f990b3a742e667f8",
}
SALES_TYPES = {
    "SalesComparableAdditionalAdjustableComparisonItem",
    "SalesComparableAdditionalNonAdjustableComparisonItem",
}
GRM_TYPE = "GrossRentMultiplierAdditionalNonAdjustableComparisonItem"
ADJUSTMENTS = "m:COMPARABLE/m:COMPARABLE_ADJUSTMENTS/m:COMPARABLE_ADJUSTMENT"
IMPROVEMENTS = "m:IMPROVEMENTS/m:IMPROVEMENT"
UNIT_DETAILS = IMPROVEMENTS + "/m:PROPERTY_UNITS/m:PROPERTY_UNIT/m:PROPERTY_UNIT_DETAIL"
STRUCTURE_COUNTS = IMPROVEMENTS + "/m:STRUCTURE/m:STRUCTURE_DETAIL/m:LivingUnitCount"


def binding_for(row):
    rule_id = row.get("Message ID")
    expected = FINGERPRINTS.get(rule_id)
    if expected is None:
        return None
    actual = hashlib.sha256(json.dumps(
        [row.get(column) for column in SOURCE_COLUMNS],
        ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    if actual != expected:
        raise ValueError(f"{rule_id}: governed aggregate definition changed")
    return rule_id


def count(node):
    """Read a supplied nonnegative integer without inventing missing data."""
    value = decimal(text(node))
    if value is None or value < 0 or value != value.to_integral_value():
        return None
    return int(value)


def comparison_keys(prop, types):
    return {
        (child_text(item, "ComparableAdjustmentType"), identifier)
        for item in prop.findall(ADJUSTMENTS, NS)
        if child_text(item, "ComparableAdjustmentType") in types
        and (identifier := child_text(item, "AdditionalComparisonLineItemIdentifier"))
    }


def cross_record_violations(document, rule_id):
    role = "GrossRentMultiplierComparable" if rule_id == "UAD1250" else "SalesComparable"
    types = {GRM_TYPE} if rule_id == "UAD1250" else SALES_TYPES
    for analysis in document.findall(".//m:VALUATION_ANALYSIS", NS):
        properties = analysis.find("m:PROPERTIES", NS)
        if properties is None:
            continue
        subjects = properties.findall("m:PROPERTY[@ValuationUseType='SubjectProperty']", NS)
        comparables = properties.findall(f"m:PROPERTY[@ValuationUseType='{role}']", NS)
        if not subjects or not comparables:
            continue
        inventories = [comparison_keys(prop, types) for prop in subjects + comparables]
        if any(keys != inventories[0] for keys in inventories[1:]):
            yield properties, "Additional comparison row keys differ across participating properties."


def adjustment_violations(document):
    for analysis in document.findall(".//m:VALUATION_ANALYSIS", NS):
        for prop in analysis.findall("m:PROPERTIES/m:PROPERTY[@ValuationUseType='SalesComparable']", NS):
            target = prop.find("m:COMPARABLE/m:COMPARABLE_DETAIL/m:SalePriceNetTotalAdjustmentAmount", NS)
            reported = decimal(text(target))
            if reported is None:
                continue
            total = Decimal(0)
            invalid = False
            for item in prop.findall(ADJUSTMENTS, NS):
                amount = item.find("m:ComparableAdjustmentAmount", NS)
                raw = text(amount)
                if not raw:
                    continue
                value = decimal(raw)
                if value is None:
                    invalid = True
                    break
                total += value
            # Invalid numeric operands belong to representation validation.
            if not invalid and reported != total:
                yield target, f"Reported net adjustment {reported}; adjustment sum {total}."


def count_violations(document, rule_id):
    for analysis in document.findall(".//m:VALUATION_ANALYSIS", NS):
        for prop in analysis.findall("m:PROPERTIES/m:PROPERTY[@ValuationUseType='SubjectProperty']", NS):
            if rule_id == "UAD1086":
                for improvement in prop.findall(IMPROVEMENTS, NS):
                    target = improvement.find("m:STRUCTURE/m:STRUCTURE_DETAIL/m:LivingUnitCount", NS)
                    reported = count(target)
                    expected = len(improvement.findall("m:PROPERTY_UNITS/m:PROPERTY_UNIT", NS))
                    if reported is not None and reported != expected:
                        yield target, f"Reported living units {reported}; property units in this improvement {expected}."
                continue
            detail = prop.find("m:PROPERTY_DETAIL", NS)
            if detail is None:
                continue
            if rule_id == "UAD1693":
                target = detail.find("m:LivingUnitExcludingADUCount", NS)
                adus = count(detail.find("m:AccessoryDwellingUnitTotalCount", NS))
                non_adus = count(target)
                values = [count(node) for node in prop.findall(STRUCTURE_COUNTS, NS)]
                if adus is None or non_adus is None or any(value is None for value in values):
                    continue
                reported, expected = adus + non_adus, sum(values)
            elif rule_id == "UAD1016":
                target = detail.find("m:DwellingCount", NS)
                reported = count(target)
                expected = sum(
                    child_text(item, "ImprovementType") == "Dwelling"
                    for item in prop.findall(IMPROVEMENTS + "/m:IMPROVEMENT_DETAIL", NS)
                )
            else:
                name = "AccessoryDwellingUnitTotalCount" if rule_id == "UAD1011" else "LivingUnitExcludingADUCount"
                target = detail.find("m:" + name, NS)
                reported = count(target)
                accepted = {"true", "1"} if rule_id == "UAD1011" else {"false", "0"}
                expected = sum(
                    child_text(item, "AccessoryDwellingUnitIndicator") in accepted
                    for item in prop.findall(UNIT_DETAILS, NS)
                )
            if reported is not None and reported != expected:
                yield target, f"Reported aggregate {reported}; participating record total {expected}."


def evaluate_aggregate_cross_record(root, investor, row):
    rule_id = binding_for(row)
    if rule_id is None:
        return []
    document = etree.fromstring(ET.tostring(root, encoding="utf-8"))
    if rule_id in {"UAD1250", "UAD1455"}:
        violations = cross_record_violations(document, rule_id)
    elif rule_id == "UAD1461":
        violations = adjustment_violations(document)
    else:
        violations = count_violations(document, rule_id)
    return [
        Finding(
            finding_id=f"F-{uuid4().hex[:8]}",
            severity=Severity(row["Severity"].casefold()),
            investor=investor,
            rule_type=RuleType.APPENDIX_H,
            rule_id=rule_id,
            row_id=row["Unique ID"],
            primary_data_element=row["Primary Data Element"],
            property_affected=row["Property Affected"],
            violation_kind="AggregateOrCrossRecordInconsistency",
            data_location=location(target),
            observed_value=observed,
            expected_condition=row["Rule Logic"],
            source=Provenance(
                source_document="data/data-constraints.csv",
                source_version="UAD 3.6",
                source_section=row["Unique ID"],
            ),
            finding=row["Message Text"],
        )
        for target, observed in violations
    ]