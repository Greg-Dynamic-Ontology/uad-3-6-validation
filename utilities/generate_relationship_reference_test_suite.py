"""Generate the IT-1R9S1 RDF suite from governed relationship rows."""

import copy
import csv
import hashlib
import json
from pathlib import Path

from lxml import etree
from rdflib import Graph, Namespace, URIRef


ROOT = Path(__file__).resolve().parents[1]
TRACKING = ROOT / "data/spreadsheet-rule-category-tracking.ttl"
RULES = ROOT / "data/data-constraints.csv"
OUTPUT = ROOT / (
    "data/uad36-test-suite/tests/fixtures/relationship_reference_integrity/"
    "test-suite.ttl"
)
PRODUCTION_OUTPUT = ROOT / "data/relationship-reference-bindings.ttl"
DERIVED = OUTPUT.parent / "derived"
SCHEMA = ROOT / (
    "chatgpt-sources/sources/schemas/UAD/GSE_UAD_3.6.0_v1.3/"
    "Combined/GSE_UAD_3.6.0_v1.3.xsd"
)
WT = Namespace("urn:uad36:work-tracking:vocab:")
SCENARIO = URIRef(
    "urn:uad36:work-tracking:scenario:relationship_reference_integrity"
)
NS = {
    "m": "http://www.mismo.org/residential/2009/schemas",
    "xlink": "http://www.w3.org/1999/xlink",
}
X = "{http://www.w3.org/1999/xlink}"
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
SOURCE_COLUMNS = tuple(SOURCE_FIELDS)

SF1 = "examples/xml/SF1_Appraisal_v1.4.xml"
CONDO1 = "examples/xml/Condo1_Appraisal_v1.4.xml"
MH1 = "examples/xml/MH1_Appraisal_v1.4.xml"
MULTI = "examples/xml/2- to 4-unit_Appraisal_v1.4.xml"


def literal(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return json.dumps(value or "", ensure_ascii=False)


def source_fingerprint(row):
    return hashlib.sha256(
        json.dumps(
            [row.get(key) for key in SOURCE_COLUMNS],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def relationship_xpath(arcrole=None, source=None, target=None):
    clauses = []
    if arcrole:
        clauses.append(f"@xlink:arcrole='{arcrole}'")
    if source:
        clauses.append(f"@xlink:from='{source}'")
    if target:
        clauses.append(f"@xlink:to='{target}'")
    predicate = " and ".join(clauses)
    return "//m:RELATIONSHIP" + (f"[{predicate}]" if predicate else "")


def arcrole(name):
    return "urn:fdc:mismo.org:2009:residential/" + name


def binding(baseline, xpath, mode="remove-relationships", kind=None):
    kinds = {
        "remove-relationships": "MissingRequiredRelationship",
        "duplicate-relationship": "DuplicateRelationship",
        "replace-from": "UnresolvedRelationshipSource",
        "replace-to": "UnresolvedRelationshipTarget",
    }
    return baseline, xpath, mode, kind or kinds[mode]


def reviewed_bindings():
    return {
        "UAD1183": binding(
            SF1,
            relationship_xpath(
                arcrole("DATA_SOURCE_IsDataSourceFor_PROPERTY_UNIT_AREA"),
                target="PROPERTY_UNIT_AREA_SubjectPropertyArea",
            ),
        ),
        "UAD1199": binding(
            SF1,
            relationship_xpath(
                arcrole(
                    "DATA_SOURCE_IsDataSourceFor_"
                    "PriorSalesOrTransfersIndicator"
                ),
                target="PriorSalesOrTransfersIndicator_SalesComp2NoPriorSales",
            ),
        ),
        "UAD1200": binding(
            SF1,
            relationship_xpath(
                arcrole(
                    "DATA_SOURCE_IsDataSourceFor_"
                    "PriorSalesOrTransfersIndicator"
                ),
                target=(
                    "PriorSalesOrTransfersIndicator_"
                    "SubjectPropertyNoPriorSales"
                ),
            ),
        ),
        "UAD1201": binding(
            SF1,
            relationship_xpath(
                arcrole("DATA_SOURCE_IsDataSourceFor_SALES_HISTORY"),
                target="SALES_HISTORY_SalesComp1_PriorSales",
            ),
        ),
        "UAD1202": binding(
            CONDO1,
            relationship_xpath(
                arcrole("DATA_SOURCE_IsDataSourceFor_SALES_HISTORY"),
                target="SALES_HISTORY_SUBJECT",
            ),
        ),
        "UAD1209": binding(
            CONDO1,
            relationship_xpath(
                arcrole(
                    "DATA_SOURCE_IsDataSourceFor_"
                    "LISTING_INFORMATION_SUMMARY"
                ),
                target="LISTING_INFORMATION_SUMMARY_SUBJECT",
            ),
        ),
        "UAD1470": binding(
            MULTI,
            relationship_xpath(
                arcrole("PROPERTY_UNIT_IsComparableFor_PROPERTY_UNIT"),
                source="PROPERTY_UNIT_COMP1_BLDG1",
                target="PROPERTY_UNIT_BLDG1",
            ),
        ),
        "UAD1477": binding(
            SF1,
            relationship_xpath(
                arcrole("DATA_SOURCE_IsDataSourceFor_PROPERTY"),
                target="PROPERTY_SALESCOMP1",
            ),
        ),
        "UAD1614": binding(
            SF1,
            relationship_xpath(
                arcrole("DATA_SOURCE_IsDataSourceFor_PROJECT"),
                target="PROJECT_1",
            ),
        ),
        "UAD1658": binding(
            SF1,
            relationship_xpath(
                arcrole("DATA_SOURCE_IsDataSourceFor_MARKET_TREND"),
                target="MARKET_TREND_1",
            ),
        ),
        "UAD1685": binding(
            CONDO1,
            relationship_xpath(
                arcrole("DEFECT_ContainsDefectOf_AMENITY"),
                target="AMENITY_BALCONY",
            ),
        ),
        "UAD1686": binding(
            "data/uad36-test-suite/tests/fixtures/"
            "relationship_reference_integrity/derived/UAD1686.xml",
            relationship_xpath(
                arcrole("DEFECT_ContainsDefectOf_CAR_STORAGE"),
                target="CAR_STORAGE_Subject",
            ),
        ),
        "UAD1689": binding(
            SF1,
            relationship_xpath(
                arcrole("DEFECT_ContainsDefectOf_IMPROVEMENT"),
                target="IMPROVEMENT_SubjectDwelling",
            ),
        ),
        "UAD1690": binding(
            "data/uad36-test-suite/tests/fixtures/"
            "relationship_reference_integrity/derived/UAD1690.xml",
            relationship_xpath(
                arcrole("DEFECT_ContainsDefectOf_SITE"),
                target="SITE_Subject",
            ),
        ),
        "UAD1691": binding(
            SF1,
            relationship_xpath(
                arcrole("DEFECT_ContainsDefectOf_PROPERTY_UNIT"),
                target="PROPERTY_UNIT_SubjectUnit1",
            ),
        ),
        "UAD1692": binding(
            MH1,
            relationship_xpath(
                arcrole("DEFECT_ContainsDefectOf_IMPROVEMENT"),
                target="IMPROVEMENT_SUBJECTPROPERTY_BARN",
            ),
        ),
        "UAD1717": binding(
            SF1,
            "(//m:RELATIONSHIP)[1]",
            "duplicate-relationship",
        ),
        "UAD1718": binding(
            SF1,
            "(//m:RELATIONSHIP)[1]",
            "replace-from",
        ),
        "UAD1719": binding(
            SF1,
            "(//m:RELATIONSHIP)[1]",
            "replace-to",
        ),
        "UAD1747": binding(
            SF1,
            relationship_xpath(
                arcrole("INSPECTION_CompletedBy_ROLE"),
                source="INSPECTION_Appraiser",
                target="ROLE_Appraiser",
            ),
        ),
    }


def production_binding(
    mode,
    *,
    arcrole_value="",
    applicability="",
    target="",
    target_axis="to",
    other_element="",
):
    return {
        "applicabilityXPath": applicability,
        "arcrole": arcrole_value,
        "evaluationMode": mode,
        "otherEndpointElement": other_element,
        "targetAxis": target_axis,
        "targetXPath": target,
    }


def production_bindings():
    subject = "//m:PROPERTY[@ValuationUseType='SubjectProperty']"
    sales = "//m:PROPERTY[@ValuationUseType='SalesComparable']"
    return {
        "UAD1183": production_binding(
            "required-link-per-target",
            arcrole_value=arcrole(
                "DATA_SOURCE_IsDataSourceFor_PROPERTY_UNIT_AREA"
            ),
            target=subject + "//m:PROPERTY_UNIT_AREA[@xlink:label]",
            other_element="DATA_SOURCE",
        ),
        "UAD1199": production_binding(
            "required-link-per-target",
            arcrole_value=arcrole(
                "DATA_SOURCE_IsDataSourceFor_"
                "PriorSalesOrTransfersIndicator"
            ),
            target=(
                sales
                + "//m:PriorSalesOrTransfersIndicator[.='false']"
                "[@xlink:label]"
            ),
            other_element="DATA_SOURCE",
        ),
        "UAD1200": production_binding(
            "required-link-per-target",
            arcrole_value=arcrole(
                "DATA_SOURCE_IsDataSourceFor_"
                "PriorSalesOrTransfersIndicator"
            ),
            target=(
                subject
                + "//m:PriorSalesOrTransfersIndicator[.='false']"
                "[@xlink:label]"
            ),
            other_element="DATA_SOURCE",
        ),
        "UAD1201": production_binding(
            "required-link-per-target",
            arcrole_value=arcrole("DATA_SOURCE_IsDataSourceFor_SALES_HISTORY"),
            target=(
                sales
                + "[.//m:PriorSalesOrTransfersIndicator='true']"
                "//m:SALES_HISTORY[@xlink:label]"
            ),
            other_element="DATA_SOURCE",
        ),
        "UAD1202": production_binding(
            "required-link-per-target",
            arcrole_value=arcrole("DATA_SOURCE_IsDataSourceFor_SALES_HISTORY"),
            target=(
                subject
                + "[.//m:PriorSalesOrTransfersIndicator='true']"
                "//m:SALES_HISTORY[@xlink:label]"
            ),
            other_element="DATA_SOURCE",
        ),
        "UAD1209": production_binding(
            "required-link-per-target",
            arcrole_value=arcrole(
                "DATA_SOURCE_IsDataSourceFor_LISTING_INFORMATION_SUMMARY"
            ),
            target=(
                subject
                + "[.//m:ListedWithinPreviousYearIndicator='false']"
                "//m:LISTING_INFORMATION_SUMMARY[@xlink:label]"
            ),
            other_element="DATA_SOURCE",
        ),
        "UAD1470": production_binding(
            "required-link-per-target",
            arcrole_value=arcrole(
                "PROPERTY_UNIT_IsComparableFor_PROPERTY_UNIT"
            ),
            target=(
                sales
                + "[.//m:LivingUnitExcludingADUCount > 1 or "
                ".//m:AccessoryDwellingUnitTotalCount > 0]"
                "//m:PROPERTY_UNIT[@xlink:label]"
            ),
            target_axis="from",
            other_element="PROPERTY_UNIT",
        ),
        "UAD1477": production_binding(
            "required-link-per-target",
            arcrole_value=arcrole("DATA_SOURCE_IsDataSourceFor_PROPERTY"),
            applicability="//m:SalesComparisonApproachIndicator[.='true']",
            target=sales + "[@xlink:label]",
            other_element="DATA_SOURCE",
        ),
        "UAD1614": production_binding(
            "required-link-per-target",
            arcrole_value=arcrole("DATA_SOURCE_IsDataSourceFor_PROJECT"),
            target=(
                subject
                + "[.//m:PropertyInProjectIndicator='true' or "
                ".//m:PUDIndicator='true']//m:PROJECT[@xlink:label]"
            ),
            other_element="DATA_SOURCE",
        ),
        "UAD1658": production_binding(
            "required-link-per-target",
            arcrole_value=arcrole("DATA_SOURCE_IsDataSourceFor_MARKET_TREND"),
            target=subject + "//m:MARKET_TREND[@xlink:label]",
            other_element="DATA_SOURCE",
        ),
        "UAD1685": production_binding(
            "required-link-per-target",
            arcrole_value=arcrole("DEFECT_ContainsDefectOf_AMENITY"),
            target=(
                subject
                + "[.//m:SubjectPropertyAmenitiesDefectsExistIndicator='true']"
                "//m:AMENITY[@xlink:label]"
            ),
            other_element="DEFECT",
        ),
        "UAD1686": production_binding(
            "required-link-per-target",
            arcrole_value=arcrole("DEFECT_ContainsDefectOf_CAR_STORAGE"),
            target=(
                subject
                + "[.//m:VehicleStorageDefectsExistIndicator='true']"
                "//m:CAR_STORAGE[@xlink:label]"
            ),
            other_element="DEFECT",
        ),
        "UAD1689": production_binding(
            "required-link-per-target",
            arcrole_value=arcrole("DEFECT_ContainsDefectOf_IMPROVEMENT"),
            target=(
                subject
                + "//m:IMPROVEMENT["
                "m:IMPROVEMENT_DETAIL/m:ImprovementType='Dwelling' and "
                "m:IMPROVEMENT_DETAIL/"
                "m:DwellingExteriorDefectsExistIndicator='true']"
                "[@xlink:label]"
            ),
            other_element="DEFECT",
        ),
        "UAD1690": production_binding(
            "required-link-per-target",
            arcrole_value=arcrole("DEFECT_ContainsDefectOf_SITE"),
            target=(
                subject
                + "//m:SITE[m:SITE_DETAIL/m:SiteDefectsExistIndicator='true']"
                "[@xlink:label]"
            ),
            other_element="DEFECT",
        ),
        "UAD1691": production_binding(
            "required-link-per-target",
            arcrole_value=arcrole("DEFECT_ContainsDefectOf_PROPERTY_UNIT"),
            target=(
                subject
                + "//m:PROPERTY_UNIT[m:PROPERTY_UNIT_DETAIL/"
                "m:UnitInteriorDefectsExistIndicator='true'][@xlink:label]"
            ),
            other_element="DEFECT",
        ),
        "UAD1692": production_binding(
            "required-link-per-target",
            arcrole_value=arcrole("DEFECT_ContainsDefectOf_IMPROVEMENT"),
            target=(
                subject
                + "//m:IMPROVEMENT["
                "m:IMPROVEMENT_DETAIL/m:ImprovementType='Outbuilding' and "
                "m:IMPROVEMENT_DETAIL/"
                "m:OutbuildingDefectsExistIndicator='true']"
                "[@xlink:label]"
            ),
            other_element="DEFECT",
        ),
        "UAD1717": production_binding("unique-relationship-key"),
        "UAD1718": production_binding("from-endpoint-resolves"),
        "UAD1719": production_binding("to-endpoint-resolves"),
        "UAD1747": production_binding(
            "required-link-per-target",
            arcrole_value=arcrole("INSPECTION_CompletedBy_ROLE"),
            target=(
                "//m:ROLE[.//m:PartyRoleType='Appraiser' or "
                ".//m:PartyRoleType='AppraiserSupervisor'][@xlink:label]"
            ),
            other_element="INSPECTION",
        ),
    }


def write_derived(rule_id, indicator_name, target_name, target_label, arcrole_name):
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    document = etree.parse(str(ROOT / SF1), parser)
    indicator = document.xpath(
        "(//m:PROPERTY[@ValuationUseType='SubjectProperty']"
        f"//m:{indicator_name})[1]",
        namespaces=NS,
    )
    target = document.xpath(
        "(//m:PROPERTY[@ValuationUseType='SubjectProperty']"
        f"//m:{target_name})[1]",
        namespaces=NS,
    )
    relation = document.xpath(
        "(//m:RELATIONSHIP[@xlink:arcrole="
        "'urn:fdc:mismo.org:2009:residential/"
        "DEFECT_ContainsDefectOf_IMPROVEMENT'])[1]",
        namespaces=NS,
    )
    if len(indicator) != 1 or len(target) != 1 or len(relation) != 1:
        raise ValueError(f"{rule_id}: cannot derive positive fixture")
    indicator[0].text = "true"
    target[0].set(X + "label", target_label)
    relation[0].set(X + "arcrole", arcrole(arcrole_name))
    relation[0].set(X + "to", target_label)
    schema = etree.XMLSchema(etree.parse(str(SCHEMA), parser))
    schema.assertValid(document)
    DERIVED.mkdir(parents=True, exist_ok=True)
    document.write(
        str(DERIVED / f"{rule_id}.xml"),
        encoding="utf-8",
        xml_declaration=True,
    )


def write_derived_fixtures():
    write_derived(
        "UAD1686",
        "VehicleStorageDefectsExistIndicator",
        "CAR_STORAGE",
        "CAR_STORAGE_Subject",
        "DEFECT_ContainsDefectOf_CAR_STORAGE",
    )
    write_derived(
        "UAD1690",
        "SiteDefectsExistIndicator",
        "SITE",
        "SITE_Subject",
        "DEFECT_ContainsDefectOf_SITE",
    )


def relationship_key(node):
    return (
        node.get(X + "arcrole", ""),
        node.get(X + "from", ""),
        node.get(X + "to", ""),
    )


def main():
    write_derived_fixtures()
    tracking = Graph().parse(TRACKING, format="turtle")
    members = sorted(set(tracking.objects(SCENARIO, WT.coversRule)), key=str)
    rule_ids = [str(member).rsplit(":", 1)[-1] for member in members]
    reviewed = reviewed_bindings()
    if len(rule_ids) != 20 or set(rule_ids) != set(reviewed):
        raise ValueError("Relationship/reference inventory must contain 20 rules")

    with RULES.open(encoding="utf-8-sig", newline="") as stream:
        source = {
            row["Message ID"]: row
            for row in csv.DictReader(stream)
            if row["Message ID"] in rule_ids
        }
    if set(source) != set(rule_ids):
        raise ValueError("The source CSV does not contain every governed rule")

    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    schema = etree.XMLSchema(etree.parse(str(SCHEMA), parser))
    cases = {}
    for rule_id in rule_ids:
        baseline, xpath, mode, kind = reviewed[rule_id]
        root = etree.parse(str(ROOT / baseline), parser).getroot()
        schema.assertValid(root)
        relationships = root.getroottree().xpath(xpath, namespaces=NS)
        if not relationships or not all(
            node.tag.endswith("RELATIONSHIP") for node in relationships
        ):
            raise ValueError(f"{rule_id}: no relationship mutation target")
        negative = copy.deepcopy(root)
        targets = negative.getroottree().xpath(xpath, namespaces=NS)
        if mode == "remove-relationships":
            for target in targets:
                target.getparent().remove(target)
        elif mode == "duplicate-relationship":
            if len(targets) != 1:
                raise ValueError(f"{rule_id}: duplicate needs one target")
            targets[0].addnext(copy.deepcopy(targets[0]))
        elif mode == "replace-from":
            if len(targets) != 1:
                raise ValueError(f"{rule_id}: from replacement needs one target")
            targets[0].set(X + "from", "MISSING_RELATIONSHIP_SOURCE")
        elif mode == "replace-to":
            if len(targets) != 1:
                raise ValueError(f"{rule_id}: to replacement needs one target")
            targets[0].set(X + "to", "MISSING_RELATIONSHIP_TARGET")
        else:
            raise ValueError(f"{rule_id}: unsupported mutation mode {mode}")
        cases[rule_id] = {
            "baselinePath": baseline,
            "expectedDataLocation": xpath,
            "expectedViolationKind": kind,
            "mutationMode": mode,
            "relationshipXPath": xpath,
            "xsdValidAfterMutation": schema.validate(negative),
        }

    lines = [
        "@prefix case: <urn:uad36:test-case:IT-1R9S1:> .",
        "@prefix suite: <urn:uad36:test-suite:> .",
        "@prefix t: <urn:uad36:test-suite:vocab:> .",
        "",
        "suite:relationship-reference-integrity a t:TestSuite ;",
        "    t:category "
        "<urn:uad36:work-tracking:scenario:relationship_reference_integrity> ;",
        "    t:hasCase "
        + ",\n        ".join(f"case:{rule_id}" for rule_id in rule_ids)
        + " ;",
        "    t:ruleInventoryPath \"data/data-constraints.csv\" ;",
        "    t:scenarioId \"IT-1R9S1\" .",
        "",
    ]
    for member, rule_id in zip(members, rule_ids):
        row = source[rule_id]
        statements = ["a t:TestCase"]
        for source_name, predicate in SOURCE_FIELDS.items():
            statements.append(f"t:{predicate} {literal(row[source_name])}")
        statements.append(f"t:sourceRule <{member}>")
        for predicate, value in cases[rule_id].items():
            statements.append(f"t:{predicate} {literal(value)}")
        lines.append(
            f"case:{rule_id} " + " ;\n    ".join(statements) + " ."
        )
        lines.append("")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")

    production = [
        "@prefix b: <urn:uad36:relationship-reference-binding:> .",
        "",
    ]
    governed = production_bindings()
    if set(governed) != set(rule_ids):
        raise ValueError("Production bindings do not match governed membership")
    for rule_id in rule_ids:
        row = source[rule_id]
        test_binding = cases[rule_id]
        binding = governed[rule_id]
        statements = [
            "a b:Binding",
            "b:applicabilityXPath "
            f"{literal(binding['applicabilityXPath'])}",
            f"b:arcrole {literal(binding['arcrole'])}",
            f"b:element {literal(row['Primary Data Element'])}",
            f"b:evaluationMode {literal(binding['evaluationMode'])}",
            "b:expectedDataLocation "
            f"{literal(test_binding['expectedDataLocation'])}",
            "b:otherEndpointElement "
            f"{literal(binding['otherEndpointElement'])}",
            f"b:ruleId {literal(rule_id)}",
            f"b:sourceFingerprint {literal(source_fingerprint(row))}",
            f"b:targetAxis {literal(binding['targetAxis'])}",
            f"b:targetXPath {literal(binding['targetXPath'])}",
            "b:violationKind "
            f"{literal(test_binding['expectedViolationKind'])}",
        ]
        production.append(
            f"<urn:uad36:relationship-reference-rule:{rule_id}> "
            + " ;\n    ".join(statements)
            + " ."
        )
        production.append("")
    PRODUCTION_OUTPUT.write_text(
        "\n".join(production), encoding="utf-8", newline="\n"
    )


if __name__ == "__main__":
    main()
