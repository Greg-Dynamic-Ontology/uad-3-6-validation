"""Generate schema-valid IT-1R13S1 aggregate fixtures and manifest.ttl.

Default: validate in memory and verify saved files without writing.
Use --write to create the corpus. --replace-generated additionally requires
an existing ownership manifest and unchanged saved XML hashes.
"""

import argparse
import csv
import hashlib
import json
import os
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path, PurePosixPath

from lxml import etree
from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.compare import isomorphic


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = "tests/fixtures/it_1/r13/s1"
GENERATOR = "scripts/testing/generate_it_1_r13_s1_fixtures.py"
SOURCE = (
    "chatgpt-sources/sources/samples/UAD/"
    "Appendix D-1 URAR Sample Use Cases and XML Files/"
    "Appendix D-1 SF1_Appraisal/SF1_Appraisal_v1.4.xml"
)
SOURCE_SHA256 = "47509c23bcf28c3abb9c57e00a3f93cf52ed38fec3862d7cda24bffd6bca5be9"
SCHEMA = (
    "chatgpt-sources/sources/schemas/UAD/GSE_UAD_3.6.0_v1.3/"
    "Combined/GSE_UAD_3.6.0_v1.3.xsd"
)
TRACKING = "data/spreadsheet-rule-category-tracking.ttl"
CSV = "data/data-constraints.csv"
T = Namespace("urn:uad36:test-suite:vocab:")
WT = Namespace("urn:uad36:work-tracking:vocab:")
SUITE = URIRef("urn:uad36:test-suite:aggregate-cross-record-consistency")
SCENARIO = URIRef("urn:uad36:work-tracking:scenario:aggregate_cross_record_consistency")
NS = {
    "m": "http://www.mismo.org/residential/2009/schemas",
    "xlink": "http://www.w3.org/1999/xlink",
    "xs": "http://www.w3.org/2001/XMLSchema",
}
M = "{" + NS["m"] + "}"
X = "{" + NS["xlink"] + "}"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
FIELDS = {
    "Message ID": T.ruleId,
    "Unique ID": T.sourceUniqueIdCell,
    "Primary Data Element": T.primaryDataElement,
    "Rule Logic": T.ruleLogic,
    "Severity": T.severity,
    "Property Affected": T.propertyAffected,
    " xPath": T.xpath,
    "Message Text": T.messageText,
}
FINGERPRINTS = {
    "UAD1011": "4cb2ac514aa085795b35779981b8abe1cdcfbc3149a91606cfe61b1d8ce47f7e",
    "UAD1016": "3c0422d0a5985ae6c1e657e4119a3d03481650bd1fbe2849d95e14bee030bea3",
    "UAD1019": "c94fce7ed56cf537fdd299944f6d663aaddde43bb7c7b759d5355515d79f2146",
    "UAD1086": "a29eba5b13db2f9d673620f1be2b0339842e56e1c084a63c7f0b12c6ce364833",
    "UAD1250": "7f66ebfb5348c5aad26a8f13652d5fd10371ff29a328ba56d824bdd2fad363d1",
    "UAD1455": "8565dcf4bf2e9d178e6135c9eb8c4b3e66dc69b46872fa6c9f0279c0cdbfe1d8",
    "UAD1461": "514b0f1e30d0e97eefcaa24e9957e0f4192f0e50ae06c75e0999284393467956",
    "UAD1693": "110ec70fb17dec3c40d0a43ef1b341aec31d71c084163525f990b3a742e667f8",
}
SALES_TYPES = (
    "SalesComparableAdditionalAdjustableComparisonItem",
    "SalesComparableAdditionalNonAdjustableComparisonItem",
)
GRM_TYPE = "GrossRentMultiplierAdditionalNonAdjustableComparisonItem"


@dataclass(frozen=True)
class Plan:
    rule_id: str
    name: str
    expected: int = 1


PLANS = (
    Plan("UAD1011", "zero-adus"),
    Plan("UAD1011", "one-adu"),
    Plan("UAD1011", "other-property-control", 0),
    Plan("UAD1016", "one-dwelling"),
    Plan("UAD1016", "zero-dwellings"),
    Plan("UAD1016", "exclude-outbuilding"),
    Plan("UAD1016", "two-dwellings"),
    Plan("UAD1016", "other-property-control", 0),
    Plan("UAD1019", "one-non-adu"),
    Plan("UAD1019", "zero-non-adus"),
    Plan("UAD1019", "other-property-control", 0),
    Plan("UAD1086", "one-unit"),
    Plan("UAD1086", "local-improvement-count"),
    Plan("UAD1086", "other-property-control", 0),
    Plan("UAD1693", "one-structure"),
    Plan("UAD1693", "multiple-structures"),
    Plan("UAD1693", "other-property-control", 0),
    Plan("UAD1461", "decimal-mixed-sign"),
    Plan("UAD1461", "negative-total"),
    Plan("UAD1461", "zero-total"),
    Plan("UAD1461", "subject-adjustment-control", 0),
    *(Plan(rule, name, 0 if name == "other-property-control" else 1)
      for rule in ("UAD1250", "UAD1455")
      for name in (
          "identifier-mismatch", "missing-comparable-row",
          "missing-subject-row", "extra-comparable-row",
          "type-and-identifier-key", "other-property-control",
          "separate-analysis-groups",
      )),
    Plan("UAD1455", "nonadjustable-identifier-mismatch"),
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def fingerprint(row):
    return sha256(json.dumps(
        [row[key] for key in FIELDS],
        ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8"))


def one(node, xpath):
    selected = node.xpath(xpath, namespaces=NS)
    if len(selected) != 1:
        raise ValueError(
            f"Expected exactly one node for {xpath}: {len(selected)}"
        )
    return selected[0]


def absolute_path(node):
    parts = []
    while node is not None:
        name = "m:" + etree.QName(node).localname
        parent = node.getparent()
        if parent is not None:
            siblings = [item for item in parent if item.tag == node.tag]
            if len(siblings) > 1:
                name += f"[{siblings.index(node) + 1}]"
        parts.append(name)
        node = parent
    return "/" + "/".join(reversed(parts))


def set_text(node, value, changes):
    before = node.text or ""
    if before != value:
        changes.append((absolute_path(node), before, value))
        node.text = value


def ensure_child(parent, name, schema_document, additions):
    matches = parent.findall(M + name)
    if matches:
        if len(matches) != 1:
            raise ValueError(f"Ambiguous existing {name}")
        return matches[0]
    type_name = etree.QName(parent).localname
    declarations = schema_document.xpath(
        "/xs:schema/xs:complexType[@name=$name]/xs:sequence/xs:element",
        namespaces=NS, name=type_name,
    )
    order = [item.get("name") for item in declarations]
    if name not in order:
        raise ValueError(
            f"No direct schema sequence entry for {type_name}/{name}"
        )
    rank = order.index(name)
    child = etree.Element(M + name)
    index = len(parent)
    for position, sibling in enumerate(parent):
        sibling_name = etree.QName(sibling).localname
        if sibling_name in order and order.index(sibling_name) > rank:
            index = position
            break
    parent.insert(index, child)
    additions.append(absolute_path(child))
    return child


def source_rows():
    tracking = Graph().parse(ROOT / TRACKING, format="turtle")
    governed = {
        str(tracking.value(node, WT.ruleId)): node
        for node in tracking.objects(SCENARIO, WT.coversRule)
    }
    if set(governed) != set(FINGERPRINTS):
        raise ValueError(
            "Governed aggregate membership differs from reviewed eight rows"
        )
    with (ROOT / CSV).open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    selected = {}
    for rule_id, expected_hash in FINGERPRINTS.items():
        matches = [row for row in rows if row["Message ID"] == rule_id]
        if len(matches) != 1:
            raise ValueError(f"{rule_id}: expected one original CSV row")
        row = matches[0]
        if fingerprint(row) != expected_hash:
            raise ValueError(f"{rule_id}: reviewed CSV definition changed")
        differences = []
        for column, predicate in FIELDS.items():
            key = str(predicate).removeprefix(str(T))
            values = list(tracking.objects(governed[rule_id], WT[key]))
            approved = row[column]
            reason = ""
            if rule_id == "UAD1455" and column == "Rule Logic":
                approved = approved.replace("Basement Access", "Below Grade Exterior Access")
                reason = "Reviewed example-label difference; CSV remains authoritative"
            elif rule_id == "UAD1693" and column in {"Rule Logic", " xPath"}:
                approved = approved.replace("\n", "\r\n")
                reason = "Reviewed LF/CRLF literal difference; original values preserved"
            if len(values) != 1 or str(values[0]) != approved:
                raise ValueError(
                    f"{rule_id}: CSV/tracking mismatch for {column}"
                )
            if str(values[0]) != row[column]:
                differences.append((column, row[column], str(values[0]), reason))
        selected[rule_id] = (row, governed[rule_id], differences)
    return selected


def scalar(node, name):
    child = node.find(M + name)
    return "" if child is None else (child.text or "").strip()


def clone_record(node, suffix, additions):
    clone = deepcopy(node)
    labels = {
        item.get(X + "label"): item.get(X + "label") + suffix
        for item in clone.iter() if item.get(X + "label")
    }
    for item in clone.iter():
        for key in ("label", "from", "to"):
            value = item.get(X + key)
            if value in labels:
                item.set(X + key, labels[value])
    parent = node.getparent()
    siblings = [item for item in parent if item.tag == node.tag]
    if clone.get("SequenceNumber") is not None:
        clone.set("SequenceNumber", str(max(
            int(item.get("SequenceNumber", "0")) for item in siblings
        ) + 1))
    parent.insert(parent.index(siblings[-1]) + 1, clone)
    additions.append(absolute_path(clone))
    return clone


def add_comparison(prop, kind, identifier, schema_document, additions):
    comparable = ensure_child(prop, "COMPARABLE", schema_document, additions)
    container = ensure_child(
        comparable, "COMPARABLE_ADJUSTMENTS", schema_document, additions,
    )
    node = etree.Element(M + "COMPARABLE_ADJUSTMENT")
    for name, value in (
        ("AdditionalComparisonLineItemIdentifier", identifier),
        ("ComparableAdjustmentType", kind),
    ):
        etree.SubElement(node, M + name).text = value
    existing = container.findall(M + "COMPARABLE_ADJUSTMENT")
    index = container.index(existing[-1]) + 1 if existing else 0
    container.insert(index, node)
    additions.append(absolute_path(node))
    return node


def prepare(plan, original, schema_document):
    root = etree.fromstring(original, etree.XMLParser(
        resolve_entities=False, no_network=True, remove_blank_text=True,
    ))
    changes, additions, removals = [], [], []
    analysis = one(root, "//m:VALUATION_ANALYSIS")
    properties = one(analysis, "m:PROPERTIES")
    subject = one(properties, "m:PROPERTY[@ValuationUseType='SubjectProperty']")
    comparables = properties.findall("m:PROPERTY[@ValuationUseType='SalesComparable']", NS)
    rule, mode = plan.rule_id, plan.name
    mutation = "text"
    after = ""
    target = None

    def set_value(parent, name, value):
        node = ensure_child(parent, name, schema_document, additions)
        set_text(node, str(value), changes)
        return node

    if rule in {"UAD1250", "UAD1455"}:
        role = "GrossRentMultiplierComparable" if rule == "UAD1250" else "SalesComparable"
        if rule == "UAD1250":
            for prop in comparables[:2]:
                before = prop.get("ValuationUseType")
                prop.set("ValuationUseType", role)
                changes.append((absolute_path(prop) + "/@ValuationUseType", before, role))
        participants = [subject] + properties.findall(
            f"m:PROPERTY[@ValuationUseType='{role}']", NS,
        )
        types = (GRM_TYPE,) if rule == "UAD1250" else SALES_TYPES
        kind = types[-1] if mode.startswith("nonadjustable") else types[0]
        keys = [(kind, "Reviewed row A"), (kind, "Reviewed row B")]
        if rule == "UAD1455" and mode == "type-and-identifier-key":
            keys = [(types[0], "Shared identifier"), (types[1], "Shared identifier")]
        for prop in participants:
            for node in list(prop.findall("m:COMPARABLE/m:COMPARABLE_ADJUSTMENTS/m:COMPARABLE_ADJUSTMENT", NS)):
                if scalar(node, "ComparableAdjustmentType") in types:
                    removals.append(absolute_path(node))
                    node.getparent().remove(node)
            for item_kind, identifier in keys:
                add_comparison(prop, item_kind, identifier, schema_document, additions)

        # Select the reviewed row by its explicit type and identifier.
        def reviewed(prop):
            return one(prop,
                "m:COMPARABLE/m:COMPARABLE_ADJUSTMENTS/m:COMPARABLE_ADJUSTMENT"
                f"[m:ComparableAdjustmentType='{keys[0][0]}']"
                f"[m:AdditionalComparisonLineItemIdentifier='{keys[0][1]}']")

        node = reviewed(participants[1])
        target = node.find(M + "AdditionalComparisonLineItemIdentifier")
        after = "Changed row A"
        if mode.startswith("missing-"):
            target = reviewed(subject if mode == "missing-subject-row" else participants[1])
            mutation = "remove"
        elif mode == "extra-comparable-row":
            node = add_comparison(participants[1], "SiteSize", "Comparable-only extra row",
                                  schema_document, additions)
            target = node.find(M + "ComparableAdjustmentType")
            after = kind
        elif mode == "type-and-identifier-key":
            target = node.find(M + "ComparableAdjustmentType")
            after = SALES_TYPES[1] if rule == "UAD1455" else SALES_TYPES[0]
        elif mode == "other-property-control":
            foreign = one(properties, "m:PROPERTY[@ValuationUseType='PropertyAnalyzedNotUsed'][1]")
            node = add_comparison(foreign, kind, "Reviewed row A", schema_document, additions)
            target = node.find(M + "AdditionalComparisonLineItemIdentifier")
        elif mode == "separate-analysis-groups":
            service = analysis
            while etree.QName(service).localname != "SERVICE":
                service = service.getparent()
            other_service = clone_record(service, "_R13_OTHER_ANALYSIS", additions)
            other = one(other_service, ".//m:VALUATION_ANALYSIS")
            for identifier in other.findall(
                "m:PROPERTIES/m:PROPERTY/m:COMPARABLE/m:COMPARABLE_ADJUSTMENTS/"
                "m:COMPARABLE_ADJUSTMENT/m:AdditionalComparisonLineItemIdentifier", NS,
            ):
                set_text(identifier, (identifier.text or "") + " other analysis", changes)
        expected_location = absolute_path(properties)
    elif rule == "UAD1461":
        for prop in comparables:
            detail = one(prop, "m:COMPARABLE/m:COMPARABLE_DETAIL")
            values = prop.findall("m:COMPARABLE/m:COMPARABLE_ADJUSTMENTS/m:COMPARABLE_ADJUSTMENT/m:ComparableAdjustmentAmount", NS)
            total = sum((Decimal(item.text) for item in values), Decimal(0))
            set_value(detail, "SalePriceNetTotalAdjustmentAmount", total)
        values = comparables[0].findall("m:COMPARABLE/m:COMPARABLE_ADJUSTMENTS/m:COMPARABLE_ADJUSTMENT/m:ComparableAdjustmentAmount", NS)
        if len(values) < 3:
            raise ValueError("Published sample requires three adjustment amounts")
        amounts = {
            "decimal-mixed-sign": ("0.10", "0.20", "-0.10"),
            "negative-total": ("-10", "-2", "0"),
            "zero-total": ("100", "-100", "0"),
            "subject-adjustment-control": ("0.10", "0.20", "-0.10"),
        }[mode]
        for index, item in enumerate(values):
            set_text(item, amounts[index] if index < 3 else "0", changes)
        detail = one(comparables[0], "m:COMPARABLE/m:COMPARABLE_DETAIL")
        total_node = set_value(detail, "SalePriceNetTotalAdjustmentAmount",
                               sum(map(Decimal, amounts), Decimal(0)))
        target, after = values[0], str(Decimal(amounts[0]) + Decimal("0.01"))
        if mode == "subject-adjustment-control":
            adjustment = one(subject, "m:COMPARABLE/m:COMPARABLE_ADJUSTMENTS/m:COMPARABLE_ADJUSTMENT")
            target = set_value(adjustment, "ComparableAdjustmentAmount", "0")
            after = "1"
        expected_location = absolute_path(total_node)
    else:
        improvements = one(subject, "m:IMPROVEMENTS")
        improvement = one(improvements, "m:IMPROVEMENT")
        if mode in {"exclude-outbuilding", "two-dwellings", "local-improvement-count", "multiple-structures"}:
            clone = clone_record(improvement, "_R13_SECOND", additions)
            if mode == "exclude-outbuilding":
                set_value(one(clone, "m:IMPROVEMENT_DETAIL"), "ImprovementType", "Outbuilding")
        property_detail = one(subject, "m:PROPERTY_DETAIL")
        units = subject.findall("m:IMPROVEMENTS/m:IMPROVEMENT/m:PROPERTY_UNITS/m:PROPERTY_UNIT/m:PROPERTY_UNIT_DETAIL", NS)
        for unit in units:
            indicator = "false"
            if rule == "UAD1011" and mode == "one-adu":
                indicator = "true"
            elif rule == "UAD1019" and mode == "zero-non-adus":
                indicator = "true"
            set_value(unit, "AccessoryDwellingUnitIndicator", indicator)
        details = subject.findall("m:IMPROVEMENTS/m:IMPROVEMENT/m:IMPROVEMENT_DETAIL", NS)
        if mode == "zero-dwellings":
            set_value(details[0], "ImprovementType", "Outbuilding")
        adus = sum(scalar(item, "AccessoryDwellingUnitIndicator") in {"true", "1"} for item in units)
        non_adus = sum(scalar(item, "AccessoryDwellingUnitIndicator") in {"false", "0"} for item in units)
        dwellings = sum(scalar(item, "ImprovementType") == "Dwelling" for item in details)
        nodes = {
            "UAD1011": set_value(property_detail, "AccessoryDwellingUnitTotalCount", adus),
            "UAD1016": set_value(property_detail, "DwellingCount", dwellings),
            "UAD1019": set_value(property_detail, "LivingUnitExcludingADUCount", non_adus),
        }
        living_nodes = []
        for item in improvements.findall(M + "IMPROVEMENT"):
            structure = one(item, "m:STRUCTURE/m:STRUCTURE_DETAIL")
            count = len(item.findall("m:PROPERTY_UNITS/m:PROPERTY_UNIT", NS))
            living_nodes.append(set_value(structure, "LivingUnitCount", count))
        if rule == "UAD1086":
            target = living_nodes[0]
        elif rule == "UAD1693":
            target = nodes["UAD1019"]
        else:
            target = nodes[rule]
        expected_location = absolute_path(target)
        if mode == "other-property-control":
            if rule in {"UAD1086", "UAD1693"}:
                target = one(comparables[0], "m:IMPROVEMENTS/m:IMPROVEMENT/m:STRUCTURE/m:STRUCTURE_DETAIL/m:LivingUnitCount")
            else:
                element = {"UAD1011": "AccessoryDwellingUnitTotalCount", "UAD1016": "DwellingCount", "UAD1019": "LivingUnitExcludingADUCount"}[rule]
                target = one(comparables[0], "m:PROPERTY_DETAIL/m:" + element)
        value = int(target.text)
        after = str(value - 1 if value > 0 and rule != "UAD1086" else value + 1)

    return root, target, mutation, after, expected_location, changes, additions, removals


def oracle(root, rule):
    """Validate fixture intent without invoking any production evaluator."""
    bad = []
    for analysis in root.findall(".//" + M + "VALUATION_ANALYSIS"):
        properties = analysis.find(M + "PROPERTIES")
        subjects = properties.findall("m:PROPERTY[@ValuationUseType='SubjectProperty']", NS)
        if rule in {"UAD1250", "UAD1455"}:
            role = "GrossRentMultiplierComparable" if rule == "UAD1250" else "SalesComparable"
            types = {GRM_TYPE} if rule == "UAD1250" else set(SALES_TYPES)
            participants = subjects + properties.findall(f"m:PROPERTY[@ValuationUseType='{role}']", NS)
            keys = [set(
                (scalar(item, "ComparableAdjustmentType"), scalar(item, "AdditionalComparisonLineItemIdentifier"))
                for item in prop.findall("m:COMPARABLE/m:COMPARABLE_ADJUSTMENTS/m:COMPARABLE_ADJUSTMENT", NS)
                if scalar(item, "ComparableAdjustmentType") in types
            ) for prop in participants]
            if keys and any(key != keys[0] for key in keys[1:]):
                bad.append(absolute_path(properties))
        elif rule == "UAD1461":
            for prop in properties.findall("m:PROPERTY[@ValuationUseType='SalesComparable']", NS):
                target = one(prop, "m:COMPARABLE/m:COMPARABLE_DETAIL/m:SalePriceNetTotalAdjustmentAmount")
                values = prop.findall("m:COMPARABLE/m:COMPARABLE_ADJUSTMENTS/m:COMPARABLE_ADJUSTMENT/m:ComparableAdjustmentAmount", NS)
                if Decimal(target.text) != sum((Decimal(item.text) for item in values), Decimal(0)):
                    bad.append(absolute_path(target))
        else:
            for subject in subjects:
                detail = one(subject, "m:PROPERTY_DETAIL")
                improvements = subject.findall("m:IMPROVEMENTS/m:IMPROVEMENT", NS)
                units = subject.findall("m:IMPROVEMENTS/m:IMPROVEMENT/m:PROPERTY_UNITS/m:PROPERTY_UNIT/m:PROPERTY_UNIT_DETAIL", NS)
                if rule == "UAD1086":
                    for item in improvements:
                        target = one(item, "m:STRUCTURE/m:STRUCTURE_DETAIL/m:LivingUnitCount")
                        if int(target.text) != len(item.findall("m:PROPERTY_UNITS/m:PROPERTY_UNIT", NS)):
                            bad.append(absolute_path(target))
                    continue
                element = {
                    "UAD1011": "AccessoryDwellingUnitTotalCount", "UAD1016": "DwellingCount",
                    "UAD1019": "LivingUnitExcludingADUCount", "UAD1693": "LivingUnitExcludingADUCount",
                }[rule]
                target = one(detail, "m:" + element)
                observed = int(target.text)
                if rule == "UAD1016":
                    expected = sum(scalar(one(item, "m:IMPROVEMENT_DETAIL"), "ImprovementType") == "Dwelling" for item in improvements)
                elif rule == "UAD1693":
                    observed += int(scalar(detail, "AccessoryDwellingUnitTotalCount"))
                    expected = sum(int(scalar(one(item, "m:STRUCTURE/m:STRUCTURE_DETAIL"), "LivingUnitCount")) for item in improvements)
                else:
                    accepted = {"true", "1"} if rule == "UAD1011" else {"false", "0"}
                    expected = sum(scalar(item, "AccessoryDwellingUnitIndicator") in accepted for item in units)
                if observed != expected:
                    bad.append(absolute_path(target))
    return bad


def serialize_xml(root, relative, schema):
    reference = Path(os.path.relpath(ROOT / SCHEMA, (ROOT / relative).parent)).as_posix()
    root.set("{" + XSI + "}schemaLocation", NS["m"] + " " + reference)
    etree.cleanup_namespaces(root, top_nsmap={"xsi": XSI})
    data = etree.tostring(root, encoding="UTF-8", xml_declaration=True, pretty_print=True)
    parsed = etree.fromstring(data, etree.XMLParser(resolve_entities=False, no_network=True))
    schema.assertValid(parsed)
    labels = [item.get(X + "label") for item in parsed.iter() if item.get(X + "label")]
    if len(labels) != len(set(labels)):
        raise ValueError("Generated XML contains duplicate XLink labels")
    for item in parsed.iter():
        for key in ("from", "to"):
            if item.get(X + key) and item.get(X + key) not in set(labels):
                raise ValueError("Generated relationship has an unresolved XLink endpoint")
    return data


def build():
    rows = source_rows()
    original = (ROOT / SOURCE).read_bytes()
    if sha256(original) != SOURCE_SHA256:
        raise ValueError("Published SF1 source differs from reviewed bytes")
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    schema_document = etree.parse(str(ROOT / SCHEMA), parser)
    schema = etree.XMLSchema(schema_document)
    schema.assertValid(etree.fromstring(original, parser))
    if {plan.rule_id for plan in PLANS} != set(FINGERPRINTS):
        raise ValueError("Plans do not cover the eight reviewed source rules")
    if len({(plan.rule_id, plan.name) for plan in PLANS}) != len(PLANS):
        raise ValueError("Duplicate test case identity")
    graph = Graph()
    graph.bind("t", T)
    graph.bind("wt", WT)
    graph.add((SUITE, RDF.type, T.TestSuite))

    def record(node, values):
        for name, value in values.items():
            graph.add((node, T[name], Literal(value)))

    record(SUITE, {
        "scenarioId": "IT-1R13S1", "generatedBy": GENERATOR,
        "expectedCaseCount": len(PLANS), "expectedFixtureCount": len(PLANS) * 2,
        "sourceRuleCount": len(FINGERPRINTS), "publishedSourcePath": SOURCE,
        "publishedSourceSha256": SOURCE_SHA256, "schemaPath": SCHEMA,
        "schemaSha256": sha256((ROOT / SCHEMA).read_bytes()),
        "note": "Expectations apply to the selected original CSV row only. Source XPath values and reviewed CSV/TTL differences are preserved; target and mutation bindings are derived test knowledge. Cross-record row mismatches yield one finding per participating property group within a valuation analysis. Other business-rule findings may occur.",
    })
    for path in sorted((ROOT / SCHEMA).parent.glob("*.xsd")):
        node = URIRef(str(SUITE) + ":schema:" + path.name)
        graph.add((SUITE, T.schemaSource, node))
        record(node, {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path.read_bytes())})
    outputs = {}
    for plan in PLANS:
        case = URIRef(str(SUITE) + ":" + plan.rule_id + ":" + plan.name)
        row, governed, differences = rows[plan.rule_id]
        graph.add((SUITE, T.hasCase, case))
        graph.add((case, RDF.type, T.TestCase))
        graph.add((case, T.sourceRule, governed))
        for column, predicate in FIELDS.items():
            graph.add((case, predicate, Literal(row[column])))
        for number, (column, csv_value, ttl_value, reason) in enumerate(differences):
            node = URIRef(str(case) + f":reconciliation:{number}")
            graph.add((case, T.sourceDiscrepancy, node))
            record(node, {
                "sourceColumn": column, "csvValue": csv_value,
                "trackingValue": ttl_value, "reason": reason,
                "csvPath": CSV, "trackingPath": TRACKING,
                "authoritativeSource": CSV,
            })
        root, target, mutation, after, location, changes, additions, removals = prepare(plan, original, schema_document)
        before = target.text if mutation == "text" else etree.tostring(target, encoding="unicode", with_tail=False)
        mutation_path = absolute_path(target)
        record(case, {
            "caseId": plan.name, "scenarioId": "IT-1R13S1",
            "sourceFingerprint": fingerprint(row), "targetXPath": location,
            "mutationXPath": mutation_path, "mutationKind": mutation,
            "beforeValue": before, "afterValue": after,
            "baselinePreparation": plan.name,
        })
        for number, (xpath, old, new) in enumerate(changes):
            node = URIRef(str(case) + f":setup:{number}")
            graph.add((case, T.setupChange, node))
            record(node, {"xpath": xpath, "beforeValue": old, "afterValue": new})
        for xpath in additions:
            graph.add((case, T.addedContextXPath, Literal(xpath)))
        for xpath in removals:
            graph.add((case, T.removedContextXPath, Literal(xpath)))
        for state, count in (("permitted", 0), ("prohibited" if plan.expected else "changed-control", plan.expected)):
            if state != "permitted":
                if mutation == "remove":
                    target.getparent().remove(target)
                else:
                    target.text = after
            observed = oracle(root, plan.rule_id)
            expected = [location] if count else []
            if observed != expected:
                raise ValueError(f"{plan.rule_id}/{plan.name}/{state}: fixture intent differs: {observed} != {expected}")
            relative = f"{FIXTURES}/{plan.rule_id}/{plan.name}-{state}.xml"
            data = serialize_xml(root, relative, schema)
            node = URIRef(str(case) + ":" + state)
            graph.add((case, T.hasFixture, node))
            graph.add((node, RDF.type, T.XMLFixture))
            record(node, {
                "state": state, "path": relative, "sha256": sha256(data),
                "expectedFindingCount": count,
                "expectedViolationKind": "AggregateOrCrossRecordInconsistency",
                "xsdValid": True,
            })
            outputs[relative] = data
    manifest = graph.serialize(format="turtle").encode("utf-8")
    if not isomorphic(graph, Graph().parse(data=manifest.decode("utf-8"), format="turtle")):
        raise ValueError("Manifest Turtle round-trip changed the graph")
    outputs[FIXTURES + "/manifest.ttl"] = manifest
    return outputs, graph


def safe_path(relative):
    portable = PurePosixPath(relative)
    if (
        portable.is_absolute()
        or ".." in portable.parts
        or "\\" in relative
    ):
        raise ValueError(f"Unsafe output path: {relative}")
    path = (ROOT / portable).resolve()
    if not path.is_relative_to((ROOT / FIXTURES).resolve()):
        raise ValueError(f"Output escapes fixture directory: {relative}")
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError(f"Output escapes project: {relative}")
    return path


def existing_manifest():
    path = ROOT / FIXTURES / "manifest.ttl"
    if not path.is_file():
        return None
    graph = Graph().parse(path, format="turtle")
    if str(graph.value(SUITE, T.generatedBy)) != GENERATOR:
        raise ValueError("Existing manifest does not identify this generator")
    return graph


def verify_saved(outputs, graph):
    directory = ROOT / FIXTURES
    if not directory.exists():
        print(
            "No saved corpus yet; plan validated in memory. No files written."
        )
        return
    old = existing_manifest()
    if old is None:
        raise ValueError("Fixture directory exists without its manifest")
    actual_xml = {
        path.relative_to(ROOT).as_posix()
        for path in directory.rglob("*.xml")
    }
    expected_xml = {name for name in outputs if name.endswith(".xml")}
    if actual_xml != expected_xml:
        raise ValueError(
            "Saved XML membership differs from generated corpus"
        )
    for relative, data in outputs.items():
        path = safe_path(relative)
        if not path.is_file():
            raise ValueError(f"Missing saved artifact: {relative}")
        if relative.endswith(".xml") and path.read_bytes() != data:
            raise ValueError(
                f"Saved XML differs from generator: {relative}"
            )
    if not isomorphic(old, graph):
        raise ValueError("Saved manifest differs from generated knowledge")
    print("Saved XML bytes and manifest graph match the generator.")


def write(outputs, replace):
    old = existing_manifest()
    owned = {}
    if old is not None:
        for fixture in old.subjects(RDF.type, T.XMLFixture):
            paths = list(old.objects(fixture, T.path))
            hashes = list(old.objects(fixture, T.sha256))
            if len(paths) != 1 or len(hashes) != 1:
                raise ValueError(
                    "Existing manifest has ambiguous fixture ownership"
                )
            relative = str(paths[0])
            if relative in owned:
                raise ValueError(
                    "Existing manifest contains a duplicate fixture path"
                )
            path = safe_path(relative)
            if (
                not path.is_file()
                or sha256(path.read_bytes()) != str(hashes[0])
            ):
                raise ValueError(
                    f"Existing fixture was changed or is missing: {relative}"
                )
            owned[relative] = str(hashes[0])

    expected_xml = {name for name in outputs if name.endswith(".xml")}
    existing_xml = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / FIXTURES).rglob("*.xml")
    }
    if existing_xml and existing_xml != set(owned):
        raise ValueError("Unowned XML files exist; replacement refused")
    if old is not None and set(owned) != expected_xml:
        raise ValueError(
            "Fixture membership changed; review before replacing corpus"
        )

    # Preflight every output before writing any file.
    for relative, data in outputs.items():
        path = safe_path(relative)
        if path.exists() and path.read_bytes() != data:
            manifest_path = FIXTURES + "/manifest.ttl"
            if (
                not replace
                or old is None
                or (
                    relative != manifest_path
                    and relative not in owned
                )
            ):
                raise ValueError(f"Refusing overwrite: {relative}")

    for relative, data in outputs.items():
        path = safe_path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_bytes() != data:
            path.write_bytes(data)
    print(
        f"Wrote {len(outputs) - 1} schema-valid XML fixtures and manifest.ttl."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--replace-generated", action="store_true")
    args = parser.parse_args()
    if args.replace_generated and not args.write:
        parser.error("--replace-generated requires --write")
    outputs, graph = build()
    print(
        f"Validated {len(PLANS)} case pairs "
        f"for {len(FINGERPRINTS)} source rules."
    )
    if args.write:
        write(outputs, args.replace_generated)
    else:
        verify_saved(outputs, graph)


if __name__ == "__main__":
    main()