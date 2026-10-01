"""Generate the IT-1R8S1 RDF test suite from governed source rows."""

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
    "data/uad36-test-suite/tests/fixtures/existing_context_required/"
    "test-suite.ttl"
)
PRODUCTION_OUTPUT = ROOT / "data/existing-context-required-bindings.ttl"
DERIVED = OUTPUT.parent / "derived"
SCHEMA = ROOT / (
    "chatgpt-sources/sources/schemas/UAD/GSE_UAD_3.6.0_v1.3/"
    "Combined/GSE_UAD_3.6.0_v1.3.xsd"
)
WT = Namespace("urn:uad36:work-tracking:vocab:")
SCENARIO = URIRef(
    "urn:uad36:work-tracking:scenario:existing_context_required"
)
NS = {"m": "http://www.mismo.org/residential/2009/schemas"}
M = "{http://www.mismo.org/residential/2009/schemas}"
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
MH1 = "examples/xml/MH1_Appraisal_v1.4.xml"
ENCROACHMENT_SOURCE = (
    "data/uad36-test-suite/tests/fixtures/single_equality/derived/UAD1293.xml"
)


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


def indexed_context(name, predicate=""):
    qualifier = f"[{predicate}]" if predicate else ""
    return (
        "(//m:PROPERTY[@ValuationUseType='SubjectProperty']"
        f"//m:{name}{qualifier})[1]"
    )


def stable_context(name):
    return (
        "//m:PROPERTY[@ValuationUseType='SubjectProperty']"
        f"//m:{name}"
    )


def bindings():
    property_context = "//m:PROPERTY"
    property_target = "(//m:PROPERTY[@ValuationUseType])[1]"
    improvement_context = stable_context("IMPROVEMENT_DETAIL")
    improvement = indexed_context("IMPROVEMENT_DETAIL", "m:ImprovementType")
    foreign_context = "//m:FOREIGN_OBJECT"
    foreign_object = "(//m:FOREIGN_OBJECT[m:ObjectURL])[1]"
    encroachment_context = stable_context("ENCROACHMENT")
    encroachment = indexed_context(
        "ENCROACHMENT", "m:EncroachmentDirectionType"
    )
    utility_context = stable_context("SITE_UTILITY_DETAIL")
    utility = indexed_context(
        "SITE_UTILITY_DETAIL", "m:SiteUtilityOwnershipType"
    )
    site_view_context = stable_context("SITE_VIEW")
    site_view = indexed_context(
        "SITE_VIEW",
        "m:ViewPrimaryIndicator and m:ViewRangeType and "
        "m:ValueMarketabilityImpactType",
    )
    commentary_context = "//m:VALUATION_COMMENTARY"
    commentary = "(//m:VALUATION_COMMENTARY[m:ValuationAnalysisCategoryType])[1]"
    inspection_context = stable_context("INSPECTION_DETAIL")
    inspection = indexed_context(
        "INSPECTION_DETAIL",
        "m:PropertyExteriorInspectionMethodType and "
        "m:PropertyInteriorInspectionMethodType",
    )
    image_context = stable_context("IMAGE")
    image = indexed_context(
        "IMAGE", "m:ImageFileLocationIdentifier and m:MIMETypeIdentifier"
    )
    defect_context = stable_context("DEFECT_DETAIL")
    defect = indexed_context(
        "DEFECT_DETAIL",
        "m:DefectItemAffectsSoundnessStructuralIntegrityIndicator and "
        "m:DefectItemDescription and m:DefectItemLocationType and "
        "m:DefectItemRecommendedActionType",
    )

    result = {
        "UAD1034": (SF1, property_context, property_target + "/@ValuationUseType"),
        "UAD1047": (
            SF1,
            improvement_context,
            improvement + "/m:ImprovementType",
        ),
        "UAD1270": (
            SF1,
            foreign_context,
            foreign_object + "/m:ObjectURL",
        ),
        "UAD1291": (
            "data/uad36-test-suite/tests/fixtures/"
            "existing_context_required/derived/UAD1291.xml",
            encroachment_context,
            encroachment + "/m:EncroachmentDirectionType",
        ),
        "UAD1349": (
            SF1,
            utility_context,
            utility + "/m:SiteUtilityOwnershipType",
        ),
        "UAD1363": (
            SF1,
            site_view_context,
            site_view + "/m:ViewPrimaryIndicator",
        ),
        "UAD1364": (
            SF1,
            site_view_context,
            site_view + "/m:ViewRangeType",
        ),
        "UAD1366": (
            SF1,
            site_view_context,
            site_view + "/m:ValueMarketabilityImpactType",
        ),
        "UAD1388": (
            SF1,
            commentary_context,
            commentary + "/m:ValuationAnalysisCategoryType",
        ),
        "UAD1558": (
            SF1,
            inspection_context,
            inspection + "/m:PropertyExteriorInspectionMethodType",
        ),
        "UAD1559": (
            SF1,
            inspection_context,
            inspection + "/m:PropertyInteriorInspectionMethodType",
        ),
        "UAD1705": (
            SF1,
            image_context,
            image + "/m:ImageFileLocationIdentifier",
        ),
        "UAD1707": (
            SF1,
            image_context,
            image + "/m:MIMETypeIdentifier",
        ),
        "UAD1710": (
            SF1,
            defect_context,
            defect + "/m:DefectItemAffectsSoundnessStructuralIntegrityIndicator",
        ),
        "UAD1711": (
            SF1,
            defect_context,
            defect + "/m:DefectItemDescription",
        ),
        "UAD1712": (
            SF1,
            defect_context,
            defect + "/m:DefectItemLocationType",
        ),
        "UAD1714": (
            SF1,
            defect_context,
            defect + "/m:DefectItemRecommendedActionType",
        ),
    }
    image_names = {
        "UAD1736": "MH1_Garage.png",
        "UAD1737": "MH1_Flooring.png",
        "UAD1738": "MH1_Bedroom1.png",
        "UAD1739": "MH1_Deck.png",
        "UAD1740": "MH1_ExteriorTrimDDD.png",
    }
    for rule_id, filename in image_names.items():
        image_context = indexed_context(
            "IMAGE",
            "m:ImageFileLocationIdentifier='\\\\Images\\"
            + filename
            + "' and m:MIMETypeIdentifier",
        )
        result[rule_id] = (
            "data/uad36-test-suite/tests/fixtures/"
            f"existing_context_required/derived/{rule_id}.xml",
            stable_context("IMAGE"),
            image_context + "/m:ImageFileLocationIdentifier",
        )
    return result


def write_derived_fixtures(parser, schema):
    DERIVED.mkdir(parents=True, exist_ok=True)

    encroachment = etree.parse(str(ROOT / ENCROACHMENT_SOURCE), parser)
    contexts = encroachment.xpath(
        "(//m:PROPERTY[@ValuationUseType='SubjectProperty']"
        "//m:ENCROACHMENT[m:EncroachmentType])[1]",
        namespaces=NS,
    )
    if len(contexts) != 1:
        raise ValueError("UAD1291 needs one subject encroachment context")
    context = contexts[0]
    direction = etree.Element(M + "EncroachmentDirectionType")
    direction.text = "BorderingPropertyEncroachingOnSubjectProperty"
    encroachment_type = context.find(M + "EncroachmentType")
    context.insert(context.index(encroachment_type), direction)
    schema.assertValid(encroachment)
    encroachment.write(
        str(DERIVED / "UAD1291.xml"),
        encoding="utf-8",
        xml_declaration=True,
    )

    image_names = {
        "UAD1736": "MH1_Garage.png",
        "UAD1737": "MH1_Flooring.png",
        "UAD1738": "MH1_Bedroom1.png",
        "UAD1739": "MH1_Deck.png",
        "UAD1740": "MH1_ExteriorTrimDDD.png",
    }
    source = etree.parse(str(ROOT / MH1), parser)
    images = source.xpath(
        "//m:PROPERTY[@ValuationUseType='SubjectProperty']"
        "//m:IMAGE[m:ImageFileLocationIdentifier and m:MIMETypeIdentifier]",
        namespaces=NS,
    )
    if not images:
        raise ValueError("MH1 sample has no usable subject IMAGE context")
    for rule_id, filename in image_names.items():
        document = copy.deepcopy(source)
        target = document.xpath(
            "(//m:PROPERTY[@ValuationUseType='SubjectProperty']"
            "//m:IMAGE[m:ImageFileLocationIdentifier and "
            "m:MIMETypeIdentifier])[1]/m:ImageFileLocationIdentifier",
            namespaces=NS,
        )
        if len(target) != 1:
            raise ValueError(f"{rule_id}: expected one selected IMAGE")
        target[0].text = "\\\\Images\\" + filename
        schema.assertValid(document)
        document.write(
            str(DERIVED / f"{rule_id}.xml"),
            encoding="utf-8",
            xml_declaration=True,
        )


def main():
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    schema = etree.XMLSchema(etree.parse(str(SCHEMA), parser))
    write_derived_fixtures(parser, schema)

    tracking = Graph().parse(TRACKING, format="turtle")
    members = sorted(set(tracking.objects(SCENARIO, WT.coversRule)), key=str)
    rule_ids = [str(member).rsplit(":", 1)[-1] for member in members]
    if len(rule_ids) != 22 or len(set(rule_ids)) != 22:
        raise ValueError("Existing-context inventory must contain 22 rules")

    with RULES.open(encoding="utf-8-sig", newline="") as stream:
        source = {
            row["Message ID"]: row
            for row in csv.DictReader(stream)
            if row["Message ID"] in rule_ids
        }
    if set(source) != set(rule_ids):
        missing = sorted(set(rule_ids) - set(source))
        raise ValueError("Missing governed source rows: " + ", ".join(missing))

    reviewed = bindings()
    if set(reviewed) != set(rule_ids):
        raise ValueError("Executable bindings do not match governed membership")

    executable = {}
    for rule_id in rule_ids:
        baseline, context_xpath, target_xpath = reviewed[rule_id]
        document = etree.parse(str(ROOT / baseline), parser)
        schema.assertValid(document)
        contexts = document.xpath(context_xpath, namespaces=NS)
        targets = document.xpath(target_xpath, namespaces=NS)
        if not contexts or len(targets) != 1:
            raise ValueError(
                f"{rule_id}: expected contexts and one required value; "
                f"found {len(contexts)} and {len(targets)}"
            )
        negative = copy.deepcopy(document)
        target = negative.xpath(target_xpath, namespaces=NS)[0]
        if isinstance(target, etree._Element):
            target.getparent().remove(target)
        elif target.is_attribute:
            del target.getparent().attrib[target.attrname]
        else:
            raise ValueError(f"{rule_id}: target is not removable")
        if len(negative.xpath(context_xpath, namespaces=NS)) != len(contexts):
            raise ValueError(f"{rule_id}: context did not survive removal")
        executable[rule_id] = {
            "baselinePath": baseline,
            "contextXPath": context_xpath,
            "requiredValueXPath": target_xpath,
            "expectedDataLocation": target_xpath,
            "expectedViolationKind": "MissingRequiredValueInExistingContext",
            "xsdValidAfterRemoval": schema.validate(negative),
        }

    lines = [
        "@prefix case: <urn:uad36:test-case:IT-1R8S1:> .",
        "@prefix suite: <urn:uad36:test-suite:> .",
        "@prefix t: <urn:uad36:test-suite:vocab:> .",
        "",
        "suite:existing-context-required a t:TestSuite ;",
        "    t:category "
        "<urn:uad36:work-tracking:scenario:existing_context_required> ;",
        "    t:hasCase "
        + ",\n        ".join(f"case:{rule_id}" for rule_id in rule_ids)
        + " ;",
        "    t:ruleInventoryPath \"data/data-constraints.csv\" ;",
        "    t:scenarioId \"IT-1R8S1\" .",
        "",
    ]
    for member, rule_id in zip(members, rule_ids):
        row = source[rule_id]
        statements = ["a t:TestCase"]
        for source_name, predicate in SOURCE_FIELDS.items():
            statements.append(f"t:{predicate} {literal(row[source_name])}")
        statements.append(f"t:sourceRule <{member}>")
        for predicate, value in executable[rule_id].items():
            statements.append(f"t:{predicate} {literal(value)}")
        lines.append(
            f"case:{rule_id} " + " ;\n    ".join(statements) + " ."
        )
        lines.append("")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")

    production = [
        "@prefix b: <urn:uad36:existing-context-required-binding:> .",
        "",
    ]
    for rule_id in rule_ids:
        row = source[rule_id]
        binding = executable[rule_id]
        element = row["Primary Data Element"]
        relative = element if element.startswith("@") else "m:" + element
        production.extend([
            f"<urn:uad36:existing-context-required-rule:{rule_id}> "
            "a b:Binding ;",
            f"    b:contextXPath {literal(binding['contextXPath'])} ;",
            f"    b:element {literal(element)} ;",
            "    b:expectedDataLocation "
            f"{literal(binding['expectedDataLocation'])} ;",
            f"    b:requiredValueRelativeXPath {literal(relative)} ;",
            f"    b:ruleId {literal(rule_id)} ;",
            f"    b:sourceFingerprint {literal(source_fingerprint(row))} ;",
            "    b:violationKind "
            f"{literal(binding['expectedViolationKind'])} .",
            "",
        ])
    PRODUCTION_OUTPUT.write_text(
        "\n".join(production), encoding="utf-8", newline="\n"
    )


if __name__ == "__main__":
    main()
