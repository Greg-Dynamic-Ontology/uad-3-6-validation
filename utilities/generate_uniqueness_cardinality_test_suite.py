"""Generate the IT-1R5S1 RDF suite from governed source rows."""

import copy
import csv
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as XML
from zipfile import ZipFile

from lxml import etree
from rdflib import Graph, Namespace, URIRef


ROOT = Path(__file__).resolve().parents[1]
TRACKING = ROOT / "data/spreadsheet-rule-category-tracking.ttl"
RULES = ROOT / "data/data-constraints.csv"
OUTPUT = ROOT / (
    "data/uad36-test-suite/tests/fixtures/uniqueness_cardinality/"
    "test-suite.ttl"
)
PRODUCTION_OUTPUT = ROOT / "data/uniqueness-cardinality-bindings.ttl"
SCHEMA = ROOT / (
    "chatgpt-sources/sources/schemas/UAD/GSE_UAD_3.6.0_v1.3/"
    "Combined/GSE_UAD_3.6.0_v1.3.xsd"
)
SOURCE_WORKBOOK = ROOT / (
    "chatgpt-sources/sources/constraints/FannieMae/"
    "Appendix H-1 UAD Compliance Rules - URAR.xlsm"
)
T = Namespace("urn:uad36:work-tracking:vocab:")
SCENARIO = URIRef(
    "urn:uad36:work-tracking:scenario:uniqueness_cardinality"
)
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
NS = {
    "m": "http://www.mismo.org/residential/2009/schemas",
    "xlink": "http://www.w3.org/1999/xlink",
}


def example(name):
    return f"examples/xml/{name}"


DEFAULT = example("2- to 4-unit_Appraisal_v1.4.xml")

# Each binding identifies one occurrence whose duplication creates the exact
# governed uniqueness or cardinality violation. The production validator does
# not read this test-only RDF or this generator.
BINDINGS = {
    "UAD1033": (DEFAULT, "(//m:PROPERTY[@ValuationUseType='SubjectProperty'])[1]", "CardinalityViolation"),
    "UAD1037": (DEFAULT, "(//m:VALUATION_COMMENTARY)[1]", "CardinalityViolation"),
    "UAD1092": (DEFAULT, "(//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:STRUCTURE_DETAIL[m:StructureIdentifier])[1]", "DuplicateValue"),
    "UAD1093": (DEFAULT, "(//m:PROPERTY[@ValuationUseType='SalesComparable']//m:STRUCTURE_DETAIL[m:StructureIdentifier])[1]", "DuplicateValue"),
    "UAD1171": (DEFAULT, "(//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:PROPERTY_UNIT_DETAIL[m:UnitIdentifier])[1]", "DuplicateValue"),
    "UAD1172": (DEFAULT, "(//m:PROPERTY[@ValuationUseType='SalesComparable']//m:PROPERTY_UNIT_DETAIL[m:UnitIdentifier])[1]", "DuplicateValue"),
    "UAD1223": (DEFAULT, "(//m:SERVICE_DETAIL[m:ServiceType='Valuation'])[1]", "CardinalityViolation"),
    "UAD1224": (example("Condo1_Appraisal_v1.4.xml"), "(//m:SERVICE_DETAIL[m:ServiceType='Inspection'])[1]", "CardinalityViolation"),
    "UAD1226": (example("MH1_Appraisal_v1.4.xml"), "(//m:PROPERTY[@ValuationUseType='LandComparable'])[1]", "DuplicateValue"),
    "UAD1247": (DEFAULT, "(//m:PROPERTY[@ValuationUseType='GrossRentMultiplierComparable'])[1]", "DuplicateValue"),
    "UAD1256": (DEFAULT, "(//m:VALUATION_CONDITION[m:PropertyValuationConditionalConclusionType='AsIs'])[1]", "CardinalityViolation"),
    "UAD1268": (DEFAULT, "(//m:INSPECTION[@xlink:label='INSPECTION_Appraiser']/m:INSPECTION_DETAIL)[1]", "CardinalityViolation"),
    "UAD1403": (DEFAULT, "(//m:PROPERTY[@ValuationUseType='SalesComparable']//m:LISTING_INFORMATION)[1]", "CardinalityViolation"),
    "UAD1432": (DEFAULT, "(//m:PROPERTY[@ValuationUseType='SalesComparable'])[1]", "DuplicateValue"),
    "UAD1485": (example("SF1_Appraisal_v1.4.xml"), "(//m:PROPERTY[@ValuationUseType='PropertyAnalyzedNotUsed'])[1]", "DuplicateValue"),
    "UAD1495": (DEFAULT, "(//m:PROPERTY[@ValuationUseType='RentalComparable'])[1]", "DuplicateValue"),
    "UAD1535": (DEFAULT, "(//m:SIGNATORY/m:EXECUTION/m:EXECUTION_DETAIL/m:ExecutionDate)[1]", "CardinalityViolation"),
    "UAD1637": (DEFAULT, "(//m:MARKET_INVENTORY[m:MarketInventoryType='ActiveListings'])[1]", "CardinalityViolation"),
    "UAD1640": (DEFAULT, "(//m:MARKET_INVENTORY[m:MarketInventoryType='PendingSales'])[1]", "CardinalityViolation"),
    "UAD1649": (DEFAULT, "(//m:MARKET_INVENTORY[m:MarketInventoryType='TotalSales'])[1]", "CardinalityViolation"),
    "UAD1702": (example("MH1_Appraisal_v1.4.xml"), "(//m:PROPERTY[@ValuationUseType='LandComparable']//m:SALES_HISTORY)[1]", "CardinalityViolation"),
    "UAD1703": (DEFAULT, "(//m:PROPERTY[@ValuationUseType='GrossRentMultiplierComparable']//m:SALES_HISTORY)[1]", "CardinalityViolation"),
    "UAD1704": (example("SF1_Appraisal_v1.4.xml"), "(//m:PROPERTY[@ValuationUseType='PropertyAnalyzedNotUsed']//m:SALES_HISTORY)[1]", "CardinalityViolation"),
    "UAD1722": (DEFAULT, "(//m:ROLE_DETAIL[m:PartyRoleType='Appraiser'])[1]", "CardinalityViolation"),
    "UAD1758": (DEFAULT, "(//m:PROPERTY[@ValuationUseType='SalesComparable']//m:COMPARABLE_ADJUSTMENT[m:ComparableAdjustmentType='OverallQualityRating'])[1]", "CardinalityViolation"),
    "UAD1759": (DEFAULT, "(//m:ROLE_DETAIL[m:PartyRoleType='AppraiserSupervisor'])[1]", "CardinalityViolation"),
}


SPREADSHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def workbook_rows(path, sheet_name):
    """Read one XLSX/XLSM worksheet using only the standard library."""
    with ZipFile(path) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = XML.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = [
                "".join(node.text or "" for node in item.iter(
                    f"{{{SPREADSHEET_NS}}}t"
                ))
                for item in root.findall(f"{{{SPREADSHEET_NS}}}si")
            ]

        workbook = XML.fromstring(archive.read("xl/workbook.xml"))
        sheets = workbook.find(f"{{{SPREADSHEET_NS}}}sheets")
        selected = next(
            sheet for sheet in sheets
            if sheet.get("name") == sheet_name
        )
        relationship_id = selected.get(f"{{{OFFICE_REL_NS}}}id")
        relationships = XML.fromstring(
            archive.read("xl/_rels/workbook.xml.rels")
        )
        target = next(
            relationship.get("Target")
            for relationship in relationships.findall(
                f"{{{PACKAGE_REL_NS}}}Relationship"
            )
            if relationship.get("Id") == relationship_id
        )
        worksheet_path = target.lstrip("/")
        if not worksheet_path.startswith("xl/"):
            worksheet_path = "xl/" + worksheet_path
        worksheet = XML.fromstring(archive.read(worksheet_path))

        result = []
        for row in worksheet.iter(f"{{{SPREADSHEET_NS}}}row"):
            values = {}
            for cell in row.findall(f"{{{SPREADSHEET_NS}}}c"):
                column = "".join(
                    character for character in cell.get("r", "")
                    if character.isalpha()
                )
                value_node = cell.find(f"{{{SPREADSHEET_NS}}}v")
                if cell.get("t") == "inlineStr":
                    inline = cell.find(f"{{{SPREADSHEET_NS}}}is")
                    value = "".join(
                        node.text or "" for node in inline.iter(
                            f"{{{SPREADSHEET_NS}}}t"
                        )
                    )
                elif value_node is None:
                    value = ""
                elif cell.get("t") == "s":
                    value = shared[int(value_node.text)]
                else:
                    value = value_node.text or ""
                values[column] = value
            result.append((values.get("A", ""), values.get("B", ""), values.get("C", "")))
        return result


NON_REPEATABLE_SALES_ADJUSTMENTS = tuple(
    adjustment_type
    for adjustment_type, repeatability, valuation_use in workbook_rows(
        SOURCE_WORKBOOK, "Adjustments Cardinality"
    )
    if repeatability == "Adjustment cannot repeat"
    and valuation_use == "SalesComparable"
)


def production_binding(
    mode,
    *,
    selection="",
    scope="",
    member="",
    count=1,
    violation_kind="CardinalityViolation",
    governed_values=(),
):
    return {
        "evaluationMode": mode,
        "selectionXPath": selection,
        "scopeXPath": scope,
        "memberXPath": member,
        "governedCount": count,
        "violationKind": violation_kind,
        "governedValues": governed_values,
    }


PRODUCTION_BINDINGS = {
    "UAD1033": production_binding("max-count-global", selection="//m:PROPERTY[@ValuationUseType='SubjectProperty']"),
    "UAD1037": production_binding("unique-value-global", selection="//m:VALUATION_COMMENTARY/m:ValuationAnalysisCategoryType"),
    "UAD1092": production_binding("unique-value-global", selection="//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:STRUCTURE_DETAIL/m:StructureIdentifier", violation_kind="DuplicateValue"),
    "UAD1093": production_binding("unique-value-per-scope", scope="//m:PROPERTY[@ValuationUseType='SalesComparable']", member=".//m:STRUCTURE_DETAIL/m:StructureIdentifier", violation_kind="DuplicateValue"),
    "UAD1171": production_binding("unique-value-global", selection="//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:PROPERTY_UNIT_DETAIL/m:UnitIdentifier", violation_kind="DuplicateValue"),
    "UAD1172": production_binding("unique-value-per-scope", scope="//m:PROPERTY[@ValuationUseType='SalesComparable']", member=".//m:PROPERTY_UNIT_DETAIL/m:UnitIdentifier", violation_kind="DuplicateValue"),
    "UAD1223": production_binding("exact-count-global", selection="//m:SERVICE_DETAIL[m:ServiceType='Valuation']"),
    "UAD1224": production_binding("max-count-global", selection="//m:SERVICE_DETAIL[m:ServiceType='Inspection']"),
    "UAD1226": production_binding("unique-value-global", selection="//m:PROPERTY[@ValuationUseType='LandComparable']//m:COMPARABLE_DETAIL/m:PropertyOrdinalNumber", violation_kind="DuplicateValue"),
    "UAD1247": production_binding("unique-value-global", selection="//m:PROPERTY[@ValuationUseType='GrossRentMultiplierComparable']//m:COMPARABLE_DETAIL/m:PropertyOrdinalNumber", violation_kind="DuplicateValue"),
    "UAD1256": production_binding("as-is-exclusive-per-scope", scope="//m:VALUATION_ANALYSIS", member=".//m:VALUATION_CONDITION"),
    "UAD1268": production_binding("max-count-per-scope", scope="//m:INSPECTION[contains(@xlink:label, 'Appraiser')]", member="m:INSPECTION_DETAIL"),
    "UAD1403": production_binding("max-count-per-scope", scope="//m:PROPERTY[@ValuationUseType='SalesComparable']", member=".//m:LISTING_INFORMATION"),
    "UAD1432": production_binding("unique-value-global", selection="//m:PROPERTY[@ValuationUseType='SalesComparable']//m:COMPARABLE_DETAIL/m:PropertyOrdinalNumber", violation_kind="DuplicateValue"),
    "UAD1485": production_binding("unique-value-global", selection="//m:PROPERTY[@ValuationUseType='PropertyAnalyzedNotUsed']//m:COMPARABLE_DETAIL/m:PropertyOrdinalNumber", violation_kind="DuplicateValue"),
    "UAD1495": production_binding("unique-value-global", selection="//m:PROPERTY[@ValuationUseType='RentalComparable']//m:COMPARABLE_DETAIL/m:PropertyOrdinalNumber", violation_kind="DuplicateValue"),
    "UAD1535": production_binding("exact-count-per-scope", scope="//m:SIGNATORY/m:EXECUTION/m:EXECUTION_DETAIL", member="m:ExecutionDate"),
    "UAD1637": production_binding("max-count-global", selection="//m:MARKET_INVENTORY[m:MarketInventoryType='ActiveListings']"),
    "UAD1640": production_binding("max-count-global", selection="//m:MARKET_INVENTORY[m:MarketInventoryType='PendingSales']"),
    "UAD1649": production_binding("max-count-global", selection="//m:MARKET_INVENTORY[m:MarketInventoryType='TotalSales']"),
    "UAD1702": production_binding("max-count-per-scope", scope="//m:PROPERTY[@ValuationUseType='LandComparable']", member=".//m:SALES_HISTORY"),
    "UAD1703": production_binding("max-count-per-scope", scope="//m:PROPERTY[@ValuationUseType='GrossRentMultiplierComparable']", member=".//m:SALES_HISTORY"),
    "UAD1704": production_binding("max-count-per-scope", scope="//m:PROPERTY[@ValuationUseType='PropertyAnalyzedNotUsed']", member=".//m:SALES_HISTORY"),
    "UAD1722": production_binding("max-count-global", selection="//m:ROLE_DETAIL[m:PartyRoleType='Appraiser']"),
    "UAD1758": production_binding("unique-governed-values-per-scope", scope="//m:PROPERTY[@ValuationUseType='SalesComparable']", member=".//m:COMPARABLE_ADJUSTMENT/m:ComparableAdjustmentType", governed_values=NON_REPEATABLE_SALES_ADJUSTMENTS),
    "UAD1759": production_binding("max-count-global", selection="//m:ROLE_DETAIL[m:PartyRoleType='AppraiserSupervisor']"),
}


def literal(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return json.dumps(value or "", ensure_ascii=False)


def source_fingerprint(row):
    return hashlib.sha256(json.dumps(
        [row.get(key) for key in SOURCE_COLUMNS],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def main():
    tracking = Graph().parse(TRACKING, format="turtle")
    members = sorted(set(tracking.objects(SCENARIO, T.coversRule)), key=str)
    rule_ids = [str(member).rsplit(":", 1)[-1] for member in members]
    if len(rule_ids) != 26 or len(set(rule_ids)) != 26:
        raise ValueError("Uniqueness/cardinality inventory must contain 26 rules")
    if set(rule_ids) != set(BINDINGS):
        raise ValueError(
            "Executable bindings do not match governed category: "
            f"missing={sorted(set(rule_ids) - set(BINDINGS))}, "
            f"extra={sorted(set(BINDINGS) - set(rule_ids))}"
        )

    with RULES.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    source = {row["Message ID"]: row for row in rows if row["Message ID"] in rule_ids}
    if set(source) != set(rule_ids):
        raise ValueError("The source CSV does not contain every governed rule")

    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    schema = etree.XMLSchema(etree.parse(str(SCHEMA), parser))
    reviewed = {}
    for rule_id in rule_ids:
        baseline_path, mutation_xpath, violation_kind = BINDINGS[rule_id]
        baseline = etree.parse(str(ROOT / baseline_path), parser).getroot()
        schema.assertValid(baseline)
        targets = baseline.getroottree().xpath(mutation_xpath, namespaces=NS)
        if len(targets) != 1 or not isinstance(targets[0], etree._Element):
            raise ValueError(
                f"{rule_id}: expected one element mutation target, found {len(targets)}"
            )
        negative = copy.deepcopy(baseline)
        target = negative.getroottree().xpath(mutation_xpath, namespaces=NS)[0]
        target.addnext(copy.deepcopy(target))
        reviewed[rule_id] = {
            "baselinePath": baseline_path,
            "expectedDataLocation": mutation_xpath,
            "expectedViolationKind": violation_kind,
            "mutationMode": "duplicate-node",
            "mutationXPath": mutation_xpath,
            "xsdValidAfterMutation": schema.validate(negative),
        }

    lines = [
        "@prefix case: <urn:uad36:test-case:IT-1R5S1:> .",
        "@prefix suite: <urn:uad36:test-suite:> .",
        "@prefix t: <urn:uad36:test-suite:vocab:> .",
        "",
        "suite:uniqueness-cardinality a t:TestSuite ;",
        "    t:category <urn:uad36:work-tracking:scenario:uniqueness_cardinality> ;",
        "    t:categoryInventoryPath "
        + literal("data/spreadsheet-rule-category-tracking.ttl")
        + " ;",
        "    t:hasCase "
        + ",\n        ".join(f"case:{rule_id}" for rule_id in rule_ids)
        + " ;",
        "    t:ruleInventoryPath " + literal("data/data-constraints.csv") + " ;",
        "    t:scenarioId " + literal("IT-1R5S1") + " .",
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
        for predicate, value in reviewed[rule_id].items():
            statements.append(f"t:{predicate} {literal(value)}")
        lines.append(f"case:{rule_id} " + " ;\n    ".join(statements) + " .")
        lines.append("")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")

    production = [
        "@prefix b: <urn:uad36:uniqueness-cardinality-binding:> .",
        "",
    ]
    for rule_id in rule_ids:
        row = source[rule_id]
        test_binding = reviewed[rule_id]
        binding = PRODUCTION_BINDINGS[rule_id]
        statements = [
            "a b:Binding",
            f"b:element {literal(row['Primary Data Element'])}",
            f"b:evaluationMode {literal(binding['evaluationMode'])}",
            "b:expectedDataLocation "
            f"{literal(test_binding['expectedDataLocation'])}",
            f"b:governedCount {binding['governedCount']}",
            f"b:memberXPath {literal(binding['memberXPath'])}",
            f"b:ruleId {literal(rule_id)}",
            f"b:scopeXPath {literal(binding['scopeXPath'])}",
            f"b:selectionXPath {literal(binding['selectionXPath'])}",
            f"b:sourceFingerprint {literal(source_fingerprint(row))}",
            f"b:violationKind {literal(binding['violationKind'])}",
        ]
        for governed_value in binding["governedValues"]:
            statements.append(f"b:governedValue {literal(governed_value)}")
        production.append(
            f"<urn:uad36:uniqueness-cardinality-rule:{rule_id}> "
            + " ;\n    ".join(statements)
            + " ."
        )
        production.append("")
    PRODUCTION_OUTPUT.write_text(
        "\n".join(production), encoding="utf-8", newline="\n"
    )


if __name__ == "__main__":
    main()
