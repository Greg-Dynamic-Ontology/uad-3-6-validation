"""Generate schema-valid IT-1R1S1 XML cases and manifest.ttl.

Default: verify in memory only.
--write: save new artifacts.
--write --replace-generated: replace only artifacts matching the old manifest.
"""

import argparse
import hashlib
import json
import os
from copy import deepcopy
from pathlib import Path
from urllib.parse import quote, unquote

from lxml import etree as ET
from rdflib import Graph, Literal, Namespace, RDF
from rdflib.compare import isomorphic

from it_1_r1_s1_slice_02_cases import case_plans, rule_plans


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
R1 = Namespace("urn:uad36:work-tracking:r1-classification:")

# Fingerprint of the 30 reviewed source definitions, not the whole TTL.
SLICE_SOURCE_HASH = (
    "97665dc2a174c3993c7e6c24b2bba5fccd"
    "6a821b2ef04dcecb13d207f6ff88d4"
)
SOURCE_FIELDS = (
    "ruleId", "sourceRow", "sourceUniqueIdCell", "primaryDataElement",
    "ruleLogic", "xpath", "severity", "propertyAffected",
)
MEASURE_ATTRIBUTES = {
    "DistanceFromPropertyLinearMeasure": {"LinearUnitOfMeasureType": "Feet"},
    "CarStorageAreaMeasure": {"AreaUnitOfMeasureType": "SquareFeet"},
}
REPEATED_CONTEXT = {
    "IMPROVEMENT_DETAIL": "IMPROVEMENT",
    "MANUFACTURED_HOME_FINANCING_PROGRAM": "MANUFACTURED_HOME_FINANCING_PROGRAM",
    "ROOM_DETAIL": "ROOM",
    "INTERIOR_COMPONENT_DETAIL": "INTERIOR_COMPONENT",
    "ENVIRONMENTAL_CONDITION": "ENVIRONMENTAL_CONDITION",
    "SITE_INFLUENCE_DETAIL": "SITE_INFLUENCE",
    "INSPECTION_DETAIL": "INSPECTION",
    "PROJECT_AMENITY": "PROJECT_AMENITY",
    "ASSOCIATION_CHARGE_DETAIL": "ASSOCIATION_CHARGE",
    "MARKET_INVENTORY": "MARKET_INVENTORY",
    "CAR_STORAGE_DETAIL": "CAR_STORAGE",
}

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

    # Obtain order and cardinality from the schema.
    orders = {}
    occurrences = {}
    minimums = {}
    required_children = {}
    for definition in schema_doc.xpath(
        "//x:complexType[@name]", namespaces=xs
    ):
        children = definition.xpath(
            "./x:sequence/x:element[@name]", namespaces=xs
        )
        if children:
            required_children[definition.get("name")] = [
                child for child in children
                if int(child.get("minOccurs", "1")) > 0
            ]
            for child in children:
                minimums[(definition.get("name"), child.get("name"))] = int(
                    child.get("minOccurs", "1")
                )
                occurrences[(definition.get("name"), child.get("name"))] = (
                    child.get("maxOccurs", "1")
                )
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
            for attribute, unit in MEASURE_ATTRIBUTES.get(name, {}).items():
                node.set(attribute, unit)
            insert(parent, node)

    def complete_required_containers(parent):
        parent_name = ET.QName(parent).localname
        for declaration in required_children.get(parent_name, []):
            name = declaration.get("name")
            minimum = int(declaration.get("minOccurs", "1"))
            existing = parent.findall(f"{{{URI}}}{name}")
            while len(existing) < minimum:
                if not name.isupper() or declaration.get("type") != name:
                    raise ValueError(
                        f"Required value needs explicit fixture data: {parent_name}/{name}"
                    )
                node = ET.Element(f"{{{URI}}}{name}")
                insert(parent, node)
                existing.append(node)
        for child in list(parent):
            if isinstance(child.tag, str):
                complete_required_containers(child)

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

    plans = {plan.rule_id: plan for plan in rule_plans()}
    cases = case_plans()
    if len(plans) != 30 or len(cases) != 333:
        raise ValueError("Slice-02 coverage changed; review the case matrix.")
    selected = set(inventory.objects(R1.nextSlice, T.proposedSliceRule))
    selected_ids = {
        str(single(inventory, row, T.ruleId)): row for row in selected
    }
    if len(selected) != 30 or set(selected_ids) != set(plans):
        raise ValueError("Slice-02 plans do not match the TTL selection.")
    records = []
    for rule_id, row in sorted(selected_ids.items()):
        if row not in members:
            raise ValueError(f"Rule is outside R1: {rule_id}")
        record = {
            key: str(single(inventory, row, T[key]))
            for key in SOURCE_FIELDS
        }
        records.append(record)
        plan = plans[rule_id]
        if record["primaryDataElement"] != plan.target:
            raise ValueError(f"Dependent field mismatch: {rule_id}")
        if record["propertyAffected"] != "Subject":
            raise ValueError(f"Unsupported property scope: {rule_id}")
        fields = set(map(str, inventory.objects(row, T.conditionField)))
        for branch in plan.applicable + plan.nonapplicable + plan.split:
            if set(dict(branch.values)) != fields:
                raise ValueError(f"Condition fields mismatch: {rule_id}")
        sources[rule_id] = row
    fingerprint = digest(
        json.dumps(records, sort_keys=True, ensure_ascii=False).encode("utf-8")
    )
    if fingerprint != SLICE_SOURCE_HASH:
        raise ValueError("Reviewed slice-02 source definitions changed.")
    if {case.rule_id for case in cases} != set(plans):
        raise ValueError("Missing or unexpected slice-02 case rules.")

    graph = Graph()
    graph.bind("m", M)
    graph.bind("case", C)

    def put(subject, predicate, value):
        graph.add((subject, predicate, Literal(value)))

    graph.add((C.manifest, RDF.type, M.Manifest))
    put(C.manifest, M.schemaVersion, 1)
    put(C.manifest, M.scenarioId, "IT-1R1S1")
    put(C.manifest, M.caseCount, 17 + len(cases))
    put(
        C.manifest, M.coverage,
        "Slices 01 and 02: 33 source rules; not full R1 coverage.",
    )

    for predicate, node, path in [
        (M.baseline, C.baseline, BASELINE),
        (M.inventory, C.inventory, INVENTORY),
        (M.validationSchema, C.schema, SCHEMA),
        (M.generator, C.generator, Path(__file__).resolve()),
        (
            M.caseDefinitions, C.caseDefinitions,
            Path(__file__).resolve().with_name("it_1_r1_s1_slice_02_cases.py"),
        ),
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
        "Slice-02 cases replace one subject branch with focused contexts.",
        "Baseline relationships outside that branch are not repaired.",
        "XSD checks do not establish business-level relationship integrity.",
    ]:
        put(C.manifest, M.limitation, limitation)

    artifacts = {}

    def add(
        rule_id, name, root, facts, paths, supplied, changes,
        slice_id="01", purpose=None,
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
            (M.sourceRuleLogic, str(single(inventory, source, T.ruleLogic))),
            (M.sliceId, slice_id),
            (M.state, state),
            (M.purpose, purpose or name.replace("-", " ")),
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

    for case in cases:
        plan = plans[case.rule_id]
        source = sources[case.rule_id]
        source_path = str(single(inventory, source, T.xpath))
        prefix = "../VALUATION_ANALYSIS/PROPERTIES/PROPERTY/"
        if not source_path.startswith(prefix):
            raise ValueError(f"Unsupported source path: {source_path}")
        parts = source_path[len(prefix):].strip("/").split("/")
        if any(not part.replace("_", "").isalnum() for part in parts):
            raise ValueError(f"Unsupported source path components: {source_path}")
        repeat_name = REPEATED_CONTEXT[parts[-1]]
        if parts.count(repeat_name) != 1:
            raise ValueError(f"Ambiguous repeating context: {source_path}")
        repeat_index = parts.index(repeat_name)
        if repeat_index == 0:
            raise ValueError("Repeating context requires an explicit container.")
        declaration_key = (parts[repeat_index - 1], repeat_name)
        instances = list(case.instances)
        supporting = plan.nonapplicable[0].values + ((plan.target, None),)
        while len(instances) < minimums[declaration_key]:
            instances.append(supporting)
        limit = occurrences[declaration_key]
        if limit != "unbounded" and len(instances) > int(limit):
            raise ValueError(f"Too many instances for schema: {case.case_id}")

        root = deepcopy(baseline)
        prop = one(root, SUBJECT)
        # Replace only the selected subject branch with explicit minimal contexts.
        # Other subject branches and other properties remain from the baseline.
        for child in list(prop.findall(f"{{{URI}}}{parts[0]}")):
            prop.remove(child)
        parent = ensure(prop, "/".join(parts[:repeat_index]))
        repeat_path = SUBJECT + "/" + "/".join(
            "m:" + part for part in parts[:repeat_index + 1]
        )
        full_context = SUBJECT + "/" + "/".join("m:" + part for part in parts)
        facts = [
            (repeat_path, len(instances), None),
            (full_context, len(instances), None),
        ]
        paths = []
        changes = [
            f"Append {len(instances) - len(case.instances)} nonapplicable "
            "supporting instance(s) to satisfy XSD minimum cardinality.",
            f"Replace subject {parts[0]} with {len(instances)} "
            f"focused {repeat_name} instance(s)."
        ]
        for position, values in enumerate(instances, 1):
            repeated = ET.Element(f"{{{URI}}}{repeat_name}")
            insert(parent, repeated)
            tail = parts[repeat_index + 1:]
            context = ensure(repeated, "/".join(tail)) if tail else repeated
            path_parts = ["m:" + part for part in parts]
            if len(instances) > 1:
                path_parts[repeat_index] += f"[{position}]"
            context_path = SUBJECT + "/" + "/".join(path_parts)
            values_by_name = dict(values)
            expected_fields = set(
                map(str, inventory.objects(source, T.conditionField))
            ) | {plan.target}
            if len(values_by_name) != len(values) or set(values_by_name) != expected_fields:
                raise ValueError(f"Invalid case fields: {case.case_id}")
            for name, value in values:
                scalar(context, name, value)
                facts.append(fact(context_path + "/m:" + name, value))
                if value is not None:
                    for attribute, unit in MEASURE_ATTRIBUTES.get(name, {}).items():
                        facts.append(fact(
                            context_path + "/m:" + name
                            + f"[@{attribute}='{unit}']", value,
                        ))
                        changes.append(f"Instance {position}: {name}/@{attribute}={unit}")
                changes.append(
                    f"Instance {position}: {name}="
                    + ("absent" if value is None else repr(value))
                )
            if position in case.missing_positions:
                if values_by_name[plan.target] is not None:
                    raise ValueError(f"Expected missing target is supplied: {case.case_id}")
                paths.append((context_path + "/m:" + plan.target)[1:])
        complete_required_containers(one(prop, "m:" + parts[0]))
        changes.append("Add required empty structural containers from the XSD.")
        if len(paths) != len(case.missing_positions):
            raise ValueError(f"Invalid expected positions: {case.case_id}")
        if bool(paths) != (case.state == "applicable_missing"):
            raise ValueError(f"Case state disagrees with findings: {case.case_id}")
        add(
            case.rule_id, case.name, root, facts, paths,
            case.state == "applicable_supplied", changes,
            slice_id="02", purpose=case.purpose,
        )

    if len(artifacts) != 17 + len(cases):
        raise ValueError("Unexpected total XML fixture count.")
    case_nodes = set(graph.objects(C.manifest, M.case))
    if len(case_nodes) != len(artifacts):
        raise ValueError("Manifest case coverage differs from generated XML.")

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
    xml_count = len(artifacts) - 1
    if not args.write:
        print(
            f"PASS: {xml_count} XSD-valid XML cases, fixture checks, "
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

    removed = set(known_hashes) - set(artifacts)
    if removed:
        raise ValueError(f"Generation would omit prior cases: {sorted(removed)}")

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

    print(f"Saved and verified {xml_count} XSD-valid XML fixtures and manifest.ttl.")
    print("Validator RED/GREEN tests were not run.")


if __name__ == "__main__":
    main()