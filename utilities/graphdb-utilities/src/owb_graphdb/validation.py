"""Verify GraphDB repository configuration and SHACL enforcement."""

from urllib.parse import quote, urlencode, urlsplit

from decimal import Decimal
from dataclasses import dataclass
import json

from rdflib import Graph, Literal, Namespace, RDF, XSD
from rdflib.compare import graph_diff, isomorphic, to_isomorphic

from owb_graphdb.errors import GraphDBError, GraphDBHTTPError, RepositoryVerificationError
from owb_graphdb.provisioning import (
    _normalized_shape_graph,
    _read_required_configuration,
    _verify_existing_repository,
)
from owb_graphdb.shapes import MAPPING_GRAPH, METADATA_GRAPH, SHAPES_GRAPH

from owb_graphdb.client import GraphDBClient
from owb_graphdb.configuration import RepositoryConfiguration


def verify_repository(
    *,
    client: GraphDBClient,
    configuration: RepositoryConfiguration,
) -> None:
    """Verify that a repository meets the supplied requirements.

    Verification must confirm the repository configuration,
    active SHACL shape version, and validation graph scope.

    A successful return means all required checks passed.
    A failed check must raise an appropriate GraphDB utility exception.

    This initial stub performs no network requests, reads no files,
    and makes no GraphDB changes.
    """
    raise NotImplementedError(
        "GraphDB repository verification is not implemented."
    )


def _normalized_verification_graph(graph: Graph) -> Graph:
    """Compare decimal values without treating trailing zeroes as precision.

    Preserve datatype IRIs, other RDF terms, and invalid literals. Fixed-point
    formatting avoids floating-point conversion and Decimal context rounding.
    """
    result = Graph()
    for subject, predicate, obj in _normalized_shape_graph(graph):
        if isinstance(obj, Literal) and obj.datatype == XSD.decimal:
            value = obj.toPython()
            if isinstance(value, Decimal) and value.is_finite():
                lexical = format(value, "f")
                if "." in lexical:
                    lexical = lexical.rstrip("0").rstrip(".")
                if value == 0:
                    lexical = "0"
                obj = Literal(lexical, datatype=XSD.decimal, normalize=False)
        result.add((subject, predicate, obj))
    return result

def verify_conforming_dataset(
    *,
    client: GraphDBClient,
    configuration: RepositoryConfiguration,
    dataset: Graph,
    verification_graph_iri: str,
) -> "DatasetVerificationResult | None":
    """Commit, retrieve, compare, and remove caller-supplied verification RDF.

    The caller must reserve the verification graph exclusively for this check.
    It must be empty and inside the installed SHACL validation scope. Normal
    returning None means persistence, RDF equivalence, and cleanup succeeded.
    Cleanup failure returns success=False and ready=False with the graph IRI.
    """
    graph_iri = str(verification_graph_iri)
    reserved = {str(SHAPES_GRAPH), str(MAPPING_GRAPH), str(METADATA_GRAPH)}
    if (
        not urlsplit(graph_iri).scheme
        or any(character.isspace() or character in '<>"{}|^`\\' for character in graph_iri)
        or graph_iri in reserved
        or graph_iri not in configuration.data_graph_iris
    ):
        raise RepositoryVerificationError(
            "Supply an isolated verification graph IRI within the configured "
            "validation scope and outside the utility's internal graphs."
        )
    if not isinstance(dataset, Graph) or not dataset:
        raise RepositoryVerificationError("Supply a nonempty RDF verification graph.")

    # Reuse read-only verification, never provisioning: a missing or incompatible
    # repository must not be created, upgraded, or repaired by this check.
    _, required = _read_required_configuration(configuration)
    readiness = _verify_existing_repository(
        client=client, configuration=configuration, required=required,
    )
    if not readiness.success or not readiness.ready:
        raise RepositoryVerificationError(readiness.message)

    repository_id = quote(configuration.repository_id, safe="")
    endpoint = f"/repositories/{repository_id}/statements"
    context = {"context": f"<{graph_iri}>"}
    write_path = endpoint + "?" + urlencode(context)
    read_path = endpoint + "?" + urlencode({**context, "infer": "false"})

    def read_graph() -> Graph:
        content = client.request(method="GET", path=read_path, accept="text/turtle")
        graph = Graph()
        if content.strip():
            try:
                graph.parse(data=content, format="turtle")
            except Exception:
                raise RepositoryVerificationError(
                    "The persisted verification RDF could not be read as Turtle."
                ) from None
        return graph

    if read_graph():
        raise RepositoryVerificationError(
            "The verification graph already contains RDF; no changes were made."
        )

    # Snapshot the input so comparison does not depend on later caller changes.
    expected = Graph()
    for triple in dataset:
        expected.add(triple)
    payload = expected.serialize(format="turtle", encoding="utf-8")

    verification_error = None
    try:
        # A successful statements POST commits this RDF to the named graph.
        client.request(
            method="POST", path=write_path,
            body=payload, content_type="text/turtle",
        )
        persisted = read_graph()
        if not isomorphic(
            _normalized_verification_graph(expected),
            _normalized_verification_graph(persisted),
        ):
            _, missing, unexpected = graph_diff(
                to_isomorphic(_normalized_verification_graph(expected)),
                to_isomorphic(_normalized_verification_graph(persisted)),
            )

            def describe(graph):
                # Explicit N3 terms expose lexical forms and datatype IRIs.
                return "\n".join(sorted(
                    " ".join(term.n3() for term in triple) + " ."
                    for triple in graph
                )) or "(none)"

            raise RepositoryVerificationError(
                "Persisted verification RDF is not equivalent to the supplied dataset.\n"
                f"Expected triples: {len(expected)}; retrieved triples: {len(persisted)}\n"
                f"Missing triples:\n{describe(missing)}\n"
                f"Unexpected triples:\n{describe(unexpected)}"
            )
    except GraphDBError as error:
        verification_error = error

    # Always attempt scoped cleanup, including after an uncertain write.
    # Report cleanup failure as a result rather than suppressing exceptions
    # with a return from a finally block.
    try:
        client.request(method="DELETE", path=write_path)
        if read_graph():
            raise RepositoryVerificationError("Verification RDF remains after cleanup.")
    except GraphDBError:
        return DatasetVerificationResult(
            success=False,
            ready=False,
            message=(
                f"Verification cleanup failed for graph '{graph_iri}'. "
                "Inspect this graph before repeating verification."
            ),
        )

    if verification_error is not None:
        raise verification_error
    return None

@dataclass(frozen=True)
class DatasetVerificationResult:
    """Dataset-check outcome; a single check never establishes repository readiness."""

    success: bool
    message: str
    ready: bool = False


def _has_shacl_rejection_report(error: GraphDBHTTPError, dataset: Graph) -> bool:
    """Require a nonconforming RDF report about a supplied focus node.

    Accept Turtle reports, including reports embedded in JSON error messages
    or preceded by an exception heading. Never accept a status code or the
    word 'SHACL' alone as evidence of validation rejection.
    """
    text = error.response_body.decode("utf-8", errors="replace")
    candidates = [text]

    def collect_strings(value):
        if isinstance(value, str):
            candidates.append(value)
        elif isinstance(value, dict):
            for item in value.values():
                collect_strings(item)
        elif isinstance(value, list):
            for item in value:
                collect_strings(item)

    try:
        collect_strings(json.loads(text))
    except (ValueError, RecursionError):
        pass

    sh = Namespace("http://www.w3.org/ns/shacl#")
    supplied_nodes = set(dataset.all_nodes())
    for candidate in candidates:
        variants = [candidate]
        for marker in ("@prefix", "PREFIX "):
            position = candidate.find(marker)
            if position > 0:
                variants.append(candidate[position:])
        for variant in variants:
            report_graph = Graph()
            try:
                report_graph.parse(data=variant, format="turtle")
            except Exception:
                continue
            for report in report_graph.subjects(RDF.type, sh.ValidationReport):
                if (report, sh.conforms, Literal(False)) not in report_graph:
                    continue
                for result in report_graph.objects(report, sh.result):
                    if (
                        any(node in supplied_nodes for node in report_graph.objects(result, sh.focusNode))
                        and any(report_graph.objects(result, sh.sourceShape))
                        and any(report_graph.objects(result, sh.sourceConstraintComponent))
                    ):
                        return True
    return False


def verify_nonconforming_dataset(
    *,
    client: GraphDBClient,
    configuration: RepositoryConfiguration,
    dataset: Graph,
    verification_graph_iri: str,
) -> DatasetVerificationResult:
    """Verify real SHACL rejection and absence of committed verification RDF.

    The caller exclusively reserves an initially empty graph for this check.
    A successful result means validation rejected the dataset as expected.
    """
    graph_iri = str(verification_graph_iri)
    reserved = {str(SHAPES_GRAPH), str(MAPPING_GRAPH), str(METADATA_GRAPH)}
    if (
        not urlsplit(graph_iri).scheme
        or any(character.isspace() or character in '<>"{}|^`\\' for character in graph_iri)
        or graph_iri in reserved
        or graph_iri not in configuration.data_graph_iris
    ):
        raise RepositoryVerificationError(
            "Supply an isolated verification graph IRI within the configured "
            "validation scope and outside the utility's internal graphs."
        )
    if not isinstance(dataset, Graph) or not dataset:
        raise RepositoryVerificationError("Supply a nonempty RDF verification graph.")

    _, required = _read_required_configuration(configuration)
    readiness = _verify_existing_repository(
        client=client, configuration=configuration, required=required,
    )
    if not readiness.success or not readiness.ready:
        raise RepositoryVerificationError(readiness.message)

    endpoint = f"/repositories/{quote(configuration.repository_id, safe='')}/statements"
    context = {"context": f"<{graph_iri}>"}
    write_path = endpoint + "?" + urlencode(context)
    read_path = endpoint + "?" + urlencode({**context, "infer": "false"})

    def read_graph():
        content = client.request(method="GET", path=read_path, accept="text/turtle")
        graph = Graph()
        if content.strip():
            try:
                graph.parse(data=content, format="turtle")
            except Exception:
                raise RepositoryVerificationError(
                    "Verification graph contents could not be read as Turtle."
                ) from None
        return graph

    if read_graph():
        raise RepositoryVerificationError(
            "The verification graph already contains RDF; no changes were made."
        )
    supplied = Graph()
    for triple in dataset:
        supplied.add(triple)
    payload = supplied.serialize(format="turtle", encoding="utf-8")

    verification_error = None
    result = None
    try:
        try:
            client.request(
                method="POST", path=write_path,
                body=payload, content_type="text/turtle",
            )
        except GraphDBHTTPError as error:
            # Check before cleanup: deleting accepted RDF cannot demonstrate
            # that GraphDB rolled back a rejected transaction.
            if read_graph():
                raise RepositoryVerificationError(
                    "The failed write left committed verification RDF."
                ) from None
            if not _has_shacl_rejection_report(error, supplied):
                raise RepositoryVerificationError(
                    f"HTTP {error.status_code} did not include a recognized "
                    "nonconforming SHACL report for the supplied dataset; "
                    "expected validation rejection could not be verified."
                ) from None
            result = DatasetVerificationResult(
                success=True,
                message=(
                    "Expected SHACL validation rejection verified. "
                    "None of the verification dataset was committed."
                ),
            )
        else:
            raise RepositoryVerificationError(
                "GraphDB accepted the nonconforming dataset; expected SHACL "
                "validation rejection did not occur."
            )
    except GraphDBError as error:
        verification_error = error

    try:
        if read_graph():
            client.request(method="DELETE", path=write_path)
            if read_graph():
                raise RepositoryVerificationError("Verification RDF remains after cleanup.")
    except GraphDBError:
        return DatasetVerificationResult(
            success=False,
            ready=False,
            message=(
                f"Verification cleanup could not be confirmed for graph '{graph_iri}'. "
                "Inspect this graph before repeating verification."
            ),
        )

    if verification_error is not None:
        raise verification_error
    return result
