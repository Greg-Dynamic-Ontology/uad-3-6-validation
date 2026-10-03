"""Evaluate the 14 CSV-governed UAD chronological requirements.

Date comparisons use the owning property, report, service, or document.
RDF manifests and test fixtures are not runtime inputs.
"""

import hashlib
import json
import re
from datetime import date
from uuid import uuid4
from xml.etree import ElementTree as ET

from lxml import etree

from app.models.common import Provenance
from app.models.enums import RuleType, Severity
from app.models.validation import Finding
from app.services.value_consistency_required_data import (
    ancestor,
    child_text,
    contexts,
    location,
    text,
)


NS = {"m": "http://www.mismo.org/residential/2009/schemas"}
SOURCE_COLUMNS = (
    "Message ID", "Unique ID", "Primary Data Element", "Rule Logic",
    "Severity", "Property Affected", " xPath", "Message Text",
)
FINGERPRINTS = {
    "UAD1051": "3b3ca5c75743d6446c9b040efb82113bcb847ab91ee88bf4b49b6af1b91bab67",
    "UAD1053": "b468bc3be2946c82aee64972d55b746eab9477b87298bc4e35d20853ffcee07b",
    "UAD1131": "854b7de4a16591693f782f8b9d9d9c9d1748e4f7cec63ccb84ebc5ae00f79ae3",
    "UAD1206": "4ecb705407477878c1ad4d9bf82af6d98d0248be95330cbe67ede4f75b2361f3",
    "UAD1258": "27a11458158e9f7576b24549252ce2903d0a8aa5065c7d8c7f10b24a57da66f9",
    "UAD1259": "8923eb6ceb9331e1bc5ac8d805433d261fddae60faad035d69714383951950c0",
    "UAD1505": "d3217926bb300c670cfe1bce5263368970c24e2f550f746427a8c062f7429378",
    "UAD1506": "227c2483031da37ffd05aea87d6f059b87aeadad9fdb047d215fc0b24b68c447",
    "UAD1529": "e29a6e63200d475c3166fd6e8b4586dcdfeedd84b4a7f30bdc9fdb46355a1ed8",
    "UAD1536": "55cb501f9bde4d0f1bbb05eaa02fee04fb923464a0aea2abcdc76e3933a41175",
    "UAD1557": "6366f4eaed7edaaf90f7659a45877bfb1b1fcba629a57cbbd0a43600bb34b6d3",
    "UAD1611": "ba015cf73a70baee263ad42d91277343e4197e4ccd4e5c4572d491e2d998be05",
    "UAD1756": "f04e49a81f3b438e5eafec77f87c573448bc2e412dd9bc4b32ece22e0ac745e1",
    "UAD1757": "e8edf2dc0ec2eb0523a3e072f67806578ea5bdb3caf3ab80457ba6e05494d54a",
}
FUTURE_RULES = {"UAD1258", "UAD1505"}
AGE_RULES = {"UAD1259", "UAD1506", "UAD1757"}
EFFECTIVE_PATH = (
    "m:VALUATION_RECONCILIATION/m:VALUATION_RECONCILIATION_SUMMARY/"
    "m:VALUATION_RECONCILIATION_SUMMARY_DETAIL/m:AppraisalReportEffectiveDate"
)
DATE_PATTERN = re.compile(
    r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?(?:Z|[+-]\d{2}:\d{2})?$"
)


def binding_for(row):
    rule_id = row.get("Message ID")
    expected = FINGERPRINTS.get(rule_id)
    if expected is None:
        return None
    actual = hashlib.sha256(json.dumps(
        [row.get(column) for column in SOURCE_COLUMNS],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    if actual != expected:
        raise ValueError(
            f"{rule_id}: governed chronology definition changed"
        )
    return rule_id


def date_value(raw, precision="date"):
    """Read calendar components without inventing missing months or days."""
    match = DATE_PATTERN.fullmatch(raw)
    if match is None:
        return None
    year, month, day = match.groups()
    year = int(year)
    if not 1 <= year <= 9999:
        return None
    if month is not None and not 1 <= int(month) <= 12:
        return None
    if day is not None:
        try:
            date(year, int(month), int(day))
        except ValueError:
            return None
    if precision == "year":
        return year
    if month is None:
        return None
    if precision == "year-month":
        return year, int(month)
    if day is None:
        return None
    return date(year, int(month), int(day))


def effective_date(context):
    report = ancestor(context, "VALUATION_REPORT")
    if report is not None:
        selected = report.findall(EFFECTIVE_PATH, NS)
    else:
        analysis = ancestor(context, "VALUATION_ANALYSIS")
        if analysis is not None:
            selected = analysis.findall(
                "m:VALUATION_REPORT/" + EFFECTIVE_PATH, NS,
            )
        else:
            # Licenses belong to SERVICE; signatories belong to DOCUMENT.
            owner = ancestor(context, "SERVICE")
            if owner is None:
                owner = ancestor(context, "DOCUMENT")
            if owner is None:
                return ""
            selected = owner.findall(
                ".//m:VALUATION_REPORT/" + EFFECTIVE_PATH, NS,
            )
    if len(selected) > 1:
        raise ValueError(
            "Chronology comparison requires one appraisal effective date "
            "within the owning context; multiple reports require an explicit binding."
        )
    return text(selected[0]) if selected else ""


def violations(document, row, rule_id, today):
    for context in contexts(document, row):
        if rule_id == "UAD1051":
            if child_text(
                context, "NewConstructionIndicator",
            ) not in {"true", "1"}:
                continue
            property_node = ancestor(context, "PROPERTY")
            reference = date_value(effective_date(context), "year")
            if property_node is None or reference is None:
                continue
            for detail in property_node.findall(
                "m:IMPROVEMENTS/m:IMPROVEMENT/m:IMPROVEMENT_DETAIL", NS,
            ):
                if child_text(detail, "ImprovementType") != "Dwelling":
                    continue
                target = detail.find("m:PropertyStructureBuiltYear", NS)
                built = date_value(text(target), "year")
                if built is not None and abs(built - reference) > 1:
                    yield target
            continue

        target = context.find("m:" + row["Primary Data Element"], NS)
        raw = text(target)
        if not raw:
            continue

        if rule_id == "UAD1053":
            if child_text(context, "ImprovementType") != "Dwelling":
                continue
            improvement = ancestor(context, "IMPROVEMENT")
            rating_node = (
                None if improvement is None else improvement.find(
                    "m:STRUCTURE/m:STRUCTURE_DETAIL/"
                    "m:ExteriorConditionRatingCode",
                    NS,
                )
            )
            rating = text(rating_node)
            reference = date_value(effective_date(context), "year")
            built = date_value(raw, "year")
            if rating and reference is not None and built is not None:
                if built > reference + (2 if rating == "C1" else 0):
                    yield target
            continue

        if rule_id == "UAD1529":
            role = ancestor(context, "ROLE")
            detail = (
                None if role is None else role.find("m:ROLE_DETAIL", NS)
            )
            if child_text(detail, "PartyRoleType") not in {
                "Appraiser", "AppraiserSupervisor"
            }:
                continue

        if rule_id in FUTURE_RULES | AGE_RULES:
            observed = date_value(raw)
            if observed is None:
                continue
            if (
                rule_id in FUTURE_RULES and observed > today
                or rule_id in AGE_RULES and (today - observed).days > 367
            ):
                yield target
            continue

        reference_raw = (
            child_text(context, "ListingEndDate")
            if rule_id == "UAD1206" else effective_date(context)
        )
        precision = "year-month" if rule_id == "UAD1611" else "date"
        observed = date_value(raw, precision)
        reference = date_value(reference_raw, precision)

        # Missing or malformed operands belong to presence/format validation.
        if observed is None or reference is None:
            continue
        if rule_id in {"UAD1131", "UAD1206", "UAD1557"}:
            bad = observed > reference
        else:
            bad = observed < reference
        if bad:
            yield target


def evaluate_date_chronology(root, investor, row):
    rule_id = binding_for(row)
    if rule_id is None:
        return []
    document = etree.fromstring(ET.tostring(root, encoding="utf-8"))
    today = date.today()
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
            violation_kind="ProhibitedDateRelationship",
            data_location=location(target),
            observed_value=text(target),
            expected_condition=row["Rule Logic"],
            source=Provenance(
                source_document="data/data-constraints.csv",
                source_version="UAD 3.6",
                source_section=row["Unique ID"],
            ),
            finding=row["Message Text"],
        )
        for target in violations(document, row, rule_id, today)
    ]