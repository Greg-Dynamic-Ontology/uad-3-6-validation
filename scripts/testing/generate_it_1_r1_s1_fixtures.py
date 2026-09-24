"""Generate schema-valid IT-1R1S1 XML cases and manifest.ttl.

Default: verify in memory only.
--write: save new artifacts.
--write --replace-generated: replace only artifacts matching the old manifest.
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


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "tests/fixtures/it_1/r1/s1"
INVENTORY = ROOT / "data/spreadsheet-rule-category-tracking.ttl"
BASELINE = ROOT / (
    "data/uad36-test-suite/tests/fixtures/required_data/"
    "baseline/SF1_Appraisal_v1.4.xml"
)
BASELINE_HASH = (
    "47509c23bcf28c3abb9c57e00a3f93cf52ed"
    "38fec3862d7cda24bffd6bca5be9"
)
SCHEMA = ROOT / (
    "specs/UAD/GSE_UAD_3.6.0_v1.3/Combined/"
    "GSE_UAD_3.6.0_v1.3.xsd"
)

URI = "http://www.mismo.org/residential/2009/schemas"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
NS = {"m": URI}
M = Namespace("urn:uad36:test-manifest:vocab:")
C = Namespace("urn:uad36:test-manifest:IT-1R1S1:")
T = Namespace("urn:uad36:work-tracking:vocab:")
S = Namespace("urn:uad36:work-tracking:scenario:")
B = Namespace("urn:uad36:work-tracking:")

SUBJECT = (
    ".//m:VALUATION_ANALYSIS/m:PROPERTIES/"
    "m:PROPERTY[@ValuationUseType='SubjectProperty']"
)
DETAIL = SUBJECT + "/m:PROPERTY_DETAIL"
PROJECT = SUBJECT + "/m:PROJECT/m:PROJECT_DETAIL"
SITE = SUBJECT + "/m:SITE/m:SITE_DETAIL"
RENT = SUBJECT + "/m:PROPERTY_GROUND_RENT"
IMPROVEMENTS = SUBJECT + "/m:IMPROVEMENTS"

LOGIC = {
    "UAD1021": (
        'If (PropertyInProjectIndicator = "false" or '
        'ProjectLegalStructureType = "Condominium"), '
        "and PropertyEstateType is not provided"
    ),
    "UAD1024": (
        'If PropertyEstateType = "Leasehold" and '
        'LandOwnedInCommonIndicator = "false", '
        "and PropertyGroundLeaseAnnualAmount is not provided"
    ),
    "UAD1054": (
        'If ImprovementType = "Dwelling", and '
        "PropertyStructureBuiltYearEstimatedIndicator is not provided "
        "in a given instance of IMPROVEMENT_DETAIL"
    ),
}

# Explicit source-derived examples; no validator computes expectations.
# Name, project indicator, project type, dependent value, violation.
OR_CASES = [
    ("neither-missing", "true", "Cooperative", None, False),
    ("left-only-missing", "false", "Cooperative", None, True),
    ("right-only-missing", "true", "Condominium", None, True),
    ("both-missing", "false", "Condominium", None, True),
    ("left-only-supplied", "false", "Cooperative", "FeeSimple", False),
    ("right-only-supplied", "true", "Condominium", "FeeSimple", False),
    ("both-supplied", "false", "Condominium", "FeeSimple", False),
]

# Name, estate type, common-land indicator, dependent value, violation.
AND_CASES = [
    ("neither-missing", "FeeSimple", "true", None, False),
    ("left-only-missing", "Leasehold", "true", None, False),
    ("right-only-missing", "FeeSimple", "false", None, False),
    ("both-missing", "Leasehold", "false", None, True),
    ("both-supplied", "Leasehold", "false", "1200", False),
]

# Name, ordered (improvement type, dependent value), deficient positions.
SCOPE_CASES = [
    ("outbuilding-missing", [("Outbuilding", None)], []),
    ("dwelling-missing", [("Dwelling", None)], [1]),
    ("dwelling-supplied", [("Dwelling", "false")], []),
    (
        "first-dwelling-missing-second-supplied",
        [("Dwelling", None), ("Dwelling", "false")],
        [1],
    ),
    (
        "first-dwelling-supplied-second-missing",
        [("Dwelling", "false"), ("Dwelling", None)],
        [2],
    ),
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def single(graph, subject, predicate):
    values = list(graph.objects(subject, predicate))
    if len(values) != 1:
        raise ValueError(f"Expected one value: {subject} {predicate}")
    return values[0]


def one(root, path):
    nodes = root.findall(path, NS)
    if len(nodes) != 1:
        raise ValueError(
            f"Expected one XML node: {path}; found {len(nodes)}"
        )
    return nodes[0]


def target_path(relative):
    target = (OUTPUT / relative).resolve()
    if not target.is_relative_to(OUTPUT.resolve()):
        raise ValueError(f"Output escapes fixture directory: {relative}")
    return target


def build():
    parser = ET.XMLParser(resolve_entities=False, no_network=True)
    schema_doc = ET.parse(str(SCHEMA), parser)
    schema = ET.XMLSchema(schema_doc)
    xs = {"x": "http://www.w3.org/2001/XMLSchema"}

    # Obtain order from the schema rather than guessing insertion points.
    orders = {}
    for definition in schema_doc.xpath(
        "//x:complexType[@name]", namespaces=xs
    ):
        children = definition.xpath(
            "./x:sequence/x:element[@name]", namespaces=xs
        )
        if children:
            orders[definition.get("name")] = {
                child.get("name"): index
                for index, child in enumerate(children)
            }

    def insert(parent, node):
        # These fixture contexts use same-named complex types in this XSD.
        parent_name = ET.QName(parent).localname
        name = ET.QName(node).localname
        ranks = orders.get(parent_name, {})
        if name not in ranks:
            raise ValueError(
                f"No supported schema order for {parent_name}/{name}"
            )

        position = len(parent)
        for index, child in enumerate(parent):
            if not isinstance(child.tag, str):
                continue
            child_name = ET.QName(child).localname
            if child_name not in ranks:
                raise ValueError(
                    f"Unknown child order: {parent_name}/{child_name}"
                )
            if ranks[child_name] > ranks[name]:
                position = index
                break
        parent.insert(position, node)

    def ensure(parent, path):
        for name in path.split("/"):
            children = parent.findall(f"{{{URI}}}{name}")
            if len(children) > 1:
                raise ValueError(f"Ambiguous context: {path}")
            if children:
                parent = children[0]
            else:
                node = ET.Element(f"{{{URI}}}{name}")
                insert(parent, node)
                parent = node
        return parent

    def scalar(parent, name, value):
        children = parent.findall(f"{{{URI}}}{name}")
        if len(children) > 1:
            raise ValueError(f"Ambiguous scalar: {name}")
        for child in children:
            parent.remove(child)
        if value is not None:
            node = ET.Element(f"{{{URI}}}{name}")
            node.text = value
            insert(parent, node)

    raw = BASELINE.read_bytes()
    if digest(raw) != BASELINE_HASH:
        raise ValueError("Baseline changed; review before regenerating.")

    baseline = ET.fromstring(raw, parser)
    schema.assertValid(baseline)
    one(baseline, ".//m:VALUATION_ANALYSIS")
    one(baseline, SUBJECT)

    inventory = Graph().parse(INVENTORY, format="turtle")
    members = list(
        inventory.objects(S.other_conditional_scoped, T.coversRule)
    )
    sources = {}
    for rule_id, logic in LOGIC.items():
        rows = [
            row for row in members
            if str(single(inventory, row, T.ruleId)) == rule_id
        ]
        if len(rows) != 1:
            raise ValueError(f"Expected one source rule: {rule_id}")
        row = rows[0]
        if str(single(inventory, row, T.ruleLogic)) != logic:
            raise ValueError(f"Source logic changed: {rule_id}")
        sources[rule_id] = row

    graph = Graph()
    graph.bind("m", M)
    graph.bind("case", C)

    def put(subject, predicate, value):
        graph.add((subject, predicate, Literal(value)))

    graph.add((C.manifest, RDF.type, M.Manifest))
    put(C.manifest, M.schemaVersion, 1)
    put(C.manifest, M.scenarioId, "IT-1R1S1")
    put(C.manifest, M.caseCount, 17)
    put(
        C.manifest, M.coverage,
        "Initial three-rule slice; not full R1 coverage.",
    )

    for predicate, node, path in [
        (M.baseline, C.baseline, BASELINE),
        (M.inventory, C.inventory, INVENTORY),
        (M.validationSchema, C.schema, SCHEMA),
    ]:
        graph.add((C.manifest, predicate, node))
        graph.add((node, RDF.type, M.SourceArtifact))
        put(node, M.path, path.relative_to(ROOT).as_posix())
        put(node, M.sha256, digest(path.read_bytes()))

    graph.add((C.manifest, M.sourceWorkbook, C.workbook))
    graph.add((C.workbook, RDF.type, M.SourceWorkbook))
    graph.add((C.workbook, M.sourceResource, B.appendixH))
    for key in ("path", "sheet", "version", "sha256"):
        put(
            C.workbook, M[key],
            str(single(inventory, B.appendixH, T[key])),
        )

    for limitation in [
        "Focused fixtures isolate the selected source rule.",
        "Other business rules may be violated by deliberate case changes.",
        "XSD validity does not establish external endpoint acceptance.",
        "Copied improvements may repeat identifiers not constrained by this XSD.",
    ]:
        put(C.manifest, M.limitation, limitation)

    artifacts = {}

    def add(
        rule_id, name, root, facts, paths, supplied, changes
    ):
        relative = f"{rule_id}/{name}.xml"
        target = target_path(relative)
        location = quote(
            Path(os.path.relpath(SCHEMA, target.parent)).as_posix(),
            safe="/.",
        )
        resolved_schema = (
            target.parent / unquote(location)
        ).resolve()
        if resolved_schema != SCHEMA.resolve():
            raise ValueError("Relative schema reference does not resolve.")

        root.set(
            f"{{{XSI}}}schemaLocation",
            f"{URI} {location}",
        )

        # Make namespace cleanup part of reproducible generation.
        # Used element and attribute namespaces remain declared.
        ET.cleanup_namespaces(root)

        content = ET.tostring(
            root, encoding="utf-8", xml_declaration=True
        )
        parsed = ET.fromstring(content, parser)

        # Validate the serialized bytes, not just an earlier XML tree.
        try:
            schema.assertValid(parsed)
        except ET.DocumentInvalid as error:
            raise ValueError(
                f"{relative}: XSD validation failed: {error}"
            ) from error

        for path, count, expected_text in facts:
            nodes = parsed.findall(path, NS)
            if len(nodes) != count:
                raise ValueError(
                    f"{relative}: fixture count mismatch: {path}"
                )
            if expected_text is not None:
                if [node.text for node in nodes] != [expected_text]:
                    raise ValueError(
                        f"{relative}: fixture text mismatch: {path}"
                    )

        if relative in artifacts:
            raise ValueError(f"Duplicate fixture: {relative}")
        artifacts[relative] = content

        key = f"{rule_id}-{name}"
        case = C[key]
        source = sources[rule_id]
        state = (
            "applicable_missing" if paths
            else "applicable_supplied" if supplied
            else "not_applicable"
        )

        graph.add((C.manifest, M.case, case))
        graph.add((case, RDF.type, M.TestCase))
        graph.add((case, M.sourceRule, source))
        graph.add((case, M.baseline, C.baseline))
        graph.add((case, M.validationSchema, C.schema))

        values = [
            (M.caseId, f"IT-1R1S1-{key}"),
            (M.ruleId, rule_id),
            (
                M.sourceRow,
                int(single(inventory, source, T.sourceRow)),
            ),
            (
                M.sourceUniqueId,
                str(single(inventory, source, T.sourceUniqueIdCell)),
            ),
            (M.sourceRuleLogic, LOGIC[rule_id]),
            (M.state, state),
            (M.purpose, name.replace("-", " ")),
            (M.xmlFile, relative),
            (M.xmlSha256, digest(content)),
            (M.expectedFindingCount, len(paths)),
            (M.fixtureKind, "focused_validator_fixture"),
            (M.endpointReadiness, "not_verified"),
            (M.xsdValid, True),
        ]
        for predicate, value in values:
            put(case, predicate, value)

        for change in changes + [
            "Replace stale schema reference with a relative URI."
        ]:
            put(case, M.change, change)

        for index, (path, count, expected_text) in enumerate(facts, 1):
            check = C[f"{key}-check-{index}"]
            graph.add((case, M.fixtureCheck, check))
            graph.add((check, RDF.type, M.FixtureCheck))
            put(check, M.path, path)
            put(check, M["count"], count)
            if expected_text is not None:
                put(check, M.expectedText, expected_text)

        for index, path in enumerate(paths, 1):
            finding = C[f"{key}-finding-{index}"]
            graph.add((case, M.expectedFinding, finding))
            graph.add((finding, RDF.type, M.ExpectedFinding))
            for predicate, value in [
                (M.ruleId, rule_id),
                (
                    M.severity,
                    str(single(inventory, source, T.severity)).casefold(),
                ),
                (M.dataLocation, path),
                (M.violationKind, "MissingRequiredValue"),
            ]:
                put(finding, predicate, value)

    def fact(path, value):
        return path, 0 if value is None else 1, value

    for rule_id, table in [
        ("UAD1021", OR_CASES),
        ("UAD1024", AND_CASES),
    ]:
        for name, first, second, dependent, violation in table:
            root = deepcopy(baseline)
            prop = one(root, SUBJECT)
            detail = one(root, DETAIL)

            if rule_id == "UAD1021":
                other = ensure(prop, "PROJECT/PROJECT_DETAIL")
                scalar(detail, "PropertyInProjectIndicator", first)
                scalar(other, "ProjectLegalStructureType", second)
                scalar(detail, "PropertyEstateType", dependent)
                values = [
                    (DETAIL + "/m:PropertyInProjectIndicator", first),
                    (PROJECT + "/m:ProjectLegalStructureType", second),
                    (DETAIL + "/m:PropertyEstateType", dependent),
                ]
            else:
                other = ensure(prop, "PROPERTY_GROUND_RENT")
                scalar(detail, "PropertyEstateType", first)
                scalar(
                    one(root, SITE),
                    "LandOwnedInCommonIndicator",
                    second,
                )
                scalar(
                    other, "PropertyGroundLeaseAnnualAmount", dependent
                )
                values = [
                    (DETAIL + "/m:PropertyEstateType", first),
                    (SITE + "/m:LandOwnedInCommonIndicator", second),
                    (RENT + "/m:PropertyGroundLeaseAnnualAmount", dependent),
                ]

            changes = [
                f"{path}: "
                + ("removed" if value is None else f"set to {value}")
                for path, value in values
            ]
            add(
                rule_id, name, root,
                [fact(path, value) for path, value in values],
                [values[-1][0][1:]] if violation else [],
                dependent is not None,
                changes,
            )

    for name, instances, missing in SCOPE_CASES:
        root = deepcopy(baseline)
        container = one(root, IMPROVEMENTS)
        existing = container.findall(f"{{{URI}}}IMPROVEMENT")
        if not existing:
            raise ValueError("Baseline has no subject improvement.")
        template = deepcopy(existing[0])
        for node in existing:
            container.remove(node)

        facts = [
            (
                IMPROVEMENTS + "/m:IMPROVEMENT",
                len(instances),
                None,
            )
        ]
        paths = []
        changes = [
            "Replace subject improvements with copies of the first "
            "baseline improvement."
        ]

        for position, (kind, dependent) in enumerate(instances, 1):
            node = deepcopy(template)
            insert(container, node)
            detail = one(node, "m:IMPROVEMENT_DETAIL")
            scalar(detail, "ImprovementType", kind)
            scalar(
                detail,
                "PropertyStructureBuiltYearEstimatedIndicator",
                dependent,
            )

            step = (
                f"m:IMPROVEMENT[{position}]"
                if len(instances) > 1 else "m:IMPROVEMENT"
            )
            context = (
                IMPROVEMENTS + "/" + step + "/m:IMPROVEMENT_DETAIL"
            )
            path = (
                context + "/m:PropertyStructureBuiltYearEstimatedIndicator"
            )
            facts.extend([
                fact(context + "/m:ImprovementType", kind),
                fact(path, dependent),
            ])
            if position in missing:
                paths.append(path[1:])
            changes.append(
                f"Instance {position}: type={kind}; "
                f"estimated-year indicator={dependent!r}."
            )

        add(
            "UAD1054", name, root, facts, paths,
            name == "dwelling-supplied", changes,
        )

    if len(artifacts) != 17:
        raise ValueError("Expected 17 XML fixtures.")

    turtle = graph.serialize(format="turtle", encoding="utf-8")
    parsed_graph = Graph().parse(data=turtle, format="turtle")
    if not isomorphic(graph, parsed_graph):
        raise ValueError("Turtle round-trip changed the manifest.")
    artifacts["manifest.ttl"] = turtle
    return artifacts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--replace-generated", action="store_true")
    args = parser.parse_args()
    if args.replace_generated and not args.write:
        parser.error("--replace-generated requires --write")

    # Build and validate the entire corpus before any output is written.
    artifacts = build()
    if not args.write:
        print(
            "PASS: 17 XSD-valid XML cases, fixture checks, "
            "relative schema references, and Turtle."
        )
        print(
            "No files written. Validator RED/GREEN tests were not run."
        )
        return

    old_manifest = OUTPUT / "manifest.ttl"
    known_hashes = {}
    old_bytes = None

    if args.replace_generated and old_manifest.exists():
        old_bytes = old_manifest.read_bytes()
        old = Graph().parse(data=old_bytes, format="turtle")
        for case in old.subjects(RDF.type, M.TestCase):
            name = str(single(old, case, M.xmlFile))
            target_path(name)
            if name in known_hashes:
                raise ValueError(
                    f"Duplicate old manifest filename: {name}"
                )
            known_hashes[name] = str(single(old, case, M.xmlSha256))

    # Preflight every replacement before writing anything.
    for name, content in artifacts.items():
        target = target_path(name)
        if not target.exists() or target.read_bytes() == content:
            continue
        if not args.replace_generated:
            raise FileExistsError(
                f"Existing artifact differs: {target}"
            )

        current = target.read_bytes()
        if name == "manifest.ttl":
            if old_bytes is None or current != old_bytes:
                raise ValueError("Manifest changed during preflight.")
        elif digest(current) != known_hashes.get(name):
            raise ValueError(
                f"Preserving modified/unrecognized fixture: {target}"
            )

    # The manifest is the final artifact in insertion order.
    for name, content in artifacts.items():
        target = target_path(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_bytes() != content:
            target.write_bytes(content)

    for name, content in artifacts.items():
        if target_path(name).read_bytes() != content:
            raise ValueError(f"Saved artifact differs: {name}")

    print("Saved and verified 17 XSD-valid XML fixtures and manifest.ttl.")
    print("Validator RED/GREEN tests were not run.")


if __name__ == "__main__":
    main()