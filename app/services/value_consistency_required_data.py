"""Evaluate CSV-governed value and cross-field consistency requirements.

Bindings use source-row fingerprints, never RDF test cases or fixture paths.
Comparisons remain within their owning property, analysis, or service.
"""

import hashlib
import json
from decimal import Decimal, InvalidOperation
from uuid import uuid4
from xml.etree import ElementTree as ET

from lxml import etree

from app.models.common import Provenance
from app.models.enums import RuleType, Severity
from app.models.validation import Finding


NS = {
    "m": "http://www.mismo.org/residential/2009/schemas",
    "xlink": "http://www.w3.org/1999/xlink",
}
M = "{" + NS["m"] + "}"
X = "{" + NS["xlink"] + "}"
SOURCE_COLUMNS = (
    "Message ID", "Unique ID", "Primary Data Element", "Rule Logic",
    "Severity", "Property Affected", " xPath", "Message Text",
)
FINGERPRINTS = {
    "UAD1007": "52213ea2e8c2972d8cdae72a8fbb2e6d52ef1880162c6ae8941043709878b46a",
    "UAD1015": "3c5df4b0ef18101fc503d5e0dd865fb763a37e6fdef218bf399a9b9ed3d31e90",
    "UAD1029": "d67d4ee0ad460f1cd2da323594b25fe030698c27b7688af7ab83cda51e4122b9",
    "UAD1215": "d6444d5777cd24e52fae86b9b5fbb1b74ebdb8e8997feb72ba5823fe3949f6f1",
    "UAD1261": "9c0841245261db3d01d56b18b07236eb4cd719445995f4fb3cb3295e55886d41",
    "UAD1272": "9aeb06e4770b2a4f9ff5305cf6fe5108c7d6158b5bcd0b337e79f7f671c05387",
    "UAD1512": "75b3351d74a171a8e0f281934c79a2e8fe6d9fe89fd2d046a4e1628aa0cf5604",
    "UAD1513": "66a3d938a33c89fc9b80daea42819be0ce9320ead96d8dc4222ef125ba44f6ed",
    "UAD1514": "26bd8682fdf99e44209dc5a1f5d4e065abea1b80a6466a3af57a9addc17d0b09",
    "UAD1515": "cfea4003f790089269f07816dde5e5ccc2fe606f9ab9bb29dab3ad33cd217209",
    "UAD1516": "3d573c1d2ae61cb3858155c27810a8616ad06228200672988abb39d47b439534",
    "UAD1517": "664cf0a3ae7a4a9d1c75d1a760028ec9a3d960e963defac7e64b7387156b7eba",
    "UAD1518": "2e7a0fd370a5e7a2cd6878e051475298f95fb448bd4013b1a260456ecbe82a3b",
    "UAD1533": "9832dad347de72ee53fa43268d3c3beef39f55c2c4d2b53b8de3b5b4ea580056",
    "UAD1574": "61f46db2f5a4ede8cf17235810e6c1ebb587c609a107b5b8b071d7813f341ea6",
    "UAD1605": "6743d598b92b6eb1ad028ab9803a4ac2a7ed780ef634b786144b755e1775a39b",
    "UAD1730": "3541937996c5862c9a19462b48fddfd146875b129f71fe499b0fb51aebd3a108",
}
STATE_CODES = frozenset(
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA "
    "MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN "
    "TX UT VT VA WA WV WI WY DC AS GU MP PR VI".split()
)
METHOD_CERTIFICATIONS = {
    "UAD1512": ("TraditionalAppraisal", "InteriorAndExterior"),
    "UAD1513": ("ExteriorAppraisal", "Exterior"),
    "UAD1514": ("DesktopAppraisal", "NoPhysicalInspection"),
    "UAD1515": ("HybridAppraisal", "NoPhysicalInspection"),
}


def binding_for(row):
    rule_id = row.get("Message ID")
    expected = FINGERPRINTS.get(rule_id)
    if expected is None:
        return None
    actual = hashlib.sha256(json.dumps(
        [row.get(key) for key in SOURCE_COLUMNS],
        ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    if actual != expected:
        raise ValueError(f"{rule_id}: governed consistency definition changed")
    return rule_id


def text(node):
    if node is None or node.get(
        "{http://www.w3.org/2001/XMLSchema-instance}nil"
    ) in {"true", "1"}:
        return ""
    return (node.text or "").strip()


def child_text(node, name):
    return "" if node is None else text(node.find("m:" + name, NS))


def ancestor(node, name):
    return next(
        (item for item in node.iterancestors() if item.tag == M + name),
        None,
    )


def decimal(raw):
    try:
        result = Decimal(raw)
    except InvalidOperation:
        return None
    return result if result.is_finite() else None


def location(node):
    """Return an absolute, namespace-qualified, sibling-indexed XPath."""
    parts = []
    current = node
    while current is not None:
        name = "m:" + etree.QName(current).localname
        parent = current.getparent()
        if parent is not None:
            siblings = [item for item in parent if item.tag == current.tag]
            if len(siblings) > 1:
                name += f"[{siblings.index(current) + 1}]"
        parts.append(name)
        current = parent
    return "/" + "/".join(reversed(parts))


def contexts(document, row):
    parts = row[" xPath"].removeprefix("../").strip("/").split("/")
    path = "//" + "/".join(
        "m:" + part + (
            "[@ValuationUseType='SubjectProperty']"
            if part == "PROPERTY" and row["Property Affected"] == "Subject"
            else ""
        )
        for part in parts
    )
    return document.xpath(path, namespaces=NS)


def certification_targets(analysis):
    return analysis.findall(
        "m:VALUATION_REPORT/m:VALUATION_REPORT_DETAIL/"
        "m:ValuationReportInspectionCertificationType",
        NS,
    )


def appraiser_inspections(analysis):
    """Resolve inspection-to-role links within the same SERVICE."""
    service = ancestor(analysis, "SERVICE")
    if service is None:
        return []
    labels = {}
    for node in service.iter():
        if node.get(X + "label"):
            labels.setdefault(node.get(X + "label"), []).append(node)
    appraisers = {
        role.get(X + "label")
        for role in service.findall(
            "m:PARTIES/m:PARTY/m:ROLES/m:ROLE", NS
        )
        if child_text(role.find("m:ROLE_DETAIL", NS), "PartyRoleType")
        == "Appraiser" and role.get(X + "label")
    }
    linked = set()
    arcrole = "urn:fdc:mismo.org:2009:residential/INSPECTION_CompletedBy_ROLE"
    for relation in service.iter(M + "RELATIONSHIP"):
        if (
            relation.get(X + "arcrole") == arcrole
            and relation.get(X + "to") in appraisers
        ):
            linked.update(labels.get(relation.get(X + "from"), []))
    return [
        inspection for inspection in analysis.findall(
            "m:PROPERTIES/m:PROPERTY[@ValuationUseType='SubjectProperty']/"
            "m:INSPECTIONS/m:INSPECTION", NS
        )
        if inspection in linked
    ]


def inspection_requires(inspection, rule_id):
    detail = inspection.find("m:INSPECTION_DETAIL", NS)
    if detail is None:
        return False
    interior = child_text(detail, "PropertyInteriorInspectionMethodType")
    exterior = child_text(detail, "PropertyExteriorInspectionMethodType")
    remote = {"Virtual", "NoInspection"}
    if rule_id == "UAD1516":
        return interior == exterior == "Physical"
    if rule_id == "UAD1517":
        return interior in remote and exterior in remote
    return interior in remote and exterior == "Physical"


def violating_targets(document, row, rule_id):
    """Yield the inconsistent element, or its container if a value is absent."""
    emitted = set()

    def unique(node):
        if node in emitted:
            return False
        emitted.add(node)
        return True

    if rule_id in {"UAD1516", "UAD1517", "UAD1518"}:
        expected = {
            "UAD1516": "InteriorAndExterior",
            "UAD1517": "NoPhysicalInspection",
            "UAD1518": "Exterior",
        }[rule_id]
        for analysis in document.iter(M + "VALUATION_ANALYSIS"):
            if any(
                inspection_requires(item, rule_id)
                for item in appraiser_inspections(analysis)
            ):
                for target in certification_targets(analysis):
                    if text(target) and text(target) != expected and unique(target):
                        yield target
        return

    if rule_id == "UAD1533":
        for service in document.iter(M + "SERVICE"):
            states = {
                text(state)
                for state in service.findall(
                    "m:VALUATION/m:VALUATION_RESPONSE/m:VALUATION_ANALYSES/"
                    "m:VALUATION_ANALYSIS/m:PROPERTIES/"
                    "m:PROPERTY[@ValuationUseType='SubjectProperty']/"
                    "m:ADDRESS/m:StateCode", NS,
                )
                if text(state)
            }
            for role in service.findall(
                "m:PARTIES/m:PARTY/m:ROLES/m:ROLE", NS
            ):
                detail = role.find("m:ROLE_DETAIL", NS)
                if detail is None or child_text(detail, "PartyRoleType") not in {
                    "Appraiser", "AppraiserSupervisor"
                }:
                    continue
                for target in role.findall(
                    "m:LICENSES/m:LICENSE/m:LICENSE_DETAIL/"
                    "m:LicenseIssuingAuthorityStateCode", NS
                ):
                    if text(target) and any(text(target) != state for state in states):
                        if unique(target):
                            yield target
        return

    element = row["Primary Data Element"]
    for context in contexts(document, row):
        target = context.find("m:" + element, NS)
        raw = text(target)
        bad = False
        if rule_id == "UAD1007":
            bad = bool(raw) and raw not in STATE_CODES
        elif rule_id == "UAD1015":
            count = decimal(raw)
            units = decimal(child_text(context, "LivingUnitExcludingADUCount"))
            bad = count is not None and units is not None and count > units
        elif rule_id == "UAD1029":
            bad = raw not in {"false", "0"}
        elif rule_id == "UAD1215":
            bad = (
                child_text(context, "IncomeApproachIndicator") in {"true", "1"}
                and raw in {"false", "0"}
            )
        elif rule_id == "UAD1261":
            bad = raw != "ReasonableExposureTime"
        elif rule_id == "UAD1272":
            bad = raw != "application/pdf"
        elif rule_id in METHOD_CERTIFICATIONS:
            method, expected = METHOD_CERTIFICATIONS[rule_id]
            analysis = ancestor(context, "VALUATION_ANALYSIS")
            if raw == method and analysis is not None:
                for certificate in certification_targets(analysis):
                    if text(certificate) and text(certificate) != expected:
                        if unique(certificate):
                            yield certificate
            continue
        elif rule_id == "UAD1574":
            bad = (
                child_text(context, "AssociationChargeType") == "AssociationDues"
                and raw != "Monthly"
            )
        elif rule_id == "UAD1605":
            project = ancestor(context, "PROJECT")
            detail = (
                None if project is None
                else project.find("m:PROJECT_DETAIL", NS)
            )
            bad = (
                detail is not None
                and child_text(detail, "ProjectCompletedIndicator") in {"false", "0"}
                and raw not in {"false", "0"}
            )
        elif rule_id == "UAD1730":
            improvement = ancestor(context, "IMPROVEMENT")
            detail = (
                None if improvement is None
                else improvement.find("m:IMPROVEMENT_DETAIL", NS)
            )
            bad = (
                detail is not None
                and child_text(detail, "ImprovementType") == "Outbuilding"
                and raw in {"false", "0"}
            )
        if bad:
            selected = target if target is not None else context
            if unique(selected):
                yield selected


def evaluate_value_consistency(root, investor, row):
    rule_id = binding_for(row)
    if rule_id is None:
        return []
    document = etree.fromstring(ET.tostring(root, encoding="utf-8"))
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
            violation_kind="InconsistentFieldValues",
            data_location=location(target),
            observed_value=text(target) or "missing, empty, or nil",
            expected_condition=row["Rule Logic"],
            source=Provenance(
                source_document="data/data-constraints.csv",
                source_version="UAD 3.6",
                source_section=row["Unique ID"],
            ),
            finding=row["Message Text"],
        )
        for target in violating_targets(document, row, rule_id)
    ]