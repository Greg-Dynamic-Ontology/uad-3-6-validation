"""Generate XSD-valid IT-1R1S2 outbuilding fixtures and manifest.ttl.

Default: validate in memory only. --write saves the corpus. Replacement mode
only overwrites files whose current hashes still match the old manifest.
"""

import argparse
import hashlib
import os
from copy import deepcopy
from pathlib import Path
from urllib.parse import quote, unquote

from lxml import etree as ET
from rdflib import Graph, Literal, Namespace, RDF
from rdflib.compare import isomorphic


ROOT = Path(os.environ.get("UAD36_PROJECT_ROOT", Path(__file__).resolve().parents[2])).resolve()
OUTPUT = ROOT / "tests/fixtures/it_1/r1/s2"
INVENTORY = ROOT / "data/spreadsheet-rule-category-tracking.ttl"
TEMPLATE = ROOT / "tests/fixtures/it_1/r1/s1/UAD1687/Outbuilding-not-applicable.xml"
TEMPLATE_SHA256 = "0e8ea899ed1d26472d1425fb6029a6067cc2cd6fc114aad5ba448684f8a44d2f"
SCHEMA = ROOT / (
    "chatgpt-sources/sources/schemas/UAD/GSE_UAD_3.6.0_v1.3/Combined/"
    "GSE_UAD_3.6.0_v1.3.xsd"
)
URI = "http://www.mismo.org/residential/2009/schemas"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
NS = {"m": URI}
M = Namespace("urn:uad36:test-manifest:vocab:")
C = Namespace("urn:uad36:test-manifest:IT-1R1S2:")
T = Namespace("urn:uad36:work-tracking:vocab:")
S = Namespace("urn:uad36:work-tracking:scenario:")
BASE = Namespace("urn:uad36:work-tracking:")
RULE_IDS = ("UAD1055", "UAD1059", "UAD1083", "UAD1095", "UAD1096")
TARGETS = {
    "UAD1055": ("IMPROVEMENT_DETAIL", "HeatingSystemExistsIndicator", "true"),
    "UAD1059": ("OUTBUILDING/OUTBUILDING_UTILITIES/OUTBUILDING_UTILITY", "UtilityTypeOtherDescription", "Municipal service"),
    "UAD1083": ("STRUCTURE/STRUCTURE_DETAIL", "StructureAreaMeasure", "120"),
    "UAD1095": ("STRUCTURE/STRUCTURE_DETAIL", "StructureExcludingVehicleStorageAndADUFinishedAreaMeasure", "90"),
    "UAD1096": ("STRUCTURE/STRUCTURE_DETAIL", "StructureExcludingVehicleStorageAndADUUnfinishedAreaMeasure", "30"),
}
AREA_TARGETS = {"UAD1083", "UAD1095", "UAD1096"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def single(graph, subject, predicate):
    values = list(graph.objects(subject, predicate))
    if len(values) != 1:
        raise ValueError(f"Expected one RDF value: {subject} {predicate}; found {len(values)}")
    return values[0]


def one(root, path):
    nodes = root.findall(path, NS)
    if len(nodes) != 1:
        raise ValueError(f"Expected one XML node at {path}; found {len(nodes)}")
    return nodes[0]


def safe_target(relative):
    target = (OUTPUT / relative).resolve()
    if not target.is_relative_to(OUTPUT.resolve()):
        raise ValueError(f"Artifact path escapes output directory: {relative}")
    return target


def build():
    if digest(TEMPLATE.read_bytes()) != TEMPLATE_SHA256:
        raise ValueError("Reviewed outbuilding template changed; inspect before regeneration.")
    parser = ET.XMLParser(resolve_entities=False, no_network=True)
    schema_doc = ET.parse(str(SCHEMA), parser)
    schema = ET.XMLSchema(schema_doc)
    xs = {"x": "http://www.w3.org/2001/XMLSchema"}
    order = {}
    required_containers = {}
    for complex_type in schema_doc.xpath("//x:complexType[@name]", namespaces=xs):
        children = complex_type.xpath("./x:sequence/x:element[@name]", namespaces=xs)
        if children:
            owner = complex_type.get("name")
            order[owner] = {item.get("name"): i for i, item in enumerate(children)}
            required_containers[owner] = [
                item.get("name") for item in children
                if int(item.get("minOccurs", "1")) > 0
                and item.get("type") == item.get("name")
                and item.get("name", "").isupper()
            ]

    def insert(parent, node):
        owner, name = ET.QName(parent).localname, ET.QName(node).localname
        ranks = order.get(owner, {})
        if name not in ranks:
            raise ValueError(f"Schema order not found for {owner}/{name}")
        for i, child in enumerate(parent):
            if isinstance(child.tag, str):
                child_name = ET.QName(child).localname
                if child_name not in ranks:
                    raise ValueError(f"Unknown schema child {owner}/{child_name}")
                if ranks[child_name] > ranks[name]:
                    parent.insert(i, node)
                    return
        parent.append(node)

    def ensure(parent, path):
        for name in path.split("/"):
            existing = parent.findall(f"{{{URI}}}{name}")
            if len(existing) > 1:
                raise ValueError(f"Ambiguous XML context: {path}")
            if existing:
                parent = existing[0]
            else:
                node = ET.Element(f"{{{URI}}}{name}")
                insert(parent, node)
                parent = node
        return parent

    def scalar(parent, name, value):
        found = parent.findall(f"{{{URI}}}{name}")
        if len(found) > 1:
            raise ValueError(f"Ambiguous scalar: {name}")
        for node in found:
            parent.remove(node)
        if value is None:
            return
        node = ET.Element(f"{{{URI}}}{name}")
        node.text = value
        if name in AREA_NAMES:
            node.set("AreaUnitOfMeasureType", "SquareFeet")
        insert(parent, node)

    def fill_required_containers(node):
        owner = ET.QName(node).localname
        for name in required_containers.get(owner, []):
            if not node.findall(f"{{{URI}}}{name}"):
                insert(node, ET.Element(f"{{{URI}}}{name}"))
        for child in list(node):
            if isinstance(child.tag, str):
                fill_required_containers(child)

    AREA_NAMES = {target for rid, (_, target, _) in TARGETS.items() if rid in AREA_TARGETS}
    original = ET.fromstring(TEMPLATE.read_bytes(), parser)
    schema.assertValid(original)
    property_path = ".//m:PROPERTIES/m:PROPERTY[@ValuationUseType='SubjectProperty']"
    prop = one(original, property_path)
    improvements = one(prop, "m:IMPROVEMENTS")
    templates = improvements.findall("m:IMPROVEMENT", NS)
    if len(templates) != 1:
        raise ValueError("Reviewed template must have exactly one subject improvement.")
    improvement_template = deepcopy(templates[0])

    inventory = Graph().parse(INVENTORY, format="turtle")
    scenario = S.it_1_r1_s2
    scenario_rules = set(inventory.objects(scenario, T.coversRule))
    family_rules = set(inventory.subjects(T.fixtureFamily, BASE.fixtureFamilyOutbuilding))
    selected = scenario_rules & family_rules
    source_by_id = {}
    for row in selected:
        rule_id = str(single(inventory, row, T.ruleId))
        if rule_id in source_by_id:
            raise ValueError(f"Duplicate selected rule: {rule_id}")
        source_by_id[rule_id] = row
    if set(source_by_id) != set(RULE_IDS):
        raise ValueError("Outbuilding family differs from reviewed 5-rule tracker selection.")

    graph = Graph()
    graph.bind("m", M)
    graph.bind("case", C)
    artifacts = {}
    graph.add((C.manifest, RDF.type, M.Manifest))
    for predicate, value in [
        (M.scenarioId, "IT-1R1S2"),
        (M.fixtureFamily, "outbuilding"),
        (M.caseCount, 20),
        (M.coverage, "Five outbuilding rules; four correlated-instance cases per rule."),
    ]:
        graph.add((C.manifest, predicate, Literal(value)))
    graph.add((C.manifest, M.validationSchema, C.schema))
    graph.add((C.schema, RDF.type, M.SourceArtifact))
    graph.add((C.schema, M.path, Literal(SCHEMA.relative_to(ROOT).as_posix())))
    graph.add((C.schema, M.sha256, Literal(digest(SCHEMA.read_bytes()))))

    cases = [
        ("two-applicable-missing", "applicable_missing", (True, True), (None, None)),
        ("one-missing-one-supplied", "applicable_missing", (True, True), (None, "supplied")),
        ("both-applicable-supplied", "applicable_supplied", (True, True), ("supplied", "supplied")),
        ("conditions-split-across-instances", "not_applicable", ("split", "split"), (None, None)),
    ]

    for rule_id in RULE_IDS:
        source = source_by_id[rule_id]
        target_parent, target_name, target_value = TARGETS[rule_id]
        source_logic = str(single(inventory, source, T.ruleLogic))
        source_row = int(single(inventory, source, T.sourceRow))
        source_uid = str(single(inventory, source, T.sourceUniqueIdCell))
        severity = str(single(inventory, source, T.severity)).casefold()
        target_path = str(single(inventory, source, T.xpath))
        expected_target_suffix = {
            "UAD1055": "IMPROVEMENT_DETAIL/",
            "UAD1059": "OUTBUILDING_UTILITIES/OUTBUILDING_UTILITY/",
            "UAD1083": "STRUCTURE/STRUCTURE_DETAIL/",
            "UAD1095": "STRUCTURE/STRUCTURE_DETAIL/",
            "UAD1096": "STRUCTURE/STRUCTURE_DETAIL/",
        }[rule_id]
        if not target_path.endswith(expected_target_suffix):
            raise ValueError(f"Unexpected source XPath for {rule_id}: {target_path}")

        for case_name, state, condition_mode, supply_modes in cases:
            root = deepcopy(original)
            prop = one(root, property_path)
            container = one(prop, "m:IMPROVEMENTS")
            for old in container.findall("m:IMPROVEMENT", NS):
                container.remove(old)
            instances = []
            expected_locations = []
            checks = []
            for index in range(2):
                improvement = deepcopy(improvement_template)
                insert(container, improvement)
                detail = ensure(improvement, "IMPROVEMENT_DETAIL")
                # Set each instance's own applicability inputs. The split case
                # deliberately ensures no individual Improvement meets all inputs.
                if condition_mode[index] == "split":
                    # Split ImprovementType and real-property conditions across
                    # different repeated Improvement owners.
                    kind = "Outbuilding" if index == 0 else "Dwelling"
                    real_property = "false" if index == 0 else "true"
                else:
                    kind, real_property = "Outbuilding", "true"
                scalar(detail, "ImprovementType", kind)
                scalar(detail, "OutbuildingRealPropertyIndicator", real_property)
                context_parts = ["IMPROVEMENT", f"[{index + 1}]"]
                if rule_id == "UAD1055":
                    structure_detail = ensure(improvement, "STRUCTURE/STRUCTURE_DETAIL")
                    living_count = "1" if condition_mode[index] == "split" and index == 0 else "0"
                    scalar(structure_detail, "LivingUnitCount", living_count)
                    owner = detail
                elif rule_id == "UAD1059":
                    owner = ensure(improvement, "OUTBUILDING/OUTBUILDING_UTILITIES/OUTBUILDING_UTILITY")
                    utility_type = "Other" if condition_mode[index] != "split" or index == 1 else "Water"
                    scalar(owner, "UtilityType", utility_type)
                else:
                    owner = ensure(improvement, "STRUCTURE/STRUCTURE_DETAIL")
                supplied = supply_modes[index] == "supplied"
                # The split cases keep the target absent, but their conditions
                # are separated so no instance is applicable.
                value = target_value if supplied else None
                scalar(owner, target_name, value)
                parent_xml_path = "/".join("m:" + part for part in target_parent.split("/"))
                target_location = (
                    "//m:VALUATION_ANALYSIS/m:PROPERTIES/"
                    "m:PROPERTY[@ValuationUseType='SubjectProperty']/"
                    f"m:IMPROVEMENTS/m:IMPROVEMENT[{index + 1}]/"
                    f"{parent_xml_path}/"
                    f"m:{target_name}"
                )
                if value is None and (state == "applicable_missing" and condition_mode[index] is True):
                    expected_locations.append(target_location)
                details_path = (
                    ".//m:VALUATION_ANALYSIS/m:PROPERTIES/"
                    "m:PROPERTY[@ValuationUseType='SubjectProperty']/"
                    f"m:IMPROVEMENTS/m:IMPROVEMENT[{index + 1}]/m:IMPROVEMENT_DETAIL"
                )
                checks.extend([
                    (details_path + "/m:ImprovementType", 1, kind),
                    (details_path + "/m:OutbuildingRealPropertyIndicator", 1, real_property),
                    ("." + target_location, 0 if value is None else 1, value),
                ])
                if rule_id == "UAD1055":
                    checks.append((
                        ".//m:VALUATION_ANALYSIS/m:PROPERTIES/"
                        "m:PROPERTY[@ValuationUseType='SubjectProperty']/"
                        f"m:IMPROVEMENTS/m:IMPROVEMENT[{index + 1}]/"
                        "m:STRUCTURE/m:STRUCTURE_DETAIL/m:LivingUnitCount",
                        1,
                        living_count,
                    ))
                if rule_id == "UAD1059":
                    checks.append((
                        ".//m:VALUATION_ANALYSIS/m:PROPERTIES/"
                        "m:PROPERTY[@ValuationUseType='SubjectProperty']/"
                        f"m:IMPROVEMENTS/m:IMPROVEMENT[{index + 1}]/"
                        "m:OUTBUILDING/m:OUTBUILDING_UTILITIES/"
                        "m:OUTBUILDING_UTILITY/m:UtilityType",
                        1,
                        utility_type,
                    ))
                instances.append(improvement)

            location = quote(Path(os.path.relpath(SCHEMA, safe_target(f"{rule_id}/{case_name}.xml").parent)).as_posix(), safe="/.")
            resolved_schema = (safe_target(f"{rule_id}/{case_name}.xml").parent / unquote(location)).resolve()
            if resolved_schema != SCHEMA.resolve():
                raise ValueError("Generated relative schema reference does not resolve.")
            root.set(f"{{{XSI}}}schemaLocation", f"{URI} {location}")
            ET.cleanup_namespaces(root)
            content = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            parsed = ET.fromstring(content, parser)
            try:
                schema.assertValid(parsed)
            except ET.DocumentInvalid as error:
                raise ValueError(f"{rule_id}/{case_name}.xml is XSD-invalid: {error}") from error
            for check_path, count, expected_text in checks:
                found = parsed.findall(check_path, NS)
                if len(found) != count:
                    raise ValueError(f"{rule_id}/{case_name}: wrong node count at {check_path}")
                if expected_text is not None and [node.text for node in found] != [expected_text]:
                    raise ValueError(f"{rule_id}/{case_name}: wrong value at {check_path}")

            relative = f"{rule_id}/{case_name}.xml"
            artifacts[relative] = content
            case = C[f"{rule_id}-{case_name}"]
            graph.add((C.manifest, M.case, case))
            graph.add((case, RDF.type, M.TestCase))
            for predicate, value in [
                (M.caseId, f"IT-1R1S2-{rule_id}-{case_name}"),
                (M.fixtureFamily, "outbuilding"),
                (M.ruleId, rule_id),
                (M.sourceRow, source_row),
                (M.sourceUniqueId, source_uid),
                (M.sourceRuleLogic, source_logic),
                (M.state, state),
                (M.xmlFile, relative),
                (M.xmlSha256, digest(content)),
                (M.expectedFindingCount, len(expected_locations)),
            ]:
                graph.add((case, predicate, Literal(value)))
            for check_index, (path, count, expected_text) in enumerate(checks, 1):
                check = C[f"{rule_id}-{case_name}-check-{check_index}"]
                graph.add((case, M.fixtureCheck, check))
                graph.add((check, RDF.type, M.FixtureCheck))
                graph.add((check, M.path, Literal(path)))
                graph.add((check, M["count"], Literal(count)))
                if expected_text is not None:
                    graph.add((check, M.expectedText, Literal(expected_text)))
            for finding_index, finding_path in enumerate(expected_locations, 1):
                finding = C[f"{rule_id}-{case_name}-finding-{finding_index}"]
                graph.add((case, M.expectedFinding, finding))
                for predicate, value in [
                    (M.ruleId, rule_id),
                    (M.severity, severity),
                    (M.dataLocation, finding_path),
                    (M.violationKind, "MissingRequiredValue"),
                ]:
                    graph.add((finding, predicate, Literal(value)))

    if len(artifacts) != 20:
        raise ValueError(f"Expected 20 XML fixtures; generated {len(artifacts)}")
    graph.add((C.manifest, M.caseCount, Literal(20)))
    turtle = graph.serialize(format="turtle", encoding="utf-8")
    parsed_graph = Graph().parse(data=turtle, format="turtle")
    if not isomorphic(graph, parsed_graph):
        raise ValueError("Manifest Turtle round-trip changed RDF content.")
    artifacts["manifest.ttl"] = turtle
    return artifacts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--replace-generated", action="store_true")
    args = parser.parse_args()
    if args.replace_generated and not args.write:
        parser.error("--replace-generated requires --write")
    artifacts = build()
    xml_count = len(artifacts) - 1
    if not args.write:
        print(f"Validated {xml_count} schema-valid outbuilding XML cases and manifest.ttl.")
        print("No files written. Validator RED/GREEN tests were not run.")
        return

    old_manifest_path = OUTPUT / "manifest.ttl"
    known_hashes = {}
    old_bytes = None
    if args.replace_generated and old_manifest_path.exists():
        old_bytes = old_manifest_path.read_bytes()
        old = Graph().parse(data=old_bytes, format="turtle")
        for case in old.subjects(RDF.type, M.TestCase):
            name = str(single(old, case, M.xmlFile))
            safe_target(name)
            if name in known_hashes:
                raise ValueError(f"Duplicate old manifest file: {name}")
            known_hashes[name] = str(single(old, case, M.xmlSha256))
    removed = set(known_hashes) - set(artifacts)
    if removed:
        raise ValueError(f"Generation would omit prior generated cases: {sorted(removed)}")
    for name, content in artifacts.items():
        target = safe_target(name)
        if not target.exists() or target.read_bytes() == content:
            continue
        if not args.replace_generated:
            raise FileExistsError(f"Existing artifact differs: {target}")
        if name == "manifest.ttl":
            if old_bytes is None or target.read_bytes() != old_bytes:
                raise ValueError("Existing manifest changed during preflight.")
        elif digest(target.read_bytes()) != known_hashes.get(name):
            raise ValueError(f"Preserving modified or unrecognized fixture: {target}")
    for name, content in artifacts.items():
        target = safe_target(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_bytes() != content:
            target.write_bytes(content)
    print(f"Wrote and verified {xml_count} schema-valid outbuilding XML fixtures and manifest.ttl.")
    print("Validator RED/GREEN tests were not run.")


if __name__ == "__main__":
    main()


