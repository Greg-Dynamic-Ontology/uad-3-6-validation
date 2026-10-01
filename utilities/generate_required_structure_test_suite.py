"""Generate the IT-1R3S1 RDF inventory from governed source rows."""

import csv
import copy
import glob
import hashlib
import json
from pathlib import Path

from lxml import etree
from rdflib import Graph, Namespace, URIRef


ROOT = Path(__file__).resolve().parents[1]
TRACKING = ROOT / "data/spreadsheet-rule-category-tracking.ttl"
RULES = ROOT / "data/data-constraints.csv"
OUTPUT = ROOT / (
    "data/uad36-test-suite/tests/fixtures/required_structures/"
    "required-structures-test-suite.ttl"
)
PRODUCTION_OUTPUT = ROOT / "data/required-structure-bindings.ttl"
T = Namespace("urn:uad36:work-tracking:vocab:")
SCENARIO = URIRef("urn:uad36:work-tracking:scenario:required_structures")
TEST = Namespace("urn:uad36:test-suite:vocab:")

SOURCE_FIELDS = {
    "Message ID": "ruleId",
    "Unique ID": "sourceUniqueIdCell",
    "Primary Data Element": "primaryDataElement",
    "Rule Logic": "ruleLogic",
    "Severity": "severity",
    "Property Affected": "propertyAffected",
    " xPath": "xpath",
    "Message Text": "messageText",
}
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

TARGET_XPATHS = {
    "UAD1032": "//m:PROPERTY[@ValuationUseType='SubjectProperty']",
    "UAD1038": "//m:VALUATION_COMMENTARY[m:ValuationAnalysisCategoryType='PropertySpecialTaxAssessments']",
    "UAD1067": "//m:ImprovementComponentType[.='Foundation']",
    "UAD1072": "//m:ImprovementComponentType[.='Roof']",
    "UAD1079": "//m:ImprovementComponentType[.='ExteriorWallsAndTrim']",
    "UAD1143": "//m:ROOM_DETAIL[m:RoomType='Kitchen']",
    "UAD1214": "//m:PROPERTY[@ValuationUseType='GrossRentMultiplierComparable']",
    "UAD1217": "//m:PROPERTY[@ValuationUseType='RentalComparable']",
    "UAD1238": "//m:PROPERTY[@ValuationUseType='LandComparable']",
    "UAD1274": "//m:IMAGE[m:ImageCategoryType='DwellingFront']",
    "UAD1275": "//m:PROPERTY[@ValuationUseType='SalesComparable']//m:IMAGE[m:ImageCategoryType='PropertyPhoto']",
    "UAD1278": "//m:IMAGE[m:ImageCategoryType='WaterFrontage']",
    "UAD1279": "//m:ROOM[m:ROOM_DETAIL/m:RoomType='Kitchen' or m:ROOM_DETAIL/m:RoomType='HalfBathroom' or m:ROOM_DETAIL/m:RoomType='FullBathroom']/m:IMAGES/m:IMAGE",
    "UAD1280": "//m:PROPERTY[@ValuationUseType='GrossRentMultiplierComparable']//m:IMAGE[m:ImageCategoryType='PropertyPhoto']",
    "UAD1283": "//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:IMAGE[m:ImageCategoryType='SalesComparableMap']",
    "UAD1284": "//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:IMAGE[m:ImageCategoryType='ManufacturedHomeHUDCertificationLabel']",
    "UAD1285": "//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:IMAGE[m:ImageCategoryType='ManufacturedHomeHUDDataPlate']",
    "UAD1304": "//m:PARCEL_IDENTIFICATION[m:ParcelIdentificationType='AssessorUnformattedIdentifier']",
    "UAD1345": "//m:SITE_UTILITY_DETAIL[m:UtilityType='Electricity']",
    "UAD1346": "//m:SITE_UTILITY_DETAIL[m:UtilityType='Water']",
    "UAD1347": "//m:SITE_UTILITY_DETAIL[m:UtilityType='SanitarySewer']",
    "UAD1353": "//m:SITE_UTILITY_DETAIL[m:UtilityType='Electricity' and m:SiteUtilityOwnershipType='Public']",
    "UAD1374": "//m:VALUATION_COMMENTARY[m:ValuationAnalysisCategoryType='HazardZones']",
    "UAD1375": "//m:VALUATION_COMMENTARY[m:ValuationAnalysisCategoryType='HazardZones']/m:ValueMarketabilityImpactType",
    "UAD1377": "//m:VALUATION_COMMENTARY[m:ValuationAnalysisCategoryType='ZoningCompliance']",
    "UAD1378": "//m:VALUATION_COMMENTARY[m:ValuationAnalysisCategoryType='ZoningCompliance']/m:ValueMarketabilityImpactType",
    "UAD1386": "//m:VALUATION_COMMENTARY[m:ValuationAnalysisCategoryType='OverallQualityAndCondition']",
    "UAD1520": "//m:ROLE_DETAIL[m:PartyRoleType='PropertyDataCollector']",
    "UAD1534": "//m:PARTY[.//m:PartyRoleType='AppraiserSupervisor']",
    "UAD1542": "//m:PARTY[.//m:PartyRoleType='Client']",
    "UAD1543": "//m:PARTY[.//m:PartyRoleType='Client']//m:ROLE_DETAIL[m:PartyRoleType='Attorney' or m:PartyRoleType='Investor' or m:PartyRoleType='Lender' or m:PartyRoleType='ManagementCompany' or m:PartyRoleType='Other']",
    "UAD1554": "//m:PARTY[.//m:PartyRoleType='Appraiser']",
    "UAD1570": "//m:PROJECT_AMENITY",
    "UAD1572": "//m:ASSOCIATION_CHARGE[m:ASSOCIATION_CHARGE_DETAIL/m:AssociationChargeType='AssociationDues']",
    "UAD1577": "//m:ASSOCIATION_CHARGE[m:ASSOCIATION_CHARGE_DETAIL/m:AssociationChargeType='AssociationSpecialAssessment']",
    "UAD1624": "//m:DEFECT_DETAIL[m:DefectItemRecommendedActionType='Repair']",
    "UAD1638": "//m:MARKET_INVENTORY[m:MarketInventoryType='ActiveListings']",
    "UAD1641": "//m:MARKET_INVENTORY[m:MarketInventoryType='PendingSales']",
    "UAD1650": "//m:MARKET_INVENTORY[m:MarketInventoryType='TotalSales']",
    "UAD1694": "//m:PROPERTY_UNIT_DETAIL[m:AccessoryDwellingUnitIndicator='false']",
    "UAD1732": "//m:DEFECT_DETAIL[m:DefectItemRecommendedActionType='Inspection']",
    "UAD1763": "//m:VALUATION_COMMENTARY[m:ValuationAnalysisCategoryType='ComparableRental' and m:ValuationCommentText]",
    "UAD1764": "//m:PROPERTY_UNIT",
}

# Applicability is independent of the required structure. These guards retain
# the source rule's condition after the required structure is removed.
APPLICABILITY_XPATHS = {
    "UAD1030": "//m:AllPropertyRightsAppraisedIndicator[.='false']",
    "UAD1038": "//m:SpecialTaxAssessmentsIndicator[.='true']",
    "UAD1121": "//m:MANUFACTURED_HOME_MODIFICATIONS",
    "UAD1123": "//m:SkirtingExistsIndicator[.='true']",
    "UAD1214": "//m:IncomeApproachIndicator[.='true']",
    "UAD1217": "//m:RentScheduleIndicator[.='true']",
    "UAD1238": "//m:SiteValuationMethodType[.='SalesComparison']",
    "UAD1278": "//m:BODY_OF_WATER[.//m:PrivateAccessIndicator='true']",
    "UAD1280": "//m:PROPERTY[@ValuationUseType='GrossRentMultiplierComparable']",
    "UAD1284": "//m:ManufacturedHomeHUDCertificateLabelIndicator[.='true']",
    "UAD1285": "//m:ManufacturedHomeHUDDataPlateAttachedIndicator[.='true']",
    "UAD1287": "//m:EncumbranceType[.='ConditionsCovenantsRestrictions']",
    "UAD1289": "//m:EASEMENTS",
    "UAD1292": "//m:ENCROACHMENTS",
    "UAD1299": "//m:ParcelsContiguousIndicator[.='false']",
    "UAD1310": "//m:PropertyMixedUsageIndicator[.='true']",
    "UAD1320": "//m:DRAINAGE_IMPACT_REASONS",
    "UAD1331": "//m:BODIES_OF_WATER",
    "UAD1335": "//m:WATER_FRONT_FEATURES",
    "UAD1352": "//m:SITE_UTILITY_SERVICES",
    "UAD1355": "//m:SITE_UTILITY_SERVICES",
    "UAD1357": "//m:SITE_UTILITY_SERVICES",
    "UAD1370": "//m:ZONING_ILLEGAL_REASONS",
    "UAD1374": "//m:HazardZoneType[.!='None']",
    "UAD1375": "//m:HazardZoneType[.!='None']",
    "UAD1377": "//m:SiteZoningComplianceType[.!='Legal']",
    "UAD1378": "//m:SiteZoningComplianceType[.!='Legal']",
    "UAD1398": "//m:CONDITION_COVENANT_RESTRICTIONS",
    "UAD1400": "//m:EASEMENTS",
    "UAD1520": "//m:PropertyDataReportIndicator[.='true']",
    "UAD1534": "//m:PARTY[.//m:PartyRoleType='Appraiser' and .//m:AppraiserLicenseType[.='None' or .='TraineeAppraiser']]",
    "UAD1603": "//m:PROJECT_COMPONENTS",
    "UAD1622": "//m:RenewableEnergyComponentExistsIndicator[.='true']",
    "UAD1732": "//m:PropertyValuationConditionalConclusionType[.='SubjectToInspection']",
    "UAD1763": "//m:RentScheduleIndicator[.='true']",
}

DERIVED_APPLICABILITY_VALUES = {}

NS = {"m": "http://www.mismo.org/residential/2009/schemas"}


def literal(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return json.dumps(value or "", ensure_ascii=False)


def default_target_xpath(row):
    element = row["Primary Data Element"]
    if element.startswith("@"):
        return "//@" + element[1:]
    return "//m:" + element


def expected_location(row):
    parts = row[" xPath"].removeprefix("../").strip("/").split("/")
    element = row["Primary Data Element"]
    if element and parts[-1] != element:
        parts.append(element)
    location = "//" + "/".join("m:" + part for part in parts)
    if element.startswith("@"):
        location = location.rsplit("/m:@", 1)[0] + "/" + element
    return location


def source_fingerprint(row):
    return hashlib.sha256(json.dumps(
        [row.get(key) for key in SOURCE_COLUMNS],
        ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def candidate_files():
    patterns = (
        "examples/xml/*.xml",
        "data/uad36-test-suite/tests/fixtures/single_equality/derived/*.xml",
        "data/uad36-test-suite/tests/fixtures/required_data/baseline/*.xml",
    )
    return [
        Path(path)
        for pattern in patterns
        for path in sorted(glob.glob(str(ROOT / pattern)))
    ]


def executable_bindings(source):
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    schema_path = ROOT / (
        "chatgpt-sources/sources/schemas/UAD/GSE_UAD_3.6.0_v1.3/"
        "Combined/GSE_UAD_3.6.0_v1.3.xsd"
    )
    schema = etree.XMLSchema(etree.parse(str(schema_path), parser))
    documents = []
    for path in candidate_files():
        root = etree.parse(str(path), parser).getroot()
        if schema.validate(root):
            documents.append((path, root))

    bindings = {}
    for rule_id, row in source.items():
        target = TARGET_XPATHS.get(rule_id, default_target_xpath(row))
        applicability = APPLICABILITY_XPATHS.get(rule_id, "")
        selected = None
        for path, root in documents:
            if (
                root.getroottree().xpath(target, namespaces=NS)
                and (
                    not applicability
                    or root.getroottree().xpath(applicability, namespaces=NS)
                )
            ):
                selected = (path, root)
                break
        if selected is None and rule_id in DERIVED_APPLICABILITY_VALUES:
            mutation_xpath, mutation_value = DERIVED_APPLICABILITY_VALUES[rule_id]
            for path, root in documents:
                if not root.getroottree().xpath(target, namespaces=NS):
                    continue
                derived = copy.deepcopy(root)
                mutations = derived.getroottree().xpath(
                    mutation_xpath, namespaces=NS
                )
                if not mutations:
                    continue
                for mutation in mutations:
                    mutation.text = mutation_value
                if not schema.validate(derived):
                    continue
                derived_path = OUTPUT.parent / "derived" / f"{rule_id}.xml"
                derived_path.parent.mkdir(parents=True, exist_ok=True)
                derived_path.write_bytes(
                    etree.tostring(
                        derived,
                        encoding="utf-8",
                        xml_declaration=True,
                    )
                )
                selected = (derived_path, derived)
                break
        if selected is None:
            raise ValueError(f"No positive XML fixture for {rule_id}: {target}")

        path, root = selected
        negative = copy.deepcopy(root)
        targets = negative.getroottree().xpath(target, namespaces=NS)
        if not all(isinstance(node, etree._Element) for node in targets):
            raise ValueError(f"{rule_id}: target must select removable elements")
        for node in targets:
            node.getparent().remove(node)
        if applicability and not negative.getroottree().xpath(
            applicability, namespaces=NS
        ):
            raise ValueError(
                f"{rule_id}: applicability guard does not survive removal"
            )
        bindings[rule_id] = {
            "baselinePath": path.relative_to(ROOT).as_posix(),
            "requiredStructureXPath": target,
            "expectedDataLocation": expected_location(row),
            "xsdValidAfterRemoval": schema.validate(negative),
            "applicabilityXPath": applicability,
        }
    return bindings


def main():
    tracking = Graph().parse(TRACKING, format="turtle")
    members = sorted(
        set(tracking.objects(SCENARIO, T.coversRule)), key=str
    )
    rule_ids = [str(member).rsplit(":", 1)[-1] for member in members]
    if len(rule_ids) != 98 or len(set(rule_ids)) != 98:
        raise ValueError("Required-structure inventory must contain 98 rules")

    with RULES.open(encoding="utf-8-sig", newline="") as stream:
        source = {
            row["Message ID"]: row for row in csv.DictReader(stream)
            if row["Message ID"] in rule_ids
        }
    missing = sorted(set(rule_ids) - set(source))
    if missing:
        raise ValueError("Missing governed source rows: " + ", ".join(missing))
    reviewed_bindings = executable_bindings(source)

    lines = [
        "@prefix case: <urn:uad36:test-case:IT-1R3S1:> .",
        "@prefix suite: <urn:uad36:test-suite:> .",
        "@prefix t: <urn:uad36:test-suite:vocab:> .",
        "",
        "suite:required-structures a t:TestSuite ;",
        "    t:category <urn:uad36:work-tracking:scenario:required_structures> ;",
        "    t:categoryInventoryPath "
        + literal("data/spreadsheet-rule-category-tracking.ttl")
        + " ;",
        "    t:hasCase "
        + ",\n        ".join(f"case:{rule_id}" for rule_id in rule_ids)
        + " ;",
        "    t:ruleInventoryPath " + literal("data/data-constraints.csv") + " ;",
        "    t:scenarioId " + literal("IT-1R3S1") + " .",
        "",
    ]

    for member, rule_id in zip(members, rule_ids):
        row = source[rule_id]
        statements = ["a t:TestCase"]
        for source_name, predicate in SOURCE_FIELDS.items():
            statements.append(f"t:{predicate} {literal(row[source_name])}")
        statements.append(f"t:sourceRule <{member}>")
        for unique_id in filter(
            None, (part.strip() for part in row["Unique ID"].split(";"))
        ):
            statements.append(f"t:uniqueId {literal(unique_id)}")
        for predicate, value in reviewed_bindings[rule_id].items():
            value_text = literal(value)
            statements.append(f"t:{predicate} {value_text}")

        lines.append(f"case:{rule_id} " + " ;\n    ".join(statements) + " .")
        lines.append("")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")

    production = [
        "@prefix b: <urn:uad36:required-structure-binding:> .",
        "",
    ]
    for rule_id in rule_ids:
        row = source[rule_id]
        binding = reviewed_bindings[rule_id]
        production.extend([
            f"<urn:uad36:required-structure-rule:{rule_id}> a b:Binding ;",
            "    b:applicabilityXPath "
            f"{literal(binding['applicabilityXPath'])} ;",
            f"    b:element {literal(row['Primary Data Element'])} ;",
            "    b:expectedDataLocation "
            f"{literal(binding['expectedDataLocation'])} ;",
            f"    b:requiredStructureXPath {literal(binding['requiredStructureXPath'])} ;",
            f"    b:ruleId {literal(rule_id)} ;",
            f"    b:sourceFingerprint {literal(source_fingerprint(row))} .",
            "",
        ])
    PRODUCTION_OUTPUT.write_text(
        "\n".join(production), encoding="utf-8", newline="\n"
    )


if __name__ == "__main__":
    main()
