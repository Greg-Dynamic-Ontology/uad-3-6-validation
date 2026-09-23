"""Run RDF-defined required-data acceptance tests.

Loads:
    fixtures/required_data/test-suite.ttl
    fixtures/required_data/sales-contract-tests.ttl

With the current definitions:
    55 unconditional tests + 30 conditional cases = 85 tests.

RDF supplies test inputs and expectations, never production rules.
XML variations are created in memory; no fixture files are modified.
"""

from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET

import pytest
from rdflib import Graph, Literal, Namespace, RDF, URIRef

from app.models.enums import Investor, RuleType, Severity
from app.models.validation import ValidationRequest
from app.services.validation import ValidationService


T = Namespace("https://dynamicontology.com/uad36/test-vocabulary#")
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "required_data"
DEFINITION_FILES = (
    FIXTURES / "test-suite.ttl",
    FIXTURES / "sales-contract-tests.ttl",
)
XSI = "http://www.w3.org/2001/XMLSchema-instance"
NIL_ATTRIBUTE = f"{{{XSI}}}nil"


def one(graph, subject, predicate):
    values = list(graph.objects(subject, predicate))
    if len(values) != 1:
        raise ValueError(
            f"{subject}: expected one {predicate}, found {len(values)}"
        )
    return values[0]


def string_value(graph, subject, predicate, allow_blank=False):
    value = one(graph, subject, predicate)
    if not isinstance(value, Literal):
        raise ValueError(f"{subject}: {predicate} must be a string literal")
    if not isinstance(value.toPython(), str):
        raise ValueError(f"{subject}: {predicate} must be a string")
    text = str(value)
    if not allow_blank and not text.strip():
        raise ValueError(f"{subject}: {predicate} must not be blank")
    return text


def count_value(graph, subject, predicate):
    value = one(graph, subject, predicate)
    number = value.toPython() if isinstance(value, Literal) else None
    if type(number) is not int or number < 0:
        raise ValueError(
            f"{subject}: {predicate} must be a nonnegative integer"
        )
    return number


def boolean_value(graph, subject, predicate):
    value = one(graph, subject, predicate)
    result = value.toPython() if isinstance(value, Literal) else None
    if type(result) is not bool:
        raise ValueError(f"{subject}: {predicate} must be a boolean")
    return result


def fixture_path(relative):
    portable = PurePosixPath(relative)
    if (
        portable.is_absolute()
        or ".." in portable.parts
        or "\\" in relative
        or ":" in relative
    ):
        raise ValueError(f"Invalid relative fixture path: {relative}")

    path = FIXTURES.joinpath(*portable.parts).resolve()
    if not path.is_relative_to(FIXTURES.resolve()):
        raise ValueError(f"Fixture path escapes fixture directory: {relative}")
    if not path.is_file():
        raise ValueError(f"Fixture does not exist: {path}")
    return path


def namespaces(graph, subject):
    result = {}
    for binding in graph.objects(subject, T.namespaceBinding):
        prefix = string_value(graph, binding, T.prefix)
        iri = one(graph, binding, T.namespaceIRI)
        if not isinstance(iri, URIRef):
            raise ValueError("namespaceIRI must be an IRI")
        if prefix in result:
            raise ValueError(f"Duplicate namespace prefix: {prefix}")
        result[prefix] = str(iri)
    if not result:
        raise ValueError(f"{subject}: XML namespace bindings are required")
    return result


def suite_subjects(graph, suite_type):
    subjects = sorted(set(graph.subjects(RDF.type, suite_type)), key=str)
    if not subjects:
        raise ValueError(f"No suites declared for {suite_type}")
    for subject in subjects:
        if not isinstance(subject, URIRef):
            raise ValueError("Every suite must have a stable IRI")
        if string_value(graph, subject, T.definitionVersion) != "1":
            raise ValueError(f"{subject}: unsupported definition version")
    return subjects


def validate_memberships(graph):
    """Reject orphan cases, unknown suites, and ambiguous membership."""
    type_pairs = {
        T.TestSuite: T.TestCase,
        T.ConditionalTestSuite: T.ConditionalTestCase,
    }
    suite_types = {}
    for suite_type in type_pairs:
        for subject in graph.subjects(RDF.type, suite_type):
            if subject in suite_types:
                raise ValueError(f"{subject}: conflicting suite types")
            suite_types[subject] = suite_type

    case_types = {}
    for case_type in type_pairs.values():
        for member in graph.subjects(RDF.type, case_type):
            if member in case_types:
                raise ValueError(f"{member}: conflicting case types")
            case_types[member] = case_type

    linked_cases = set(graph.subjects(T.inSuite, None))
    if linked_cases != set(case_types):
        raise ValueError(
            "Every declared case must have suite membership, "
            "and every suite member must have a supported case type"
        )

    for member, case_type in case_types.items():
        if not isinstance(member, URIRef):
            raise ValueError("Every case must have a stable IRI")
        suite = one(graph, member, T.inSuite)
        suite_type = suite_types.get(suite)
        if suite_type is None:
            raise ValueError(f"{member}: unknown suite {suite}")
        if type_pairs[suite_type] != case_type:
            raise ValueError(f"{member}: case type does not match its suite")


def members(graph, subject, case_type):
    found = set(graph.subjects(T.inSuite, subject))
    expected = count_value(graph, subject, T.expectedCaseCount)
    if expected == 0 or len(found) != expected:
        raise ValueError(
            f"{subject}: expected {expected} cases, found {len(found)}"
        )
    for member in found:
        if (member, RDF.type, case_type) not in graph:
            raise ValueError(f"{member}: expected type {case_type}")
        if one(graph, member, T.inSuite) != subject:
            raise ValueError(f"{member}: invalid suite membership")
    return sorted(found, key=str)


def fatal_severity(graph, subject):
    severity = string_value(graph, subject, T.expectedSeverity)
    if severity != Severity.FATAL.value:
        raise ValueError(f"{subject}: expected Fatal severity")
    return severity


def expanded_name(qname, ns):
    parts = qname.split(":")
    if len(parts) != 2 or not all(parts):
        raise ValueError(f"Expected a namespace-qualified element: {qname}")
    prefix, local = parts
    if prefix not in ns or any(c in local for c in "/[]@* "):
        raise ValueError(f"Invalid qualified element name: {qname}")
    return f"{{{ns[prefix]}}}{local}"


def load_required_suite(graph):
    subjects = suite_subjects(graph, T.TestSuite)
    if len(subjects) != 1:
        raise ValueError("Expected exactly one unconditional suite")
    subject = subjects[0]

    if one(graph, subject, T.findingScope) != T.DeclaredRuleIds:
        raise ValueError("Unsupported required-data finding scope")
    if one(graph, subject, T.caseKind) != T.MissingElement:
        raise ValueError("Expected MissingElement cases")
    if count_value(graph, subject, T.expectedCaseCount) != 53:
        raise ValueError("The original acceptance suite must contain 53 cases")

    suite = {
        "baseline": fixture_path(
            string_value(graph, subject, T.baselinePath)
        ),
        "namespaces": namespaces(graph, subject),
        "severity": fatal_severity(graph, subject),
        "baseline_count": count_value(
            graph, subject, T.expectedBaselineFindingCount
        ),
        "matching_count": count_value(
            graph, subject, T.expectedMatchingFindingCount
        ),
        "other_count": count_value(
            graph, subject, T.expectedOtherScopedFindingCount
        ),
    }
    if (
        suite["baseline_count"],
        suite["matching_count"],
        suite["other_count"],
    ) != (0, 1, 0):
        raise ValueError("Required-data count contract must be 0, 1, 0")

    cases = []
    for member in members(graph, subject, T.TestCase):
        case = {
            "fixture": fixture_path(
                string_value(graph, member, T.fixturePath)
            ),
            "row_id": string_value(graph, member, T.rowId),
            "element": string_value(graph, member, T.primaryDataElement),
            "rule_id": string_value(graph, member, T.ruleId),
            "xml_context": string_value(graph, member, T.xmlContext),
        }
        case["id"] = f"{case['row_id']}-{case['rule_id']}"
        cases.append(case)

    for field in ("row_id", "rule_id", "fixture"):
        values = [case[field] for case in cases]
        if len(set(values)) != len(values):
            raise ValueError(f"Duplicate required-data case {field}")

    suite["cases"] = sorted(cases, key=lambda case: case["id"])
    suite["rule_ids"] = {case["rule_id"] for case in cases}
    return suite


def load_conditional_suite(graph, subject):
    if one(graph, subject, T.conditionOperator) != T.Equals:
        raise ValueError(f"{subject}: only Equals conditions are supported")

    suite = {
        "iri": str(subject),
        "baseline": fixture_path(
            string_value(graph, subject, T.baselinePath)
        ),
        "namespaces": namespaces(graph, subject),
        "row_id": string_value(graph, subject, T.rowId),
        "rule_id": string_value(graph, subject, T.ruleId),
        "element": string_value(graph, subject, T.primaryDataElement),
        "severity": fatal_severity(graph, subject),
        "context": string_value(graph, subject, T.contextPath),
        "context_count": count_value(
            graph, subject, T.expectedContextCount
        ),
        "trigger": string_value(graph, subject, T.triggerElement),
        "target": string_value(graph, subject, T.targetElement),
        "xml_context": string_value(graph, subject, T.xmlContext),
        "condition_value": string_value(graph, subject, T.conditionValue),
    }
    if suite["context_count"] != 1:
        raise ValueError("This conditional runner requires one target context")
    if suite["namespaces"].get("xsi") != XSI:
        raise ValueError("Expected the XML Schema Instance namespace")

    suite["trigger_tag"] = expanded_name(
        suite["trigger"], suite["namespaces"]
    )
    suite["target_tag"] = expanded_name(
        suite["target"], suite["namespaces"]
    )
    if suite["trigger_tag"] == suite["target_tag"]:
        raise ValueError("Trigger and dependent element must be different")
    if suite["target_tag"].rsplit("}", 1)[-1] != suite["element"]:
        raise ValueError("Target element and Primary Data Element disagree")
    if suite["xml_context"] != suite["context"] + "/" + suite["target"]:
        raise ValueError("Finding context does not identify the target element")

    cases = []
    allowed_states = {T.Absent, T.Present, T.Empty, T.Whitespace, T.Nil}
    for member in members(graph, subject, T.ConditionalTestCase):
        state = one(graph, member, T.targetState)
        if state not in allowed_states:
            raise ValueError(f"{member}: unsupported targetState {state}")

        case = {
            "id": str(member).rsplit("/", 1)[-1],
            "scenario": string_value(graph, member, T.scenarioId),
            "trigger_value": string_value(graph, member, T.triggerValue),
            "condition_result": boolean_value(
                graph, member, T.expectedConditionResult
            ),
            "state": state,
            "matching_count": count_value(
                graph, member, T.expectedMatchingFindingCount
            ),
            "target_value": None,
        }

        values = list(graph.objects(member, T.targetValue))
        if state in {T.Present, T.Whitespace}:
            case["target_value"] = string_value(
                graph, member, T.targetValue, allow_blank=True
            )
            if state == T.Present and not case["target_value"].strip():
                raise ValueError(f"{member}: Present requires nonblank text")
            if state == T.Whitespace and (
                not case["target_value"] or case["target_value"].strip()
            ):
                raise ValueError(f"{member}: expected whitespace-only text")
        elif values:
            raise ValueError(f"{member}: targetValue is not allowed here")

        condition = case["trigger_value"] == suite["condition_value"]
        if condition != case["condition_result"]:
            raise ValueError(f"{member}: inconsistent condition expectation")

        expected = int(condition and state != T.Present)
        if case["matching_count"] != expected:
            raise ValueError(f"{member}: inconsistent finding expectation")
        cases.append(case)

    suite["cases"] = sorted(cases, key=lambda case: case["id"])
    return suite


def load_definitions():
    graph = Graph()
    seen_suites = set()
    seen_cases = set()

    for path in DEFINITION_FILES:
        if not path.is_file():
            raise ValueError(f"Missing RDF test definitions: {path}")

        document = Graph()
        document.parse(path, format="turtle")

        document_suites = (
            set(document.subjects(RDF.type, T.TestSuite))
            | set(document.subjects(RDF.type, T.ConditionalTestSuite))
        )
        document_cases = (
            set(document.subjects(RDF.type, T.TestCase))
            | set(document.subjects(RDF.type, T.ConditionalTestCase))
        )
        if not document_suites:
            raise ValueError(f"No test suites declared in {path}")
        if seen_suites & document_suites:
            raise ValueError(f"Duplicate suite definitions across files: {path}")
        if seen_cases & document_cases:
            raise ValueError(f"Duplicate case definitions across files: {path}")

        seen_suites.update(document_suites)
        seen_cases.update(document_cases)
        graph += document

    validate_memberships(graph)
    return graph


GRAPH = load_definitions()
REQUIRED = load_required_suite(GRAPH)
CONDITIONAL_SUITES = [
    load_conditional_suite(GRAPH, subject)
    for subject in suite_subjects(GRAPH, T.ConditionalTestSuite)
]

# Every parameter carries its own suite; no shared mutable current suite.
CONDITIONAL_CASES = [
    (suite, case)
    for suite in CONDITIONAL_SUITES
    for case in suite["cases"]
]
CONDITIONAL_IDS = [case["id"] for _, case in CONDITIONAL_CASES]
if len(set(CONDITIONAL_IDS)) != len(CONDITIONAL_IDS):
    raise ValueError("Duplicate conditional test IDs across suites")


def select_nodes(root, path, ns):
    """Resolve supported descendant paths using namespace bindings."""
    if not path.startswith("//"):
        raise ValueError(f"Unsupported XML context: {path}")
    wrapper = ET.Element("_test_document")
    wrapper.append(root)
    try:
        return wrapper.findall("." + path, namespaces=ns)
    except (SyntaxError, KeyError) as error:
        raise ValueError(f"Invalid XML context {path}: {error}") from error


def validate_xml(xml_text, package_name):
    result = ValidationService().validate(
        ValidationRequest(
            package_name=package_name,
            xml_text=xml_text,
            investor_scope=Investor.BOTH,
        )
    )
    schema_failures = [
        finding
        for finding in result.findings
        if finding.rule_type == RuleType.SCHEMA
        and finding.severity
        in {Severity.ERROR, Severity.CRITICAL, Severity.FATAL}
    ]
    assert not schema_failures, (
        f"{package_name}: XML processing failed: "
        f"{[finding.finding for finding in schema_failures]}"
    )
    return result


def validate_file(path):
    return validate_xml(path.read_text(encoding="utf-8-sig"), path.name)


def describe(findings):
    return [
        {
            "rule_id": finding.rule_id,
            "row_id": finding.row_id,
            "severity": str(finding.severity),
            "xml_context": finding.data_location,
        }
        for finding in findings
    ]


def check_finding(finding, row_id, severity, xml_context, test_id):
    assert finding.row_id == row_id, (
        f"{test_id}: expected row {row_id}, received {finding.row_id}"
    )
    assert str(finding.severity) == severity, (
        f"{test_id}: expected {severity}, received {finding.severity}"
    )
    assert finding.data_location == xml_context, (
        f"{test_id}: incorrect XML context\n"
        f"Expected: {xml_context}\n"
        f"Received: {finding.data_location}"
    )


def test_rdf_fixtures_have_the_declared_missing_elements():
    baseline = ET.parse(REQUIRED["baseline"]).getroot()
    for case in REQUIRED["cases"]:
        original = select_nodes(
            baseline, case["xml_context"], REQUIRED["namespaces"]
        )
        assert len(original) == 1, (
            f"{case['id']}: expected one baseline target, found {len(original)}"
        )
        assert original[0].tag.rsplit("}", 1)[-1] == case["element"], (
            f"{case['id']}: context does not identify {case['element']}"
        )
        negative = ET.parse(case["fixture"]).getroot()
        assert not select_nodes(
            negative, case["xml_context"], REQUIRED["namespaces"]
        ), f"{case['id']}: targeted element is still present"


def test_rdf_baseline_has_no_required_findings():
    result = validate_file(REQUIRED["baseline"])
    scoped = [
        finding for finding in result.findings
        if finding.rule_id in REQUIRED["rule_ids"]
    ]
    assert len(scoped) == REQUIRED["baseline_count"], (
        f"Unexpected baseline findings: {describe(scoped)}"
    )


@pytest.mark.parametrize(
    "case", REQUIRED["cases"], ids=lambda case: case["id"]
)
def test_rdf_missing_element_produces_expected_finding(case):
    result = validate_file(case["fixture"])
    scoped = [
        finding for finding in result.findings
        if finding.rule_id in REQUIRED["rule_ids"]
    ]
    matching = [
        finding for finding in scoped
        if finding.rule_id == case["rule_id"]
    ]
    other = [
        finding for finding in scoped
        if finding.rule_id != case["rule_id"]
    ]
    assert len(matching) == REQUIRED["matching_count"], (
        f"{case['id']}: incorrect matching count: {describe(scoped)}"
    )
    assert len(other) == REQUIRED["other_count"], (
        f"{case['id']}: unexpected other findings: {describe(other)}"
    )
    for finding in matching:
        check_finding(
            finding, case["row_id"], REQUIRED["severity"],
            case["xml_context"], case["id"],
        )


def conditional_xml(suite, case):
    """Create one independent variation without changing any disk file."""
    root = ET.parse(suite["baseline"]).getroot()
    contexts = select_nodes(root, suite["context"], suite["namespaces"])
    assert len(contexts) == suite["context_count"], (
        f"{case['id']}: expected {suite['context_count']} contexts, "
        f"found {len(contexts)}"
    )
    context = contexts[0]

    triggers = context.findall(suite["trigger_tag"])
    assert len(triggers) == 1, (
        f"{case['id']}: expected one existing trigger, found {len(triggers)}"
    )
    trigger = triggers[0]
    assert not list(trigger), "Trigger must be a scalar element"
    assert trigger.get(NIL_ATTRIBUTE) not in {"true", "1"}, (
        "Baseline trigger must not be nil"
    )
    trigger.text = case["trigger_value"]

    assert (trigger.text == suite["condition_value"]) == case[
        "condition_result"
    ], f"{case['id']}: fixture condition does not match the definition"

    existing = context.findall(suite["target_tag"])
    assert len(existing) <= 1, "Baseline has duplicate dependent elements"
    position = (
        list(context).index(existing[0])
        if existing
        else list(context).index(trigger) + 1
    )
    for target in existing:
        context.remove(target)

    if case["state"] != T.Absent:
        target = ET.Element(suite["target_tag"])
        if case["state"] in {T.Present, T.Whitespace}:
            target.text = case["target_value"]
        elif case["state"] == T.Nil:
            target.set(NIL_ATTRIBUTE, "true")
        context.insert(position, target)

    targets = select_nodes(
        root, suite["xml_context"], suite["namespaces"]
    )
    expected_targets = 0 if case["state"] == T.Absent else 1
    assert len(targets) == expected_targets, (
        f"{case['id']}: constructed target state is incorrect"
    )
    return ET.tostring(root, encoding="unicode")


@pytest.mark.parametrize(
    "suite,case",
    CONDITIONAL_CASES,
    ids=CONDITIONAL_IDS,
)
def test_rdf_conditional_required_data(suite, case):
    result = validate_xml(
        conditional_xml(suite, case),
        case["id"] + ".xml",
    )
    matching = [
        finding for finding in result.findings
        if finding.rule_id == suite["rule_id"]
    ]
    assert len(matching) == case["matching_count"], (
        f"{case['id']} ({case['scenario']}): "
        f"expected {case['matching_count']} findings for {suite['rule_id']}; "
        f"received {describe(result.findings)}"
    )

    for finding in matching:
        check_finding(
            finding, suite["row_id"], suite["severity"],
            suite["xml_context"], case["id"],
        )
        assert finding.primary_data_element == suite["element"], (
            f"{case['id']}: incorrect Primary Data Element"
        )
        guidance = finding.expected_condition or ""
        for term in (
            suite["trigger"].split(":", 1)[1],
            suite["condition_value"],
            suite["element"],
        ):
            assert term in guidance, (
                f"{case['id']}: correction guidance must include {term!r}"
            )