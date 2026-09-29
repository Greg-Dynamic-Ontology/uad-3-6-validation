"""Explicit conditional/scoped requirements, including repeated listing rules.

Production definitions are checked against the governed CSV.
No fixture, test manifest, or expected-result graph is read here.
"""

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
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
    condition: tuple | None = None
    equality_trigger: tuple[str, str] | None = None
    trigger_at_subject: bool = False


SCOPED_RULES = {
    ("0300.0011", "UAD1050"): ScopedRule(
        element="PropertyStructureBuiltYear",
        logic=(
            'If ImprovementType = "Dwelling" and '
            "PropertyStructureBuiltYear is not provided "
            "in a given instance of IMPROVEMENT_DETAIL"
        ),
        severity="Fatal",
        parent_path=(
            PROPERTY_PATH
            + "IMPROVEMENTS/IMPROVEMENT/IMPROVEMENT_DETAIL/"
        ),
        equality_trigger=("m:ImprovementType", "Dwelling"),
    ),
    ("0300.0025", "UAD1056"): ScopedRule(
        element="OutbuildingType",
        logic=(
            'If ImprovementType = "Outbuilding" and '
            "OutbuildingType is not provided "
            "in a given instance of IMPROVEMENT_DETAIL"
        ),
        severity="Fatal",
        parent_path=(
            PROPERTY_PATH
            + "IMPROVEMENTS/IMPROVEMENT/IMPROVEMENT_DETAIL/"
        ),
        equality_trigger=("m:ImprovementType", "Outbuilding"),
    ),
    ("0300.0026", "UAD1057"): ScopedRule(
        element="OutbuildingTypeOtherDescription",
        logic=(
            'If OutbuildingType = "Other" and '
            "OutbuildingTypeOtherDescription is not provided "
            "in a given instance of IMPROVEMENT_DETAIL"
        ),
        severity="Fatal",
        parent_path=(
            PROPERTY_PATH
            + "IMPROVEMENTS/IMPROVEMENT/IMPROVEMENT_DETAIL/"
        ),
        equality_trigger=("m:OutbuildingType", "Other"),
    ),
    ("0900.0007", "UAD1204"): ScopedRule(
        element="DaysOnMarketCount",
        logic=(
            'If ListedWithinPreviousYearIndicator = "true" and '
            "DaysOnMarketCount is not provided "
            "in a given instance of LISTING_INFORMATION_DETAIL"
        ),
        severity="Fatal",
        parent_path=(
            PROPERTY_PATH
            + "LISTING_INFORMATIONS/LISTING_INFORMATION/LISTING_INFORMATION_DETAIL/"
        ),
        equality_trigger=("m:LISTING_INFORMATION_SUMMARY/m:ListedWithinPreviousYearIndicator", "true"),
        trigger_at_subject=True,
    ),
    ("0900.0008", "UAD1205"): ScopedRule(
        element="FinalListPriceAmount",
        logic=(
            'If ListedWithinPreviousYearIndicator = "true" and '
            "FinalListPriceAmount is not provided "
            "in a given instance of LISTING_INFORMATION_DETAIL"
        ),
        severity="Fatal",
        parent_path=(
            PROPERTY_PATH
            + "LISTING_INFORMATIONS/LISTING_INFORMATION/LISTING_INFORMATION_DETAIL/"
        ),
        equality_trigger=("m:LISTING_INFORMATION_SUMMARY/m:ListedWithinPreviousYearIndicator", "true"),
        trigger_at_subject=True,
    ),
    ("0900.0016", "UAD1208"): ScopedRule(
        element="ListingTypeOtherDescription",
        logic=(
            'If ListingType = "Other" and '
            "ListingTypeOtherDescription is not provided "
            "in a given instance of LISTING_INFORMATION_DETAIL"
        ),
        severity="Fatal",
        parent_path=(
            PROPERTY_PATH
            + "LISTING_INFORMATIONS/LISTING_INFORMATION/LISTING_INFORMATION_DETAIL/"
        ),
        equality_trigger=("m:ListingType", "Other"),
        trigger_at_subject=False,
    ),
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
    ("0100.0029", "UAD1025"): ScopedRule(
        element="PropertyGroundLeaseExpirationDate",
        logic=(
            'If PropertyEstateType = "Leasehold" and '
            'LandOwnedInCommonIndicator = "false", '
            "and PropertyGroundLeaseExpirationDate is not provided"
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


# Source hashes pin these fields in order; changing a governed definition
# requires review of its predicate mapping before the hash is updated.
SOURCE_COLUMNS = (
    "Unique ID", "Message ID", "Primary Data Element", "Rule Logic",
    "Severity", "Property Affected", " xPath",
)

# Predicates are evaluated only within the source-declared parent instance.
# No test case definitions, manifests, or RDF graphs are used at runtime.
LOCAL_RULES = {
    # OutbuildingDefectsExistIndicator
    ("0300.0111", "UAD1094"): (
        "8df7fecf905ff0b8dfbd3aed38a79b7cd37414d354da4a3685a3825590a920f9",
        (
            "all",
            ("in", "ImprovementType", "Outbuilding"),
            ("in", "OutbuildingRealPropertyIndicator", "true"),
        ),
    ),
    # ManufacturedHomeFinancingProgramEligibilityType
    ("0500.0005", "UAD1100"): (
        "247758e2db3642b8f4bd3cb5289159f1dc3697410aad1dffb27f0c5cd620438d",
        ("present", "ManufacturedHomeFinancingProgramEligibilityIdentifier"),
    ),
    # ManufacturedHomeFinancingProgramEligibilityIdentifier
    ("0500.0004", "UAD1101"): (
        "401508a99d05fbb98ea753cd00af33f42d42b8d9a2735a82f6a0b164ff02b105",
        ("present", "ManufacturedHomeFinancingProgramEligibilityType"),
    ),
    # RoomUpdatedTimeframeType
    ("0700.0034", "UAD1147"): (
        "8f4939f493d1d067f97c8b97e2043f5f4713dd326173d1d1de557c3901f05479",
        (
            "all",
            ("in", "RoomType", "FullBathroom", "HalfBathroom", "Kitchen"),
            ("in", "RoomUpdateStatusType", "FullyUpdated", "PartiallyUpdated"),
        ),
    ),
    # ImprovementComponentConditionStatusType
    ("0700.0045", "UAD1156"): (
        "6714621ab5aacd4ae1b2c80920a2c3c5127805014e05bfba492d3c8a988bdb0f",
        ("in", "ImprovementComponentType", "WallsAndCeiling", "Other"),
    ),
    # DistanceFromPropertyLinearMeasure
    ("1500.0015", "UAD1294"): (
        "969294f63c3bc44c63f1c4522bc0ce916a5d10ae178000e26c586327315ad80f",
        (
            "all",
            ("ne", "EnvironmentalConditionType", "None"),
            ("in", "EnvironmentalConditionProximityType", "Bordering", "Offsite"),
        ),
    ),
    # EnvironmentalConditionProximityType
    ("1500.0018", "UAD1298"): (
        "0178763681fd3305523d09a9fb356a705c543ec675dd2f0bac15b607f9b8eb42",
        ("ne", "EnvironmentalConditionType", "None"),
    ),
    # SiteInfluenceProximityType
    ("1500.0086", "UAD1330"): (
        "5af0ca3f4ec2128161cbbcf3a1615972a5c262d8c172f0de617e3a88093fb1b4",
        ("ne", "SiteInfluenceType", "BodyOfWater"),
    ),
    # InspectionDate
    ("2400.0080; 2400.0502", "UAD1556"): (
        "1103b979300e395a29a0aec0b4988062730d19adb1cc1f64ca9d50a8da6c7f4d",
        (
            "any",
            ("in", "PropertyExteriorInspectionMethodType", "Physical", "Virtual"),
            ("in", "PropertyInteriorInspectionMethodType", "Physical", "Virtual"),
        ),
    ),
    # AmenityOwnershipType
    ("2500.0002", "UAD1568"): (
        "437ec9152057d64ec2d4b4c238af24cdf7dc23b70ecb7249c119b1c143192c64",
        ("in", "AmenityType", "BoatSlip", "UnitStorage"),
    ),
    # AssociationChargeAmount
    ("2500.0007", "UAD1573"): (
        "93ab2459f38b718523005bf3145450a409948e889a5c65cf82f204201f02adc1",
        ("in", "AssociationChargeType", "AssociationDues"),
    ),
    # AssociationChargeBalanceAmount
    ("2500.0013", "UAD1578"): (
        "e197c236e7f07b4ee59de20ba543b3b38137ab0183d7e54648aec1b83772ddd2",
        (
            "all",
            ("in", "AssociationChargeType", "AssociationSpecialAssessment"),
            ("in", "AssociationSpecialAssessmentStatusType", "Existing"),
        ),
    ),
    # AssociationSpecialAssessmentStatusType
    ("2500.0163", "UAD1613"): (
        "867ac5300fac21f4858ef4f7995464c7ad51f3c72e770dde66617d04844dc359",
        ("in", "AssociationChargeType", "AssociationSpecialAssessment"),
    ),
    # MarketInventoryCount
    ("3000.0018", "UAD1629"): (
        "f5c8d2cb7f82bfc07d21a49d06a9f3d13ed582b4782823ec2091bb8f7593be6f",
        ("in", "MarketInventoryType", "ActiveListings"),
    ),
    # MarketInventoryHighestPriceAmount
    ("3000.0019", "UAD1630"): (
        "5671da55d1a06756c66d83fdd4bce630de3279e643078091a5ab82317d8b3f0e",
        (
            "all",
            ("in", "MarketInventoryType", "ActiveListings"),
            ("gt", "MarketInventoryCount", "0"),
        ),
    ),
    # MarketInventoryLowestPriceAmount
    ("3000.0020", "UAD1632"): (
        "56fdccffac621536c953fdc1719f4ae8e22bdc4edde3bcfc306b411cd5613a49",
        (
            "all",
            ("in", "MarketInventoryType", "ActiveListings"),
            ("gt", "MarketInventoryCount", "0"),
        ),
    ),
    # MarketInventoryMedianDaysOnMarketCount
    ("3000.0021", "UAD1634"): (
        "0ef713855c217e0e912fcb77d52a3ea3598bd37884e299eee550a8f7d2119e0a",
        (
            "all",
            ("in", "MarketInventoryType", "ActiveListings"),
            ("gt", "MarketInventoryCount", "0"),
        ),
    ),
    # MarketInventoryMedianPriceAmount
    ("3000.0022", "UAD1635"): (
        "4107ce995192b5ca1cc567f63627be4f88e6a97ede0a305e4d46a76a24196f23",
        (
            "all",
            ("in", "MarketInventoryType", "ActiveListings"),
            ("gt", "MarketInventoryCount", "0"),
        ),
    ),
    # MarketInventoryCount
    ("3000.0024", "UAD1639"): (
        "501a93cbd7aced1b3d9331104285997e22d4544f65c68200f3fac376e6ff2222",
        ("in", "MarketInventoryType", "PendingSales"),
    ),
    # MarketInventoryCount
    ("3000.0026", "UAD1642"): (
        "e5fe326015486f89a790353d4be76e02742d58a21546c2499b979445d003c9e1",
        ("in", "MarketInventoryType", "TotalSales"),
    ),
    # MarketInventoryHighestPriceAmount
    ("3000.0027", "UAD1643"): (
        "788c326aeeb8ee0f1e37891c60bc6bab712e0b797260638f438b368899f4278c",
        (
            "all",
            ("in", "MarketInventoryType", "TotalSales"),
            ("gt", "MarketInventoryCount", "0"),
        ),
    ),
    # MarketInventoryLowestPriceAmount
    ("3000.0028", "UAD1645"): (
        "ae94eaf300dcbb42dd4a85036ef0920231cafc81c807481fe7002404178775bc",
        (
            "all",
            ("in", "MarketInventoryType", "TotalSales"),
            ("gt", "MarketInventoryCount", "0"),
        ),
    ),
    # MarketInventoryMedianPriceAmount
    ("3000.0029", "UAD1647"): (
        "fc01d6f63bb1fedcca66a8696461627692d1d13976bd2d2f720da0c0dd6ae95d",
        (
            "all",
            ("in", "MarketInventoryType", "TotalSales"),
            ("gt", "MarketInventoryCount", "0"),
        ),
    ),
    # CarStorageAreaMeasure
    ("3200.0004", "UAD1664"): (
        "f3926fb62059be88da2b94a7fcdc42a74edd156cf51138591ae6d74a923dbadf",
        ("in", "CarStorageType", "Carport", "Garage"),
    ),
    # CarStorageAttachmentType
    ("3200.0005", "UAD1665"): (
        "6856cfe8c94102057e03c0ca07d2b47732bf2a8041c33805a3fbe5a521754cc7",
        ("in", "CarStorageType", "Carport", "Garage"),
    ),
    # ImprovedSurfaceMaterialType
    ("3200.0008", "UAD1669"): (
        "2d19d10f04d90b152c063fb8d964b0e8359974068709a49a3eeb1ef4f9ac1033",
        ("in", "CarStorageType", "Driveway", "SharedDriveway"),
    ),
    # ParkingSpacesCount
    ("3200.0010", "UAD1671"): (
        "c40001df791a0b61b1ad6801e2cad168c4506ce34ff1c13bc772efeaad74dd3f",
        (
            "any",
            (
                "all",
                ("in", "CarStorageType", "Driveway", "SharedDriveway"),
                ("in", "TenOrMoreParkingSpacesIndicator", "false"),
            ),
            (
                "in", "CarStorageType", "Carport", "CommonCarport",
                "Garage", "OpenLot", "Other", "ParkingGarage",
            ),
        ),
    ),
    # TenOrMoreParkingSpacesIndicator
    ("3200.0011", "UAD1672"): (
        "e76292b02e98c75b303b3726de81ebe6094f60ed207638836089db729bc0464a",
        ("in", "CarStorageType", "Driveway", "SharedDriveway"),
    ),
    # ProjectParkingSpaceAssignmentType
    ("3200.0012", "UAD1673"): (
        "57b7b5ea155cb770e3441de31cb53fe95287cb93d712b85b32bfcf12923f8765",
        ("in", "CarStorageType", "CommonCarport", "OpenLot", "ParkingGarage"),
    ),
    # DwellingExteriorDefectsExistIndicator
    ("3900.0097", "UAD1687"): (
        "f361ebd8aca81138c70b63e2808898661d9638b8fe60e862f11e62e8a30a0edf",
        ("in", "ImprovementType", "Dwelling"),
    ),
}


def scoped_spec(rule: dict[str, str]) -> ScopedRule | None:
    key = (rule.get("Unique ID"), rule.get("Message ID"))
    existing = SCOPED_RULES.get(key)
    if existing is not None:
        return existing
    local = LOCAL_RULES.get(key)
    if local is None:
        return None

    expected_hash, condition = local
    values = [rule.get(column) for column in SOURCE_COLUMNS]
    actual_hash = hashlib.sha256(
        json.dumps(
            values, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    if actual_hash != expected_hash:
        raise ValueError(
            f"{key[0]}/{key[1]}: governed definition changed; "
            "review the local condition mapping"
        )
    return ScopedRule(
        element=rule["Primary Data Element"],
        logic=rule["Rule Logic"],
        severity=rule["Severity"],
        parent_path=rule[" xPath"],
        condition=condition,
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


def _local_condition(
    context: Element,
    condition: tuple,
    identity: str,
) -> bool | None:
    """Evaluate an explicit predicate without crossing instance boundaries."""
    operator = condition[0]
    if operator in {"all", "any"}:
        unknown = False
        for child in condition[1:]:
            result = _local_condition(context, child, identity)
            if operator == "all" and result is False:
                return False
            if operator == "any" and result is True:
                return True
            unknown |= result is None
        if unknown:
            return None
        return operator == "all"

    field = condition[1]
    nodes = context.findall(f"m:{field}", NS)
    if len(nodes) > 1:
        raise ValueError(f"{identity}: ambiguous condition input at {field}")
    if nodes and list(nodes[0]):
        raise ValueError(f"{identity}: nonscalar condition input at {field}")
    if operator == "present":
        return bool(nodes) and _has_value(nodes[0])
    if not nodes:
        return None
    if not _has_value(nodes[0]):
        raise ValueError(f"{identity}: invalid condition input at {field}")
    value = (nodes[0].text or "").strip()
    if operator == "in":
        return value in condition[2:]
    if operator == "ne":
        return value != condition[2]
    if operator == "gt":
        try:
            number = Decimal(value)
        except InvalidOperation as error:
            raise ValueError(
                f"{identity}: nonnumeric input at {field}"
            ) from error
        if not number.is_finite():
            raise ValueError(f"{identity}: nonfinite input at {field}")
        return number > Decimal(condition[2])
    raise ValueError(f"{identity}: unsupported condition operator {operator}")


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
            if rule_id in {"UAD1021", "UAD1024", "UAD1025"}:
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

            elif rule_id in {"UAD1024", "UAD1025"}:
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
                parent_path = "/".join(
                    "m:" + part
                    for part in specification.parent_path.removeprefix(
                        PROPERTY_PATH
                    ).strip("/").split("/")
                )

            if applies is False:
                continue

            containers = subject.findall(parent_path, NS)
            property_level = rule_id in {"UAD1021", "UAD1024", "UAD1025"}
            if property_level and len(containers) > 1:
                raise ValueError(
                    f"{identity}: ambiguous dependent context"
                )

            # Missing property-level containers still mean missing data.
            # Local rules apply within existing source-declared instances.
            contexts = (
                containers
                if not property_level
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

                if specification.equality_trigger is not None:
                    trigger_path, matching_value = specification.equality_trigger
                    trigger_context = (
                        subject if specification.trigger_at_subject else container
                    )
                    triggers = trigger_context.findall(trigger_path, NS)
                    if len(triggers) > 1:
                        raise ValueError(
                            f"{identity}: ambiguous condition input at {trigger_path}"
                        )
                    if triggers and list(triggers[0]):
                        raise ValueError(
                            f"{identity}: nonscalar condition input at {trigger_path}"
                        )
                    # Absent, blank, or nil inputs cannot match this equality.
                    # Requirements for the trigger itself remain independent.
                    if (
                        not triggers
                        or not _has_value(triggers[0])
                        or (triggers[0].text or "").strip() != matching_value
                    ):
                        continue

                if specification.condition is not None:
                    applies = _local_condition(
                        container, specification.condition, identity
                    )
                    if applies is None:
                        raise ValueError(
                            f"{identity}: missing input prevents condition evaluation"
                        )
                    if not applies:
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