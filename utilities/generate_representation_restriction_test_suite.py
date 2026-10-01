"""Generate the IT-1R7S1 RDF suite from governed representation rows."""

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
OUTPUT_DIR = ROOT / (
    "data/uad36-test-suite/tests/fixtures/representation_restrictions"
)
OUTPUT = OUTPUT_DIR / "test-suite.ttl"
PRODUCTION_OUTPUT = ROOT / "data/representation-restriction-bindings.ttl"
SCHEMA = ROOT / (
    "chatgpt-sources/sources/schemas/UAD/GSE_UAD_3.6.0_v1.3/"
    "Combined/GSE_UAD_3.6.0_v1.3.xsd"
)
WT = Namespace("urn:uad36:work-tracking:vocab:")
SCENARIO = URIRef(
    "urn:uad36:work-tracking:scenario:format_precision_length"
)
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
SF3 = example("SF3_Appraisal_v1.4.xml")
SF5 = example("SF5_Appraisal_v1.2.xml")
MH1 = example("MH1_Appraisal_v1.4.xml")
DERIVED = (
    "data/uad36-test-suite/tests/fixtures/"
    "representation_restrictions/baseline"
)


def binding(path, xpath, allowed, outside):
    return {
        "baselinePath": path,
        "mutationMode": "replace-text",
        "mutationXPath": xpath,
        "allowedValue": allowed,
        "outsideValue": outside,
        "expectedViolationKind": "RepresentationRestrictionViolation",
        "expectedDataLocation": xpath,
    }


BINDINGS = {
    "UAD1005": binding(SF1, "//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:ADDRESS/m:PostalCode", "12345", "1234"),
    "UAD1196": binding(SF5, "//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:SALES_HISTORY/m:OwnershipTransferDate", "2022-10-30", "2022-10"),
    "UAD1260": binding(SF5, "//m:VALUATION_RECONCILIATION_SUMMARY_DETAIL/m:AppraisalReportEffectiveDate", "2026-01-12", "2026-01"),
    "UAD1507": binding(SF5, "(//m:SIGNATORY//m:EXECUTION_DETAIL/m:ExecutionDate)[1]", "2026-01-16", "2026-01"),
    "UAD1530": binding(SF5, "(//m:LICENSE_DETAIL/m:LicenseExpirationDate)[1]", "2027-12-31", "2027-12"),
    "UAD1721": binding(MH1, "//m:MANUFACTURED_HOME_DETAIL/m:ManufacturedHomeManufactureDate", "2019-01-15", "2019-01"),
    "UAD1723": binding(SF1, "(//m:INSPECTION_DETAIL/m:InspectionDate)[1]", "2019-09-20", "2019-09"),
    "UAD1725": binding(SF1, "//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:LISTING_INFORMATION_DETAIL/m:ListingStartDate", "2019-09-05", "2019-09"),
    "UAD1726": binding(SF1, "//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:LISTING_INFORMATION_DETAIL/m:ListingEndDate", "2019-09-17", "2019-09"),
    "UAD1727": binding(f"{DERIVED}/UAD1727.xml", "//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:PROPERTY_TAX_EXEMPTION/m:TaxAbatementsOrExemptionsExpirationDate", "2030-12", "2030"),
    "UAD1728": binding(SF1, "//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:SALES_CONTRACT_DETAIL/m:SalesContractDate", "2019-09-17", "2019-09"),
    "UAD1741": binding(f"{DERIVED}/UAD1741.xml", "//m:PROPERTY[@ValuationUseType='SubjectProperty']/m:PROPERTY_DETAIL/m:CooperativeProprietaryLeaseExpirationDate", "2050-12", "2050"),
    "UAD1742": binding(SF1, "//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:GEOSPATIAL_INFORMATION/m:LatitudeIdentifier", "25.165173", "25.1651"),
    "UAD1743": binding(SF1, "//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:GEOSPATIAL_INFORMATION/m:LongitudeIdentifier", "-51.328125", "-51.3281"),
    "UAD1744": binding(SF1, "(//m:PROPERTY[@ValuationUseType='SalesComparable']//m:SALES_HISTORY/m:OwnershipTransferDate)[1]", "2019-08-17", "2019-08"),
    "UAD1748": binding(SF1, "(//m:PROPERTY[@ValuationUseType='SalesComparable']//m:GEOSPATIAL_INFORMATION/m:LatitudeIdentifier)[1]", "25.165172", "25.1651"),
    "UAD1749": binding(SF1, "(//m:PROPERTY[@ValuationUseType='SalesComparable']//m:GEOSPATIAL_INFORMATION/m:LongitudeIdentifier)[1]", "-51.328126", "-51.3281"),
    "UAD1755": binding(SF5, "//m:RECONSIDERATION_OF_VALUE/m:ReconsiderationOfValueResultDate", "2026-01-16", "2026-01"),
    "UAD1765": binding(f"{DERIVED}/UAD1765.xml", "//m:VALUATION_COMMENTARY[m:ValuationAnalysisCategoryType='HazardZones']/m:ValuationCommentText", "A" * 140, "A" * 141),
    "UAD1766": binding(f"{DERIVED}/UAD1766.xml", "//m:VALUATION_COMMENTARY[m:ValuationAnalysisCategoryType='Project']/m:ValuationCommentText", "A" * 210, "A" * 211),
    "UAD1767": binding(f"{DERIVED}/UAD1767.xml", "//m:VALUATION_COMMENTARY[m:ValuationAnalysisCategoryType='PropertySpecialTaxAssessments']/m:ValuationCommentText", "A" * 540, "A" * 541),
    "UAD1768": binding(SF3, "//m:VALUATION_COMMENTARY[m:ValuationAnalysisCategoryType='SiteViews']/m:ValuationCommentText", "Pastoral with distant mountain view.", "A" * 2501),
}


def policy(
    mode,
    selection,
    *,
    pattern="",
    minimum="",
    maximum="",
    min_fraction_digits=0,
    max_length=0,
):
    return {
        "evaluationMode": mode,
        "selectionXPath": selection,
        "pattern": pattern,
        "minimumValue": minimum,
        "maximumValue": maximum,
        "minimumFractionDigits": min_fraction_digits,
        "maximumLength": max_length,
    }


FULL_DATE = r"\d{4}-\d{2}-\d{2}"
YEAR_MONTH = r"\d{4}-\d{2}"
PRODUCTION_POLICIES = {
    "UAD1005": policy("pattern", "//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:ADDRESS/m:PostalCode", pattern=r"\d{5}(?:-\d{4})?"),
    "UAD1196": policy("full-date", "//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:SALES_HISTORY/m:OwnershipTransferDate", pattern=FULL_DATE),
    "UAD1260": policy("full-date", "//m:VALUATION_RECONCILIATION_SUMMARY_DETAIL/m:AppraisalReportEffectiveDate", pattern=FULL_DATE),
    "UAD1507": policy("full-date", "//m:SIGNATORY//m:EXECUTION_DETAIL/m:ExecutionDate", pattern=FULL_DATE),
    "UAD1530": policy("full-date", "//m:LICENSE_DETAIL/m:LicenseExpirationDate", pattern=FULL_DATE),
    "UAD1721": policy("full-date", "//m:MANUFACTURED_HOME_DETAIL/m:ManufacturedHomeManufactureDate", pattern=FULL_DATE),
    "UAD1723": policy("full-date", "//m:INSPECTION_DETAIL/m:InspectionDate", pattern=FULL_DATE),
    "UAD1725": policy("full-date", "//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:LISTING_INFORMATION_DETAIL/m:ListingStartDate", pattern=FULL_DATE),
    "UAD1726": policy("full-date", "//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:LISTING_INFORMATION_DETAIL/m:ListingEndDate", pattern=FULL_DATE),
    "UAD1727": policy("year-month", "//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:PROPERTY_TAX_EXEMPTION/m:TaxAbatementsOrExemptionsExpirationDate", pattern=YEAR_MONTH),
    "UAD1728": policy("full-date", "//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:SALES_CONTRACT_DETAIL/m:SalesContractDate", pattern=FULL_DATE),
    "UAD1741": policy("year-month", "//m:PROPERTY[@ValuationUseType='SubjectProperty']/m:PROPERTY_DETAIL/m:CooperativeProprietaryLeaseExpirationDate", pattern=YEAR_MONTH),
    "UAD1742": policy("decimal-precision-range", "//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:GEOSPATIAL_INFORMATION/m:LatitudeIdentifier", minimum="-90", maximum="90", min_fraction_digits=5),
    "UAD1743": policy("decimal-precision-range", "//m:PROPERTY[@ValuationUseType='SubjectProperty']//m:GEOSPATIAL_INFORMATION/m:LongitudeIdentifier", minimum="-180", maximum="180", min_fraction_digits=5),
    "UAD1744": policy("full-date", "//m:PROPERTY[@ValuationUseType='SalesComparable']//m:SALES_HISTORY/m:OwnershipTransferDate", pattern=FULL_DATE),
    "UAD1748": policy("decimal-precision-range", "//m:PROPERTY[@ValuationUseType='SalesComparable']//m:GEOSPATIAL_INFORMATION/m:LatitudeIdentifier", minimum="-90", maximum="90", min_fraction_digits=5),
    "UAD1749": policy("decimal-precision-range", "//m:PROPERTY[@ValuationUseType='SalesComparable']//m:GEOSPATIAL_INFORMATION/m:LongitudeIdentifier", minimum="-180", maximum="180", min_fraction_digits=5),
    "UAD1755": policy("full-date", "//m:RECONSIDERATION_OF_VALUE/m:ReconsiderationOfValueResultDate", pattern=FULL_DATE),
    "UAD1765": policy("max-length", "//m:VALUATION_COMMENTARY[m:ValuationAnalysisCategoryType='HazardZones' or m:ValuationAnalysisCategoryType='PropertyNonResidentialUses']/m:ValuationCommentText", max_length=140),
    "UAD1766": policy("max-length", "//m:VALUATION_COMMENTARY[m:ValuationAnalysisCategoryType='ProjectDeveloperOrSponsorControlsProjectManagement' or m:ValuationAnalysisCategoryType='IncompleteProject' or m:ValuationAnalysisCategoryType='ProjectConversion' or m:ValuationAnalysisCategoryType='SingleEntityGreatestNumberOfUnitsOwned' or m:ValuationAnalysisCategoryType='SingleEntityGreatestNumberOfSharesOwned' or m:ValuationAnalysisCategoryType='ProjectCommercialSpace' or m:ValuationAnalysisCategoryType='ProjectLegalAction' or m:ValuationAnalysisCategoryType='ProjectSpecialAssessmentsAttributedToSubjectProperty' or m:ValuationAnalysisCategoryType='TransferFeeAttributedToSubjectProperty' or m:ValuationAnalysisCategoryType='PropertyTaxAbatementsOrExemptions' or m:ValuationAnalysisCategoryType='Project']/m:ValuationCommentText", max_length=210),
    "UAD1767": policy("max-length", "//m:VALUATION_COMMENTARY[m:ValuationAnalysisCategoryType='PropertySpecialTaxAssessments']/m:ValuationCommentText", max_length=540),
    "UAD1768": policy("max-length", "//m:VALUATION_COMMENTARY[m:ValuationAnalysisCategoryType='ProjectFactors' or m:ValuationAnalysisCategoryType='Project' or m:ValuationAnalysisCategoryType='WaterFrontages' or m:ValuationAnalysisCategoryType='SiteFeatures' or m:ValuationAnalysisCategoryType='SiteViews' or m:ValuationAnalysisCategoryType='SiteInfluences']/m:ValuationCommentText", max_length=2500),
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


def add_child(parent, local_name, text):
    node = etree.Element(f"{{{MISMO}}}{local_name}")
    node.text = text
    parent.append(node)
    return node


def write_derived_baselines(parser, schema):
    source = etree.parse(str(ROOT / SF1), parser).getroot()

    tax_root = copy.deepcopy(source)
    tax = tax_root.xpath(
        "//m:PROPERTY[@ValuationUseType='SubjectProperty']"
        "/m:PROPERTY_TAXES/m:PROPERTY_TAX",
        namespaces=NS,
    )[0]
    exemptions = add_child(tax, "PROPERTY_TAX_EXEMPTIONS", None)
    exemption = add_child(exemptions, "PROPERTY_TAX_EXEMPTION", None)
    add_child(
        exemption, "TaxAbatementsOrExemptionsExpirationDate", "2030-12"
    )
    write_derived("UAD1727", tax_root, schema)

    cooperative_root = copy.deepcopy(source)
    detail = cooperative_root.xpath(
        "//m:PROPERTY[@ValuationUseType='SubjectProperty']/m:PROPERTY_DETAIL",
        namespaces=NS,
    )[0]
    dwelling = detail.xpath("m:DwellingCount", namespaces=NS)[0]
    lease = etree.Element(
        f"{{{MISMO}}}CooperativeProprietaryLeaseExpirationDate"
    )
    lease.text = "2050-12"
    dwelling.addprevious(lease)
    write_derived("UAD1741", cooperative_root, schema)

    for rule_id, category, limit in (
        ("UAD1765", "HazardZones", 140),
        ("UAD1766", "Project", 210),
        ("UAD1767", "PropertySpecialTaxAssessments", 540),
    ):
        comment_root = copy.deepcopy(source)
        commentary = comment_root.xpath(
            "(//m:VALUATION_COMMENTARY)[1]", namespaces=NS
        )[0]
        commentary.xpath(
            "m:ValuationAnalysisCategoryType", namespaces=NS
        )[0].text = category
        commentary.xpath("m:ValuationCommentText", namespaces=NS)[0].text = (
            "A" * limit
        )
        write_derived(rule_id, comment_root, schema)


def write_derived(rule_id, root, schema):
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
    if len(rule_ids) != 22 or len(set(rule_ids)) != 22:
        raise ValueError("Representation inventory must contain 22 rules")
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
    write_derived_baselines(parser, schema)
    reviewed = {}
    for rule_id in rule_ids:
        values = dict(BINDINGS[rule_id])
        root = etree.parse(
            str(ROOT / values["baselinePath"]), parser
        ).getroot()
        schema.assertValid(root)
        targets = root.getroottree().xpath(
            values["mutationXPath"], namespaces=NS
        )
        if len(targets) != 1 or not isinstance(targets[0], etree._Element):
            raise ValueError(
                f"{rule_id}: expected one element target, found {len(targets)}"
            )
        if targets[0].text != values["allowedValue"]:
            raise ValueError(
                f"{rule_id}: allowed value does not match the baseline"
            )
        negative = copy.deepcopy(root)
        negative.getroottree().xpath(
            values["mutationXPath"], namespaces=NS
        )[0].text = values["outsideValue"]
        values["xsdValidAfterMutation"] = schema.validate(negative)
        reviewed[rule_id] = values

    lines = [
        "@prefix case: <urn:uad36:test-case:IT-1R7S1:> .",
        "@prefix suite: <urn:uad36:test-suite:> .",
        "@prefix t: <urn:uad36:test-suite:vocab:> .",
        "",
        "suite:representation-restrictions a t:TestSuite ;",
        "    t:category "
        "<urn:uad36:work-tracking:scenario:format_precision_length> ;",
        "    t:hasCase "
        + ",\n        ".join(f"case:{rule_id}" for rule_id in rule_ids)
        + " ;",
        '    t:ruleInventoryPath "data/data-constraints.csv" ;',
        '    t:scenarioId "IT-1R7S1" .',
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

    production = [
        "@prefix b: <urn:uad36:representation-restriction-binding:> .",
        "",
    ]
    for rule_id in rule_ids:
        row = source[rule_id]
        test_binding = reviewed[rule_id]
        configured = PRODUCTION_POLICIES[rule_id]
        statements = [
            "a b:Binding",
            f"b:element {literal(row['Primary Data Element'])}",
            f"b:evaluationMode {literal(configured['evaluationMode'])}",
            "b:expectedDataLocation "
            f"{literal(test_binding['expectedDataLocation'])}",
            f"b:maximumLength {configured['maximumLength']}",
            f"b:maximumValue {literal(configured['maximumValue'])}",
            f"b:minimumFractionDigits {configured['minimumFractionDigits']}",
            f"b:minimumValue {literal(configured['minimumValue'])}",
            f"b:pattern {literal(configured['pattern'])}",
            f"b:ruleId {literal(rule_id)}",
            f"b:selectionXPath {literal(configured['selectionXPath'])}",
            f"b:sourceFingerprint {literal(source_fingerprint(row))}",
            'b:violationKind "RepresentationRestrictionViolation"',
        ]
        production.append(
            f"<urn:uad36:representation-restriction-rule:{rule_id}> "
            + " ;\n    ".join(statements)
            + " ."
        )
        production.append("")
    PRODUCTION_OUTPUT.write_text(
        "\n".join(production), encoding="utf-8", newline="\n"
    )


if __name__ == "__main__":
    main()
