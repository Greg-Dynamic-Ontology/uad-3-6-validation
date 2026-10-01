"""Generate the IT-1R6S1 RDF suite from governed numeric-bound rows."""

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
OUTPUT_DIR = ROOT / "data/uad36-test-suite/tests/fixtures/numeric_bounds"
OUTPUT = OUTPUT_DIR / "test-suite.ttl"
PRODUCTION_OUTPUT = ROOT / "data/numeric-bound-bindings.ttl"
SCHEMA = ROOT / (
    "chatgpt-sources/sources/schemas/UAD/GSE_UAD_3.6.0_v1.3/"
    "Combined/GSE_UAD_3.6.0_v1.3.xsd"
)
WT = Namespace("urn:uad36:work-tracking:vocab:")
SCENARIO = URIRef("urn:uad36:work-tracking:scenario:numeric_bounds")
MISMO = "http://www.mismo.org/residential/2009/schemas"
NS = {"m": MISMO}
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


def example(name):
    return f"examples/xml/{name}"


SF1 = example("SF1_Appraisal_v1.4.xml")
CONDO1 = example("Condo1_Appraisal_v1.4.xml")
MH1 = example("MH1_Appraisal_v1.4.xml")
MH2 = example("MH2_Appraisal_v1.4.xml")
MULTI = example("2- to 4-unit_Appraisal_v1.4.xml")
DERIVED = "data/uad36-test-suite/tests/fixtures/numeric_bounds/baseline"


def binding(path, xpath, allowed, outside):
    return {
        "baselinePath": path,
        "mutationMode": "replace-text",
        "mutationXPath": xpath,
        "allowedValue": allowed,
        "outsideValue": outside,
        "expectedViolationKind": "NumericBoundViolation",
        "expectedDataLocation": xpath,
    }


BINDINGS = {
    "UAD1014": binding(SF1, "//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:PROPERTY_DETAIL/m:DwellingCount", "1", "0"),
    "UAD1018": binding(SF1, "//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:PROPERTY_DETAIL/m:LivingUnitExcludingADUCount", "1", "0"),
    "UAD1052": binding(SF1, "//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:IMPROVEMENT_DETAIL[m:ImprovementType='Dwelling']/m:PropertyStructureBuiltYear", "2004", "1799"),
    "UAD1085": binding(SF1, "//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:IMPROVEMENT[m:IMPROVEMENT_DETAIL/m:ImprovementType='Dwelling']//m:STRUCTURE_DETAIL/m:LivingUnitCount", "1", "0"),
    "UAD1111": binding(MH1, "//m:MANUFACTURED_HOME_DETAIL/m:ManufacturedHomeManufactureDate", "2019-01-15", "1975-12-31"),
    "UAD1197": binding(CONDO1, "//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:SALES_HISTORY/m:OwnershipTransferTransactionAmount", "700000", "-1"),
    "UAD1233": binding(MH2, "//m:IMPROVEMENT_DEPRECIATION/m:DepreciationTotalAmount", "17710", "-1"),
    "UAD1234": binding(f"{DERIVED}/UAD1234.xml", "//m:IMPROVEMENT_DEPRECIATION/m:DepreciationExternalAmount", "0", "-1"),
    "UAD1235": binding(f"{DERIVED}/UAD1235.xml", "//m:IMPROVEMENT_DEPRECIATION/m:DepreciationFunctionalAmount", "0", "-1"),
    "UAD1236": binding(f"{DERIVED}/UAD1236.xml", "//m:IMPROVEMENT_DEPRECIATION/m:DepreciationPhysicalAmount", "0", "-1"),
    "UAD1248": binding(MULTI, "(//m:PROPERTY[@ValuationUseType='GrossRentMultiplierComparable']//m:PROPERTY_DETAIL/m:LivingUnitExcludingADUCount)[1]", "2", "0"),
    "UAD1263": binding(SF1, "//m:VALUATION_RECONCILIATION_SUMMARY_DETAIL/m:OpinionOfValueAmount", "491000", "0"),
    "UAD1264": binding(SF1, "//m:VALUATION_RECONCILIATION_SUMMARY_DETAIL/m:OpinionOfValueAmount", "491000", "1000000001"),
    "UAD1418": binding(SF1, "(//m:PROPERTY[@ValuationUseType='SalesComparable']//m:IMPROVEMENT_DETAIL[m:ImprovementType='Dwelling']/m:PropertyStructureBuiltYear)[1]", "2004", "1799"),
    "UAD1442": binding(SF1, "(//m:PROPERTY[@ValuationUseType='SalesComparable']//m:SALES_HISTORY/m:OwnershipTransferTransactionAmount)[1]", "460000", "-1"),
    "UAD1472": binding(SF1, "(//m:PROPERTY[@ValuationUseType='SalesComparable']//m:PROPERTY_DETAIL/m:DwellingCount)[1]", "1", "0"),
    "UAD1475": binding(SF1, "(//m:PROPERTY[@ValuationUseType='SalesComparable']//m:PROPERTY_DETAIL/m:LivingUnitExcludingADUCount)[1]", "1", "0"),
    "UAD1631": binding(SF1, "//m:MARKET_INVENTORY[m:MarketInventoryType='ActiveListings']/m:MarketInventoryHighestPriceAmount", "445000", "0"),
    "UAD1633": binding(SF1, "//m:MARKET_INVENTORY[m:MarketInventoryType='ActiveListings']/m:MarketInventoryLowestPriceAmount", "435000", "0"),
    "UAD1636": binding(SF1, "//m:MARKET_INVENTORY[m:MarketInventoryType='ActiveListings']/m:MarketInventoryMedianPriceAmount", "440000", "0"),
    "UAD1644": binding(SF1, "//m:MARKET_INVENTORY[m:MarketInventoryType='TotalSales']/m:MarketInventoryHighestPriceAmount", "597000", "0"),
    "UAD1646": binding(SF1, "//m:MARKET_INVENTORY[m:MarketInventoryType='TotalSales']/m:MarketInventoryLowestPriceAmount", "400000", "0"),
    "UAD1648": binding(SF1, "//m:MARKET_INVENTORY[m:MarketInventoryType='TotalSales']/m:MarketInventoryMedianPriceAmount", "499000", "0"),
    "UAD1745": binding(MULTI, "(//m:PROPERTY[@ValuationUseType='GrossRentMultiplierComparable']//m:SALES_HISTORY/m:OwnershipTransferTransactionAmount)[1]", "265000", "-1"),
}


def policy(selection, operator, threshold, value_type="decimal", applicability=""):
    return {
        "selectionXPath": selection,
        "comparisonOperator": operator,
        "thresholdValue": threshold,
        "valueType": value_type,
        "applicabilityXPath": applicability,
    }


COST_APPROACH_TRUE = (
    "//m:SCOPE_OF_WORK_DETAIL/"
    "m:CostApproachIndicator[normalize-space(.)='true']"
)
PRODUCTION_POLICIES = {
    "UAD1014": policy("//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:PROPERTY_DETAIL/m:DwellingCount", "lt", "1"),
    "UAD1018": policy("//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:PROPERTY_DETAIL/m:LivingUnitExcludingADUCount", "lt", "1"),
    "UAD1052": policy("//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:IMPROVEMENT_DETAIL[m:ImprovementType='Dwelling']/m:PropertyStructureBuiltYear", "lt", "1800"),
    "UAD1085": policy("//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:IMPROVEMENT[m:IMPROVEMENT_DETAIL/m:ImprovementType='Dwelling']//m:STRUCTURE_DETAIL/m:LivingUnitCount", "eq", "0"),
    "UAD1111": policy("//m:MANUFACTURED_HOME_DETAIL/m:ManufacturedHomeManufactureDate", "lt", "1976-01-01", "date"),
    "UAD1197": policy("//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:SALES_HISTORY/m:OwnershipTransferTransactionAmount", "lt", "0"),
    "UAD1233": policy("//m:IMPROVEMENT_DEPRECIATION/m:DepreciationTotalAmount", "lt", "0", applicability=COST_APPROACH_TRUE),
    "UAD1234": policy("//m:IMPROVEMENT_DEPRECIATION/m:DepreciationExternalAmount", "lt", "0", applicability=COST_APPROACH_TRUE),
    "UAD1235": policy("//m:IMPROVEMENT_DEPRECIATION/m:DepreciationFunctionalAmount", "lt", "0", applicability=COST_APPROACH_TRUE),
    "UAD1236": policy("//m:IMPROVEMENT_DEPRECIATION/m:DepreciationPhysicalAmount", "lt", "0", applicability=COST_APPROACH_TRUE),
    "UAD1248": policy("//m:PROPERTY[@ValuationUseType='GrossRentMultiplierComparable']//m:PROPERTY_DETAIL/m:LivingUnitExcludingADUCount", "lt", "1"),
    "UAD1263": policy("//m:VALUATION_RECONCILIATION_SUMMARY_DETAIL/m:OpinionOfValueAmount", "lt", "1"),
    "UAD1264": policy("//m:VALUATION_RECONCILIATION_SUMMARY_DETAIL/m:OpinionOfValueAmount", "gt", "1000000000"),
    "UAD1418": policy("//m:PROPERTY[@ValuationUseType='SalesComparable']//m:IMPROVEMENT_DETAIL[m:ImprovementType='Dwelling']/m:PropertyStructureBuiltYear", "lt", "1800"),
    "UAD1442": policy("//m:PROPERTY[@ValuationUseType='SalesComparable']//m:SALES_HISTORY/m:OwnershipTransferTransactionAmount", "lt", "0"),
    "UAD1472": policy("//m:PROPERTY[@ValuationUseType='SalesComparable']//m:PROPERTY_DETAIL/m:DwellingCount", "lt", "1"),
    "UAD1475": policy("//m:PROPERTY[@ValuationUseType='SalesComparable']//m:PROPERTY_DETAIL/m:LivingUnitExcludingADUCount", "lt", "1"),
    "UAD1631": policy("//m:MARKET_INVENTORY[m:MarketInventoryType='ActiveListings']/m:MarketInventoryHighestPriceAmount", "le", "0"),
    "UAD1633": policy("//m:MARKET_INVENTORY[m:MarketInventoryType='ActiveListings']/m:MarketInventoryLowestPriceAmount", "le", "0"),
    "UAD1636": policy("//m:MARKET_INVENTORY[m:MarketInventoryType='ActiveListings']/m:MarketInventoryMedianPriceAmount", "le", "0"),
    "UAD1644": policy("//m:MARKET_INVENTORY[m:MarketInventoryType='TotalSales']/m:MarketInventoryHighestPriceAmount", "le", "0"),
    "UAD1646": policy("//m:MARKET_INVENTORY[m:MarketInventoryType='TotalSales']/m:MarketInventoryLowestPriceAmount", "le", "0"),
    "UAD1648": policy("//m:MARKET_INVENTORY[m:MarketInventoryType='TotalSales']/m:MarketInventoryMedianPriceAmount", "le", "0"),
    "UAD1745": policy("//m:PROPERTY[@ValuationUseType='GrossRentMultiplierComparable']//m:SALES_HISTORY/m:OwnershipTransferTransactionAmount", "lt", "0"),
}


def literal(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return json.dumps(value or "", ensure_ascii=False)


def source_fingerprint(row):
    return hashlib.sha256(
        json.dumps(
            [row.get(key) for key in SOURCE_FIELDS],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def write_depreciation_baselines(parser, schema):
    source = etree.parse(str(ROOT / MH2), parser).getroot()
    total = source.xpath(
        "//m:IMPROVEMENT_DEPRECIATION/m:DepreciationTotalAmount",
        namespaces=NS,
    )
    if len(total) != 1:
        raise ValueError("Expected one depreciation total in the MH2 sample")
    for rule_id, local_name in {
        "UAD1234": "DepreciationExternalAmount",
        "UAD1235": "DepreciationFunctionalAmount",
        "UAD1236": "DepreciationPhysicalAmount",
    }.items():
        root = copy.deepcopy(source)
        anchor = root.xpath(
            "//m:IMPROVEMENT_DEPRECIATION/m:DepreciationTotalAmount",
            namespaces=NS,
        )[0]
        node = etree.Element(f"{{{MISMO}}}{local_name}")
        node.text = "0"
        anchor.addprevious(node)
        schema.assertValid(root)
        destination = ROOT / BINDINGS[rule_id]["baselinePath"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(
            etree.tostring(
                root,
                encoding="utf-8",
                xml_declaration=True,
                pretty_print=True,
            )
        )


def main():
    tracking = Graph().parse(TRACKING, format="turtle")
    members = sorted(
        set(tracking.objects(SCENARIO, WT.coversRule)), key=str
    )
    rule_ids = [str(member).rsplit(":", 1)[-1] for member in members]
    if len(rule_ids) != 24 or len(set(rule_ids)) != 24:
        raise ValueError("Numeric-bound inventory must contain 24 rules")
    if set(rule_ids) != set(BINDINGS):
        raise ValueError(
            "Bindings do not match governed category: "
            f"missing={sorted(set(rule_ids) - set(BINDINGS))}, "
            f"extra={sorted(set(BINDINGS) - set(rule_ids))}"
        )
    if set(rule_ids) != set(PRODUCTION_POLICIES):
        raise ValueError("Production policies do not match governed category")

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
    write_depreciation_baselines(parser, schema)
    reviewed = {}
    for rule_id in rule_ids:
        values = dict(BINDINGS[rule_id])
        path = ROOT / values["baselinePath"]
        root = etree.parse(str(path), parser).getroot()
        schema.assertValid(root)
        targets = root.getroottree().xpath(
            values["mutationXPath"], namespaces=NS
        )
        if len(targets) != 1 or not isinstance(targets[0], etree._Element):
            raise ValueError(f"{rule_id}: expected one element target")
        if targets[0].text != values["allowedValue"]:
            raise ValueError(
                f"{rule_id}: expected allowed value {values['allowedValue']!r}, "
                f"found {targets[0].text!r}"
            )
        negative = copy.deepcopy(root)
        negative_target = negative.getroottree().xpath(
            values["mutationXPath"], namespaces=NS
        )[0]
        negative_target.text = values["outsideValue"]
        values["xsdValidAfterMutation"] = schema.validate(negative)
        reviewed[rule_id] = values

    lines = [
        "@prefix case: <urn:uad36:test-case:IT-1R6S1:> .",
        "@prefix suite: <urn:uad36:test-suite:> .",
        "@prefix t: <urn:uad36:test-suite:vocab:> .",
        "",
        "suite:numeric-bounds a t:TestSuite ;",
        "    t:category <urn:uad36:work-tracking:scenario:numeric_bounds> ;",
        "    t:hasCase "
        + ",\n        ".join(f"case:{rule_id}" for rule_id in rule_ids)
        + " ;",
        '    t:ruleInventoryPath "data/data-constraints.csv" ;',
        '    t:scenarioId "IT-1R6S1" .',
        "",
    ]
    for member, rule_id in zip(members, rule_ids):
        row = source[rule_id]
        statements = ["a t:TestCase"]
        for source_name, predicate in SOURCE_FIELDS.items():
            statements.append(f"t:{predicate} {literal(row[source_name])}")
        statements.append(f"t:sourceRule <{member}>")
        for predicate, value in reviewed[rule_id].items():
            statements.append(f"t:{predicate} {literal(value)}")
        lines.append(
            f"case:{rule_id} " + " ;\n    ".join(statements) + " ."
        )
        lines.append("")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")

    production = ["@prefix b: <urn:uad36:numeric-bound-binding:> .", ""]
    for rule_id in rule_ids:
        row = source[rule_id]
        test_binding = reviewed[rule_id]
        configured = PRODUCTION_POLICIES[rule_id]
        statements = [
            "a b:Binding",
            f"b:applicabilityXPath {literal(configured['applicabilityXPath'])}",
            f"b:comparisonOperator {literal(configured['comparisonOperator'])}",
            f"b:element {literal(row['Primary Data Element'])}",
            "b:expectedDataLocation "
            f"{literal(test_binding['expectedDataLocation'])}",
            f"b:ruleId {literal(rule_id)}",
            f"b:selectionXPath {literal(configured['selectionXPath'])}",
            f"b:sourceFingerprint {literal(source_fingerprint(row))}",
            f"b:thresholdValue {literal(configured['thresholdValue'])}",
            f"b:valueType {literal(configured['valueType'])}",
            'b:violationKind "NumericBoundViolation"',
        ]
        production.append(
            f"<urn:uad36:numeric-bound-rule:{rule_id}> "
            + " ;\n    ".join(statements)
            + " ."
        )
        production.append("")
    PRODUCTION_OUTPUT.write_text(
        "\n".join(production), encoding="utf-8", newline="\n"
    )


if __name__ == "__main__":
    main()
