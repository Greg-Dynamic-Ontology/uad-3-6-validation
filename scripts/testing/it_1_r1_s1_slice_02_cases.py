"""Explicit fixture plans for IT-1R1S1 slice 02.

This module writes no files and does not evaluate production rule logic.
Values are synthetic test data. Expected outcomes are declared here.
The fixture generator must validate completed XML against the UAD XSD.
"""

from dataclasses import dataclass
from itertools import product


@dataclass(frozen=True)
class Variant:
    name: str
    values: tuple[tuple[str, str | None], ...]


@dataclass(frozen=True)
class RulePlan:
    rule_id: str
    target: str
    supplied: str
    applicable: tuple[Variant, ...]
    nonapplicable: tuple[Variant, ...]
    split: tuple[Variant, ...] = ()


@dataclass(frozen=True)
class CasePlan:
    rule_id: str
    name: str
    state: str
    instances: tuple[tuple[tuple[str, str | None], ...], ...]
    missing_positions: tuple[int, ...]
    purpose: str

    @property
    def case_id(self):
        return f"{self.rule_id}/{self.name}"


def variant(name, **values):
    return Variant(name, tuple(values.items()))


def scalar(rule_id, target, supplied, field, applicable, excluded):
    return RulePlan(
        rule_id, target, supplied,
        tuple(variant(value, **{field: value}) for value in applicable),
        (variant(excluded, **{field: excluded}),),
    )


def rule_plans():
    plans = [
        RulePlan(
            "UAD1094", "OutbuildingDefectsExistIndicator", "false",
            (variant("outbuilding-real",
                     ImprovementType="Outbuilding",
                     OutbuildingRealPropertyIndicator="true"),),
            (
                variant("dwelling-real", ImprovementType="Dwelling",
                        OutbuildingRealPropertyIndicator="true"),
                variant("outbuilding-not-real", ImprovementType="Outbuilding",
                        OutbuildingRealPropertyIndicator="false"),
                variant("neither", ImprovementType="Dwelling",
                        OutbuildingRealPropertyIndicator="false"),
            ),
            (
                variant("dwelling-real", ImprovementType="Dwelling",
                        OutbuildingRealPropertyIndicator="true"),
                variant("outbuilding-not-real", ImprovementType="Outbuilding",
                        OutbuildingRealPropertyIndicator="false"),
            ),
        ),
        RulePlan(
            "UAD1100", "ManufacturedHomeFinancingProgramEligibilityType",
            "FannieMaeMHAdvantage",
            (variant("identifier-present",
                     ManufacturedHomeFinancingProgramEligibilityIdentifier=
                     "TEST-ELIGIBILITY-001"),),
            (variant("identifier-absent",
                     ManufacturedHomeFinancingProgramEligibilityIdentifier=None),),
        ),
        RulePlan(
            "UAD1101", "ManufacturedHomeFinancingProgramEligibilityIdentifier",
            "TEST-ELIGIBILITY-001",
            tuple(variant(value,
                          ManufacturedHomeFinancingProgramEligibilityType=value)
                  for value in (
                      "FannieMaeMHAdvantage", "FreddieMacCHOICEHome", "Other"
                  )),
            (variant("type-absent",
                     ManufacturedHomeFinancingProgramEligibilityType=None),),
        ),
        RulePlan(
            "UAD1147", "RoomUpdatedTimeframeType", "OneToFiveYears",
            tuple(variant(f"{room}-{status}",
                          RoomType=room, RoomUpdateStatusType=status)
                  for room, status in product(
                      ("FullBathroom", "HalfBathroom", "Kitchen"),
                      ("FullyUpdated", "PartiallyUpdated"),
                  )),
            (
                variant("wrong-room", RoomType="Bedroom",
                        RoomUpdateStatusType="FullyUpdated"),
                variant("not-updated", RoomType="Kitchen",
                        RoomUpdateStatusType="NotUpdated"),
                variant("neither", RoomType="Bedroom",
                        RoomUpdateStatusType="NotUpdated"),
            ),
            (
                variant("wrong-room", RoomType="Bedroom",
                        RoomUpdateStatusType="FullyUpdated"),
                variant("not-updated", RoomType="Kitchen",
                        RoomUpdateStatusType="NotUpdated"),
            ),
        ),
        scalar(
            "UAD1156", "ImprovementComponentConditionStatusType",
            "TypicalWearAndTear", "ImprovementComponentType",
            ("WallsAndCeiling", "Other"), "Flooring",
        ),
        RulePlan(
            "UAD1294", "DistanceFromPropertyLinearMeasure", "100",
            tuple(variant(proximity, EnvironmentalConditionType="Radon",
                          EnvironmentalConditionProximityType=proximity)
                  for proximity in ("Bordering", "Offsite")),
            (
                variant("excluded-condition", EnvironmentalConditionType="None",
                        EnvironmentalConditionProximityType="Bordering"),
                variant("onsite", EnvironmentalConditionType="Radon",
                        EnvironmentalConditionProximityType="Onsite"),
                variant("neither", EnvironmentalConditionType="None",
                        EnvironmentalConditionProximityType="Onsite"),
            ),
            (
                variant("excluded-condition", EnvironmentalConditionType="None",
                        EnvironmentalConditionProximityType="Bordering"),
                variant("onsite", EnvironmentalConditionType="Radon",
                        EnvironmentalConditionProximityType="Onsite"),
            ),
        ),
        scalar(
            "UAD1298", "EnvironmentalConditionProximityType", "Bordering",
            "EnvironmentalConditionType", ("Radon",), "None",
        ),
        scalar(
            "UAD1330", "SiteInfluenceProximityType", "Bordering",
            "SiteInfluenceType", ("BusyRoadway",), "BodyOfWater",
        ),
        RulePlan(
            "UAD1556", "InspectionDate", "2026-09-01",
            tuple(
                variant(f"{exterior}-{interior}",
                        PropertyExteriorInspectionMethodType=exterior,
                        PropertyInteriorInspectionMethodType=interior)
                for exterior, interior in product(
                    ("NoInspection", "Physical", "Virtual"), repeat=2
                )
                if (exterior, interior) != ("NoInspection", "NoInspection")
            ),
            (variant("neither",
                     PropertyExteriorInspectionMethodType="NoInspection",
                     PropertyInteriorInspectionMethodType="NoInspection"),),
        ),
        scalar(
            "UAD1568", "AmenityOwnershipType", "Owned", "AmenityType",
            ("BoatSlip", "UnitStorage"), "Clubhouse",
        ),
        scalar(
            "UAD1573", "AssociationChargeAmount", "125",
            "AssociationChargeType", ("AssociationDues",),
            "OwnershipTransferFee",
        ),
        RulePlan(
            "UAD1578", "AssociationChargeBalanceAmount", "0",
            (variant("existing-assessment",
                     AssociationChargeType="AssociationSpecialAssessment",
                     AssociationSpecialAssessmentStatusType="Existing"),),
            (
                variant("wrong-charge", AssociationChargeType="AssociationDues",
                        AssociationSpecialAssessmentStatusType="Existing"),
                variant("proposed-assessment",
                        AssociationChargeType="AssociationSpecialAssessment",
                        AssociationSpecialAssessmentStatusType="Proposed"),
                variant("neither", AssociationChargeType="AssociationDues",
                        AssociationSpecialAssessmentStatusType="Proposed"),
            ),
            (
                variant("wrong-charge", AssociationChargeType="AssociationDues",
                        AssociationSpecialAssessmentStatusType="Existing"),
                variant("proposed-assessment",
                        AssociationChargeType="AssociationSpecialAssessment",
                        AssociationSpecialAssessmentStatusType="Proposed"),
            ),
        ),
        scalar(
            "UAD1613", "AssociationSpecialAssessmentStatusType", "Existing",
            "AssociationChargeType", ("AssociationSpecialAssessment",),
            "AssociationDues",
        ),
    ]

    for rule_id, inventory in (
        ("UAD1629", "ActiveListings"),
        ("UAD1639", "PendingSales"),
        ("UAD1642", "TotalSales"),
    ):
        excluded = "TotalSales" if inventory == "ActiveListings" else "ActiveListings"
        plans.append(scalar(
            rule_id, "MarketInventoryCount", "0",
            "MarketInventoryType", (inventory,), excluded,
        ))

    for rule_id, inventory, target, supplied in (
        ("UAD1630", "ActiveListings", "MarketInventoryHighestPriceAmount", "250000"),
        ("UAD1632", "ActiveListings", "MarketInventoryLowestPriceAmount", "150000"),
        ("UAD1634", "ActiveListings", "MarketInventoryMedianDaysOnMarketCount", "0"),
        ("UAD1635", "ActiveListings", "MarketInventoryMedianPriceAmount", "200000"),
        ("UAD1643", "TotalSales", "MarketInventoryHighestPriceAmount", "250000"),
        ("UAD1645", "TotalSales", "MarketInventoryLowestPriceAmount", "150000"),
        ("UAD1647", "TotalSales", "MarketInventoryMedianPriceAmount", "200000"),
    ):
        wrong = "PendingSales"
        zero = variant("zero", MarketInventoryType=inventory,
                       MarketInventoryCount="0")
        wrong_positive = variant("wrong-type-positive", MarketInventoryType=wrong,
                                 MarketInventoryCount="1")
        plans.append(RulePlan(
            rule_id, target, supplied,
            (variant("one", MarketInventoryType=inventory,
                     MarketInventoryCount="1"),
             variant("ten", MarketInventoryType=inventory,
                     MarketInventoryCount="10")),
            (zero, wrong_positive,
             variant("wrong-type-zero", MarketInventoryType=wrong,
                     MarketInventoryCount="0")),
            (zero, wrong_positive),
        ))

    plans.extend([
        scalar(
            "UAD1664", "CarStorageAreaMeasure", "200", "CarStorageType",
            ("Carport", "Garage"), "None",
        ),
        scalar(
            "UAD1665", "CarStorageAttachmentType", "Detached", "CarStorageType",
            ("Carport", "Garage"), "None",
        ),
        scalar(
            "UAD1669", "ImprovedSurfaceMaterialType", "Concrete", "CarStorageType",
            ("Driveway", "SharedDriveway"), "None",
        ),
        RulePlan(
            "UAD1671", "ParkingSpacesCount", "2",
            tuple(variant(f"{kind}-false", CarStorageType=kind,
                          TenOrMoreParkingSpacesIndicator="false")
                  for kind in ("Driveway", "SharedDriveway"))
            + tuple(variant(f"{kind}-{indicator}", CarStorageType=kind,
                            TenOrMoreParkingSpacesIndicator=indicator)
                    for kind, indicator in product(
                        ("Carport", "CommonCarport", "Garage", "OpenLot",
                         "Other", "ParkingGarage"),
                        ("false", "true"),
                    )),
            (
                variant("driveway-ten-or-more", CarStorageType="Driveway",
                        TenOrMoreParkingSpacesIndicator="true"),
                variant("shared-driveway-ten-or-more",
                        CarStorageType="SharedDriveway",
                        TenOrMoreParkingSpacesIndicator="true"),
                variant("none-false", CarStorageType="None",
                        TenOrMoreParkingSpacesIndicator="false"),
                variant("none-true", CarStorageType="None",
                        TenOrMoreParkingSpacesIndicator="true"),
            ),
            (
                variant("driveway-ten-or-more", CarStorageType="Driveway",
                        TenOrMoreParkingSpacesIndicator="true"),
                variant("none-false", CarStorageType="None",
                        TenOrMoreParkingSpacesIndicator="false"),
            ),
        ),
        scalar(
            "UAD1672", "TenOrMoreParkingSpacesIndicator", "false",
            "CarStorageType", ("Driveway", "SharedDriveway"), "None",
        ),
        scalar(
            "UAD1673", "ProjectParkingSpaceAssignmentType", "Assigned",
            "CarStorageType", ("CommonCarport", "OpenLot", "ParkingGarage"), "None",
        ),
        scalar(
            "UAD1687", "DwellingExteriorDefectsExistIndicator", "false",
            "ImprovementType", ("Dwelling",), "Outbuilding",
        ),
    ])
    return tuple(sorted(plans, key=lambda plan: plan.rule_id))


def case_plans():
    cases = []
    for plan in rule_plans():
        def instance(branch, supplied=False):
            return branch.values + (
                (plan.target, plan.supplied if supplied else None),
            )

        def add(name, state, instances, missing, purpose):
            cases.append(CasePlan(
                plan.rule_id, name, state, tuple(instances),
                tuple(missing), purpose,
            ))

        for branch in plan.applicable:
            add(
                f"{branch.name}-missing", "applicable_missing",
                (instance(branch),), (1,),
                f"Applicable branch {branch.name} requires {plan.target}.",
            )
            add(
                f"{branch.name}-supplied", "applicable_supplied",
                (instance(branch, True),), (),
                f"Supplying {plan.target} satisfies branch {branch.name}.",
            )
        for branch in plan.nonapplicable:
            add(
                f"{branch.name}-not-applicable", "not_applicable",
                (instance(branch),), (),
                f"Branch {branch.name} does not require {plan.target}.",
            )

        applicable = plan.applicable[0]
        nonapplicable = plan.nonapplicable[0]
        add(
            "first-missing-second-supplied", "applicable_missing",
            (instance(applicable), instance(applicable, True)), (1,),
            "A later instance cannot supply the first instance's required value.",
        )
        add(
            "first-supplied-second-missing", "applicable_missing",
            (instance(applicable, True), instance(applicable)), (2,),
            "An earlier instance cannot supply the second instance's required value.",
        )
        add(
            "nonapplicable-with-compliant-neighbor", "applicable_supplied",
            (instance(nonapplicable), instance(applicable, True)), (),
            "A compliant applicable neighbor must not activate a nonapplicable instance.",
        )
        add(
            "two-applicable-missing", "applicable_missing",
            (instance(applicable), instance(applicable)), (1, 2),
            "Each deficient applicable instance requires its own finding.",
        )
        if plan.split:
            add(
                "conditions-split-between-instances", "not_applicable",
                tuple(instance(branch) for branch in plan.split), (),
                "Condition fields in different instances must not be combined.",
            )

    ids = [case.case_id for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate slice-02 case IDs.")
    return tuple(cases)