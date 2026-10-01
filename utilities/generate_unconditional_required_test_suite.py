"""Generate the IT-1R4S1 RDF test inventory from governed source rows."""

import copy
import csv
import glob
import json
from pathlib import Path

from lxml import etree
from rdflib import Graph, Namespace, URIRef


ROOT = Path(__file__).resolve().parents[1]
TRACKING = ROOT / "data/spreadsheet-rule-category-tracking.ttl"
RULES = ROOT / "data/data-constraints.csv"
OUTPUT = ROOT / (
    "data/uad36-test-suite/tests/fixtures/unconditional_required/"
    "test-suite.ttl"
)
SCHEMA = ROOT / (
    "chatgpt-sources/sources/schemas/UAD/GSE_UAD_3.6.0_v1.3/"
    "Combined/GSE_UAD_3.6.0_v1.3.xsd"
)
WT = Namespace("urn:uad36:work-tracking:vocab:")
SCENARIO = URIRef("urn:uad36:work-tracking:scenario:unconditional_required")
NS = {"m": "http://www.mismo.org/residential/2009/schemas"}
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


def literal(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return json.dumps(value or "", ensure_ascii=False)


def governed_xpath(row):
    parts = row[" xPath"].removeprefix("../").strip("/").split("/")
    steps = ["m:" + part for part in parts]
    if row["Property Affected"] == "Subject":
        try:
            index = parts.index("PROPERTY")
        except ValueError as error:
            raise ValueError(
                f"{row['Message ID']}: subject rule has no PROPERTY context"
            ) from error
        steps[index] += "[@ValuationUseType='SubjectProperty']"
    element = row["Primary Data Element"]
    steps.append(element if element.startswith("@") else "m:" + element)
    return "//" + "/".join(steps)


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
    schema = etree.XMLSchema(etree.parse(str(SCHEMA), parser))
    documents = []
    for path in candidate_files():
        root = etree.parse(str(path), parser).getroot()
        if schema.validate(root):
            documents.append((path, root))

    bindings = {}
    for rule_id, row in source.items():
        target = governed_xpath(row)
        selected = None
        for path, root in documents:
            matches = root.getroottree().xpath(target, namespaces=NS)
            if len(matches) == 1:
                selected = (path, root)
                break
        if selected is None:
            raise ValueError(
                f"No unambiguous positive XML fixture for {rule_id}: {target}"
            )

        path, root = selected
        negative = copy.deepcopy(root)
        matches = negative.getroottree().xpath(target, namespaces=NS)
        target_node = matches[0]
        if isinstance(target_node, etree._Element):
            target_node.getparent().remove(target_node)
        elif target_node.is_attribute:
            del target_node.getparent().attrib[target_node.attrname]
        else:
            raise ValueError(f"{rule_id}: target must be an element or attribute")

        bindings[rule_id] = {
            "baselinePath": path.relative_to(ROOT).as_posix(),
            "requiredValueXPath": target,
            "expectedDataLocation": target,
            "xsdValidAfterRemoval": schema.validate(negative),
        }
    return bindings


def main():
    tracking = Graph().parse(TRACKING, format="turtle")
    members = sorted(
        set(tracking.objects(SCENARIO, WT.coversRule)), key=str
    )
    rule_ids = [str(member).rsplit(":", 1)[-1] for member in members]
    if len(rule_ids) != 62 or len(set(rule_ids)) != 62:
        raise ValueError("Unconditional-required inventory must contain 62 rules")

    with RULES.open(encoding="utf-8-sig", newline="") as stream:
        source = {
            row["Message ID"]: row
            for row in csv.DictReader(stream)
            if row["Message ID"] in rule_ids
        }
    missing = sorted(set(rule_ids) - set(source))
    if missing:
        raise ValueError("Missing governed source rows: " + ", ".join(missing))
    bindings = executable_bindings(source)

    lines = [
        "@prefix case: <urn:uad36:test-case:IT-1R4S1:> .",
        "@prefix suite: <urn:uad36:test-suite:> .",
        "@prefix t: <urn:uad36:test-suite:vocab:> .",
        "",
        "suite:unconditional-required a t:TestSuite ;",
        "    t:category <urn:uad36:work-tracking:scenario:unconditional_required> ;",
        "    t:hasCase "
        + ",\n        ".join(f"case:{rule_id}" for rule_id in rule_ids)
        + " ;",
        "    t:ruleInventoryPath \"data/data-constraints.csv\" ;",
        "    t:scenarioId \"IT-1R4S1\" .",
        "",
    ]
    for member, rule_id in zip(members, rule_ids):
        row = source[rule_id]
        statements = ["a t:TestCase"]
        for source_name, predicate in SOURCE_FIELDS.items():
            statements.append(f"t:{predicate} {literal(row[source_name])}")
        statements.append(f"t:sourceRule <{member}>")
        for predicate, value in bindings[rule_id].items():
            statements.append(f"t:{predicate} {literal(value)}")
        lines.append(
            f"case:{rule_id} " + " ;\n    ".join(statements) + " ."
        )
        lines.append("")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
