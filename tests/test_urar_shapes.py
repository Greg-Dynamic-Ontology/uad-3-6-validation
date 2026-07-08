from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import Graph, Namespace
from rdflib.namespace import RDF


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CORE_ONTOLOGY_FILE = PROJECT_ROOT / "ontologies" / "uad36-core.ttl"
URAR_MEANING_FILE = PROJECT_ROOT / "ontologies" / "urar-meaning.ttl"
URAR_SHAPES_FILE = PROJECT_ROOT / "ontologies" / "urar-shapes.ttl"
EXAMPLES_DIR = PROJECT_ROOT / "examples"
SHACL_REPORTS_DIR = PROJECT_ROOT / "shacl-reports"

UAD = Namespace("https://dynamicontology.com/uad36/ontology#")
SH = Namespace("http://www.w3.org/ns/shacl#")


def valid_example_files() -> list[Path]:
    return sorted((EXAMPLES_DIR / "valid").glob("*.ttl"))


def invalid_example_files() -> list[Path]:
    return sorted((EXAMPLES_DIR / "invalid").glob("*.ttl"))


def example_files() -> list[Path]:
    return valid_example_files() + invalid_example_files()


def load_ontology_graph() -> Graph:
    graph = Graph()
    graph.parse(CORE_ONTOLOGY_FILE, format="turtle")
    graph.parse(URAR_MEANING_FILE, format="turtle")
    return graph


def load_example_graph(example_file: Path) -> Graph:
    graph = Graph()
    graph.parse(example_file, format="turtle")
    return graph


def load_data_graph(example_file: Path) -> Graph:
    graph = load_ontology_graph()
    graph.parse(example_file, format="turtle")
    return graph


def load_shapes_graph() -> Graph:
    graph = Graph()
    graph.parse(URAR_SHAPES_FILE, format="turtle")
    return graph


def example_id(example_file: Path) -> str:
    return example_file.relative_to(EXAMPLES_DIR).as_posix()


def format_shacl_results(results_graph: Graph, results_text: str) -> str:
    lines: list[str] = []

    for result in results_graph.subjects(RDF.type, SH.ValidationResult):
        focus_node = results_graph.value(result, SH.focusNode)
        result_path = results_graph.value(result, SH.resultPath)
        source_shape = results_graph.value(result, SH.sourceShape)
        source_constraint = results_graph.value(result, SH.sourceConstraintComponent)
        message = results_graph.value(result, SH.resultMessage)

        lines.append("SHACL violation")
        lines.append(f"  Focus node: {focus_node}")
        lines.append(f"  Path: {result_path}")
        lines.append(f"  Source shape: {source_shape}")
        lines.append(f"  Constraint: {source_constraint}")
        lines.append(f"  Message: {message}")
        lines.append("")

    if lines:
        return "\n".join(lines)

    if results_text and results_text.strip():
        return results_text.strip()

    return results_graph.serialize(format="turtle")


def write_shacl_report(example_file: Path, report_text: str) -> Path:
    SHACL_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    report_file = SHACL_REPORTS_DIR / f"{example_file.stem}-shacl-report.txt"
    report_file.write_text(report_text, encoding="utf-8")

    return report_file


def test_urar_shapes_file_exists():
    assert URAR_SHAPES_FILE.exists()


def test_examples_directory_exists():
    assert EXAMPLES_DIR.exists()


def test_at_least_one_example_appraisal_exists():
    assert example_files()


def test_urar_shapes_parse_as_turtle():
    graph = load_shapes_graph()
    assert len(graph) > 0


@pytest.mark.parametrize(
    "example_file",
    example_files(),
    ids=example_id,
)
def test_example_appraisal_parses_as_turtle(example_file: Path):
    graph = load_example_graph(example_file)

    assert len(graph) > 0, f"{example_file.name} contains no RDF triples."


@pytest.mark.parametrize(
    "example_file",
    example_files(),
    ids=example_id,
)
def test_example_contains_exactly_one_appraisal(example_file: Path):
    graph = load_example_graph(example_file)

    appraisals = list(graph.subjects(RDF.type, UAD.Appraisal))

    assert len(appraisals) == 1, (
        f"{example_file.name} should contain exactly one uad:Appraisal; "
        f"found {len(appraisals)}."
    )


@pytest.mark.parametrize(
    "example_file",
    valid_example_files(),
    ids=example_id,
)
def test_valid_example_appraisal_conforms_to_urar_shapes(example_file: Path):
    conforms, results_graph, results_text = validate(
        data_graph=load_data_graph(example_file),
        shacl_graph=load_shapes_graph(),
        inference="none",
        abort_on_first=False,
        allow_infos=True,
        allow_warnings=True,
    )

    if not conforms:
        report_text = format_shacl_results(results_graph, results_text)
        report_file = write_shacl_report(example_file, report_text)

        pytest.fail(
            f"SHACL validation failed for {example_id(example_file)}. "
            f"Report written to {report_file}.\n\n{report_text}",
            pytrace=False,
        )


@pytest.mark.parametrize(
    "example_file",
    invalid_example_files(),
    ids=example_id,
)
def test_invalid_example_appraisal_fails_urar_shapes(example_file: Path):
    conforms, results_graph, results_text = validate(
        data_graph=load_data_graph(example_file),
        shacl_graph=load_shapes_graph(),
        inference="none",
        abort_on_first=False,
        allow_infos=True,
        allow_warnings=True,
    )

    if conforms:
        pytest.fail(
            f"{example_id(example_file)} was expected to fail SHACL validation "
            f"but conformed.",
            pytrace=False,
        )

    report_text = format_shacl_results(results_graph, results_text)
    write_shacl_report(example_file, report_text)