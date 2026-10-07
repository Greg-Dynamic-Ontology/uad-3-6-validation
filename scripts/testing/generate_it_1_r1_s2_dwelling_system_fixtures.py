"""Build the IT-1R1S2-Slice-02 dwelling-system corpus.

Default: validate in memory. --write creates fixtures and manifest.
Existing differing files are never overwritten. No production imports.
"""
import argparse
import csv
import hashlib
import os
from copy import deepcopy
from pathlib import Path

from lxml import etree as ET
from rdflib import Graph, Literal, Namespace, RDF
from rdflib.compare import isomorphic

ROOT = Path(os.environ.get("UAD36_PROJECT_ROOT", Path(__file__).resolve().parents[2])).resolve()
OUTPUT = ROOT / "tests/fixtures/it_1/r1/s2/dwelling-system"
TEMPLATE_REL = "tests/fixtures/it_1/r1/s1/UAD1687/Outbuilding-not-applicable.xml"
TEMPLATE_SHA256 = "0e8ea899ed1d26472d1425fb6029a6067cc2cd6fc114aad5ba448684f8a44d2f"
SCHEMA_REL = "chatgpt-sources/sources/schemas/UAD/GSE_UAD_3.6.0_v1.3/Combined/GSE_UAD_3.6.0_v1.3.xsd"
URI = "http://www.mismo.org/residential/2009/schemas"
NS = {"m": URI}
M = Namespace("urn:uad36:test-manifest:vocab:")
C = Namespace("urn:uad36:test-manifest:IT-1R1S2:dwelling-system:")
T = Namespace("urn:uad36:work-tracking:vocab:")
S = Namespace("urn:uad36:work-tracking:scenario:")
B = Namespace("urn:uad36:work-tracking:")
PROPERTY = ".//m:VALUATION_ANALYSIS/m:PROPERTIES/m:PROPERTY[@ValuationUseType='SubjectProperty']"
REPORT = ".//m:VALUATION_ANALYSIS/m:VALUATION_REPORT"
COMPONENT = "STRUCTURE/STRUCTURE_COMPONENTS/STRUCTURE_COMPONENT/STRUCTURE_COMPONENT_DETAIL"
DETAIL = "STRUCTURE/STRUCTURE_DETAIL"
ANALYSIS = "STRUCTURE/STRUCTURE_ANALYSES/STRUCTURE_ANALYSIS/STRUCTURE_ANALYSIS_DETAIL"
METHOD = "STRUCTURE/CONSTRUCTION_METHODS/CONSTRUCTION_METHOD/ConstructionMethodType"
# Scope, condition path, applicable value, non-applicable value. Every binding
# was reviewed against the CSV and the governed XML model, not validator output.
SPECS = {
    "UAD1098": ("SYSTEM/SYSTEM_DETAIL", "CoreHeatingSystemBelowGradeIndicator", "false", [
        ("improvement", "SYSTEM/HEATING_SYSTEMS/HEATING_SYSTEM/HeatingSystemType", "ForcedWarmAir", "None")]),
}
EXPECTED_LOGIC = {
    "UAD1098": 'If ImprovementType = "Dwelling" and HeatingSystemType <> "None", and CoreHeatingSystemBelowGradeIndicator is not provided in SYSTEM_DETAIL for a given instance of IMPROVEMENT',
}
SOURCE_FIELDS = {
    "Unique ID": T.sourceUniqueIdCell, "Primary Data Element": T.primaryDataElement,
    "Message ID": T.ruleId, "Message Text": T.messageText, "Rule Logic": T.ruleLogic,
    "Severity": T.severity, "Property Affected": T.propertyAffected, " xPath": T.xpath,
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def single(graph, node, predicate):
    values = list(graph.objects(node, predicate))
    if len(values) != 1:
        raise ValueError(f"Expected exactly one {predicate} on {node}")
    return values[0]


def one(root, path):
    values = root.findall(path, NS)
    if len(values) != 1:
        raise ValueError(f"Expected exactly one XML node at {path}; got {len(values)}")
    return values[0]


def xmlpath(path):
    return "/".join("m:" + part for part in path.split("/"))


def build():
    template = ROOT / TEMPLATE_REL
    original_bytes = template.read_bytes()
    if digest(original_bytes) != TEMPLATE_SHA256:
        raise ValueError("Reviewed base fixture changed; review before regenerating.")
    parser = ET.XMLParser(resolve_entities=False, no_network=True)
    schema_path = ROOT / SCHEMA_REL
    schema_doc = ET.parse(str(schema_path), parser)
    schema = ET.XMLSchema(schema_doc)
    xs = {"x": "http://www.w3.org/2001/XMLSchema"}
    order = {}
    for typ in schema_doc.xpath("//x:complexType[@name]", namespaces=xs):
        children = typ.xpath("./x:sequence/x:element", namespaces=xs)
        if children:
            order[typ.get("name")] = {n.get("name"): i for i, n in enumerate(children)}

    def insert(parent, name):
        ranks = order.get(ET.QName(parent).localname, {})
        if name not in ranks:
            raise ValueError(f"Schema has no ordered child {parent.tag}/{name}")
        node = ET.Element(f"{{{URI}}}{name}")
        for i, child in enumerate(parent):
            if isinstance(child.tag, str) and ranks[ET.QName(child).localname] > ranks[name]:
                parent.insert(i, node)
                return node
        parent.append(node)
        return node

    def ensure(parent, path):
        for name in path.split("/"):
            found = parent.findall(f"{{{URI}}}{name}")
            if len(found) > 1:
                raise ValueError(f"Ambiguous context {path}")
            parent = found[0] if found else insert(parent, name)
        return parent

    def scalar(parent, path, value):
        parts = path.split("/")
        owner = ensure(parent, "/".join(parts[:-1])) if len(parts) > 1 else parent
        for node in owner.findall(f"{{{URI}}}{parts[-1]}"):
            owner.remove(node)
        if value is not None:
            insert(owner, parts[-1]).text = value

    inventory = Graph().parse(ROOT / "data/spreadsheet-rule-category-tracking.ttl")
    family = set(inventory.subjects(T.fixtureFamily, B.fixtureFamilyDwellingSystem))
    members = set(inventory.objects(S.it_1_r1_s2, T.coversRule))
    if not family <= members or len(family) != 1:
        raise ValueError("Expected one dwelling-system row in IT-1R1S2.")
    selected = {str(single(inventory, n, T.ruleId)): n for n in family}
    if set(selected) != set(SPECS):
        raise ValueError("Tracker family membership differs from the reviewed ID.")
    with (ROOT / "data/data-constraints.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    csv_rows = {}
    for rid, node in selected.items():
        matches = [r for r in rows if r["Message ID"] == rid]
        if len(matches) != 1:
            raise ValueError(f"CSV must contain exactly one {rid}")
        row = matches[0]
        for column, predicate in SOURCE_FIELDS.items():
            if row[column] != str(single(inventory, node, predicate)):
                raise ValueError(f"CSV/tracker disagreement: {rid} {column}")
        parent, target, _, conditions = SPECS[rid]
        expected_path = "../VALUATION_ANALYSIS/PROPERTIES/PROPERTY/IMPROVEMENTS/IMPROVEMENT/" + parent + "/"
        if row[" xPath"] != expected_path or row["Primary Data Element"] != target:
            raise ValueError(f"Review changed source binding for {rid}")
        if 'ImprovementType = "Dwelling"' not in row["Rule Logic"]:
            raise ValueError(f"Review changed dwelling applicability for {rid}")
        if row["Rule Logic"] != EXPECTED_LOGIC[rid]:
            raise ValueError(f"Review changed source logic for {rid}")
        csv_rows[rid] = row

    original = ET.fromstring(original_bytes, parser)
    schema.assertValid(original)
    original_improvement = one(original, PROPERTY + "/m:IMPROVEMENTS/m:IMPROVEMENT")
    # Keep the reviewed minimal improvement template. Each case creates its
    # explicit structures; comparative properties and the report stay intact.
    graph = Graph()
    graph.bind("m", M); graph.bind("case", C)
    graph.add((C.manifest, RDF.type, M.Manifest))
    graph.add((C.manifest, M.scenarioId, Literal("IT-1R1S2")))
    graph.add((C.manifest, M.sliceId, Literal("IT-1R1S2-Slice-02")))
    graph.add((C.manifest, M.fixtureFamily, Literal("dwelling-system")))
    graph.add((C.manifest, M.validationSchema, C.schema))
    graph.add((C.schema, M.path, Literal(SCHEMA_REL)))
    graph.add((C.schema, M.sha256, Literal(digest(schema_path.read_bytes()))))
    graph.add((C.manifest, M.derivedFrom, C.template))
    graph.add((C.template, M.path, Literal(TEMPLATE_REL)))
    graph.add((C.template, M.sha256, Literal(TEMPLATE_SHA256)))
    artifacts = {}
    # Each tuple explicitly defines supply and applicability, independent of
    # the application evaluator. Mixed ownership must yield just one finding.
    modes = [
        ("two-missing", "applicable_missing", (False, False), (True, True)),
        ("first-missing", "applicable_missing", (False, True), (True, True)),
        ("second-missing", "applicable_missing", (True, False), (True, True)),
        ("both-supplied", "applicable_supplied", (True, True), (True, True)),
        ("condition-false", "not_applicable", (False, False), (False, False)),
        ("heated-and-unheated", "applicable_missing", (False, False), (True, False)),
        ("unheated-and-heated", "applicable_missing", (False, False), (False, True)),
        ("dwelling-and-outbuilding", "applicable_missing", (False, False), (True, False)),
    ]
    for rid, (parent_path, target_name, target_value, conditions) in SPECS.items():
        variants = [None]
        if rid == "UAD1077": variants = ["Windows", "Other"]
        if rid == "UAD1088": variants = ["Modular", "OnFrameModular"]
        row, source = csv_rows[rid], selected[rid]
        for variant in variants:
            for mode, state, supplied, applicable in modes:
                name = (variant + "-" if variant else "") + mode
                root = deepcopy(original)
                prop = one(root, PROPERTY)
                report = one(root, REPORT)
                container = one(prop, "m:IMPROVEMENTS")
                for item in list(container): container.remove(item)
                checks, locations = [], []
                checks.append((PROPERTY + "/m:IMPROVEMENTS/m:IMPROVEMENT", 2, None))
                for index in range(2):
                    imp = deepcopy(original_improvement)
                    container.append(imp)
                    imp_path = PROPERTY + f"/m:IMPROVEMENTS/m:IMPROVEMENT[{index + 1}]"
                    kind = "Outbuilding" if mode == "dwelling-and-outbuilding" and index == 1 else "Dwelling"
                    scalar(imp, "IMPROVEMENT_DETAIL/ImprovementType", kind)
                    checks.append((imp_path + "/m:IMPROVEMENT_DETAIL/m:ImprovementType", 1, kind))
                    for scope, condition_path, positive, negative in conditions:
                        if variant and scope == "improvement": positive = variant
                        # In the negative case turn off the final condition;
                        # earlier condition inputs remain supplied and true.
                        val = negative if (mode == "condition-false" or (mode == "heated-and-unheated" and index == 1) or (mode == "unheated-and-heated" and index == 0)) and condition_path == conditions[-1][1] else positive
                        owner, base = {"property":(prop, PROPERTY), "report":(report, REPORT), "improvement":(imp, imp_path)}[scope]
                        scalar(owner, condition_path, val)
                        check = (base + "/" + xmlpath(condition_path), 1, val)
                        if check not in checks: checks.append(check)
                    # Supply an existing governed owner even when its scalar
                    # is missing: absence of a container is a different case.
                    owner = ensure(imp, parent_path)
                    val = target_value if supplied[index] else None
                    if rid == "UAD1091" and val: val = f"Dwelling-{index + 1}"
                    scalar(owner, target_name, val)
                    location = imp_path[1:] + "/" + xmlpath(parent_path) + "/m:" + target_name
                    checks.append((imp_path + "/" + xmlpath(parent_path), 1, None))
                    checks.append(("." + location, 1 if val is not None else 0, val))
                    if applicable[index] and not supplied[index]: locations.append(location)
                # Explicit schema validation below uses the governed XSD;
                # remove the copied location hint, which belonged to the base directory.
                root.attrib.pop("{http://www.w3.org/2001/XMLSchema-instance}schemaLocation", None)
                content = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                parsed = ET.fromstring(content, parser)
                schema.assertValid(parsed)
                for path, count, expected in checks:
                    nodes = parsed.findall(path, NS)
                    if len(nodes) != count or (expected is not None and [n.text for n in nodes] != [expected]):
                        raise ValueError(f"Fixture integrity failed: {rid}/{name}: {path}")
                relative = f"{rid}/{name}.xml"
                artifacts[relative] = content
                case = C[f"{rid}-{name}"]
                graph.add((C.manifest, M.case, case))
                graph.add((case, RDF.type, M.TestCase))
                for pred, val in [(M.caseId, f"IT-1R1S2-Slice-02-{rid}-{name}"), (M.ruleId,rid),
                    (M.sourceRow,int(single(inventory,source,T.sourceRow))),
                    (M.sourceUniqueId,row["Unique ID"]), (M.sourceRuleLogic,row["Rule Logic"]),
                    (M.state,state), (M.xmlFile,relative), (M.xmlSha256,digest(content)),
                    (M.expectedFindingCount,len(locations))]:
                    graph.add((case,pred,Literal(val)))
                for i,(path,count,expected) in enumerate(checks):
                    check = C[f"{rid}-{name}-check-{i}"]
                    graph.add((case,M.fixtureCheck,check))
                    graph.add((check,M.path,Literal(path)))
                    graph.add((check,M["count"],Literal(count)))
                    if expected is not None: graph.add((check,M.expectedText,Literal(expected)))
                for i,path in enumerate(locations):
                    finding = C[f"{rid}-{name}-finding-{i}"]
                    graph.add((case,M.expectedFinding,finding))
                    for pred,val in [(M.ruleId,rid),(M.severity,row["Severity"].casefold()),
                        (M.dataLocation,path),(M.violationKind,"MissingRequiredValue")]:
                        graph.add((finding,pred,Literal(val)))
    if len(artifacts) != 8: raise ValueError("Expected 8 reviewed cases")
    graph.add((C.manifest,M.caseCount,Literal(len(artifacts))))
    data = graph.serialize(format="turtle",encoding="utf-8")
    if not isomorphic(graph,Graph().parse(data=data,format="turtle")):
        raise ValueError("Manifest round-trip mismatch")
    artifacts["manifest.ttl"] = data
    return artifacts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write",action="store_true")
    args = parser.parse_args()
    artifacts = build()
    if not args.write:
        print("Validated 8 schema-valid XML cases and manifest. No files written.")
        return
    output = OUTPUT.resolve()
    for name, data in artifacts.items():
        target = (output/name).resolve()
        if not target.is_relative_to(output): raise ValueError("Invalid output path")
        if target.exists() and target.read_bytes() != data:
            raise FileExistsError(f"Preserving existing differing file: {target}")
    for name,data in artifacts.items():
        target = output/name
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists(): target.write_bytes(data)
        if target.read_bytes() != data: raise ValueError(f"Write verification failed: {target}")
    print(f"Saved 8 XML cases and manifest to {output}")
    print("Production behavioral tests have not been run by this generator.")


if __name__ == "__main__":
    main()
