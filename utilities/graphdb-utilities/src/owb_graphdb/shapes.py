"""Install and retrieve caller-supplied SHACL shape sets."""

from dataclasses import dataclass
from hashlib import sha256
from urllib.parse import quote, urlencode

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.compare import isomorphic
from rdflib.namespace import RDF, XSD

from owb_graphdb.client import GraphDBClient
from owb_graphdb.configuration import RepositoryConfiguration
from owb_graphdb.errors import RepositoryVerificationError


SH = Namespace("http://www.w3.org/ns/shacl#")
META = Namespace("urn:owb:graphdb:shape-set:")

SHAPES_GRAPH = URIRef("urn:owb:graphdb:shapes")
MAPPING_GRAPH = URIRef(
    "http://rdf4j.org/schema/rdf4j#SHACLShapeGraph"
)
METADATA_GRAPH = URIRef("urn:owb:graphdb:shape-set-metadata")
SHAPE_SET = URIRef("urn:owb:graphdb:installed-shape-set")


@dataclass(frozen=True)
class InstalledShapeSet:
    """Shapes and metadata retrieved from GraphDB.

    content_digest is the lowercase SHA-256 digest of the original
    supplied Turtle bytes. data_graph_iris preserves configured order.
    """

    graph: Graph
    version: str
    content_digest: str
    data_graph_iris: tuple[str, ...]


def _statements_path(
    configuration: RepositoryConfiguration,
) -> str:
    repository_id = quote(configuration.repository_id, safe="")
    return f"/repositories/{repository_id}/statements"


def _serialize_named_graphs(graphs: tuple[Graph, ...]) -> bytes:
    """Serialize named graphs as TriG without deprecated Dataset APIs.

    N-Triples statements are valid inside a TriG named-graph block.
    RDFLib handles RDF term escaping, literal datatypes, and languages.
    """
    blocks: list[bytes] = []

    for graph in graphs:
        if not isinstance(graph.identifier, URIRef):
            raise RepositoryVerificationError(
                "Each stored graph must have an IRI identifier."
            )

        statements = graph.serialize(format="nt", encoding="utf-8")
        blocks.append(
            graph.identifier.n3().encode("utf-8")
            + b" {\n"
            + statements
            + b"}\n"
        )

    return b"".join(blocks)


def _read_graph(
    *,
    client: GraphDBClient,
    configuration: RepositoryConfiguration,
    graph_iri: URIRef,
) -> Graph:
    query = urlencode({"context": f"<{graph_iri}>"})
    content = client.request(
        method="GET",
        path=f"{_statements_path(configuration)}?{query}",
        accept="text/turtle",
    )
    graph = Graph()
    if content.strip():
        graph.parse(data=content, format="turtle")
    return graph


def _single_value(graph: Graph, predicate: URIRef):
    values = list(graph.objects(SHAPE_SET, predicate))
    if len(values) != 1:
        raise RepositoryVerificationError(
            f"Installed shape metadata requires one {predicate} value."
        )
    return values[0]


def _read_scope(graph: Graph) -> tuple[str, ...]:
    node = _single_value(graph, META.dataGraphs)
    values: list[str] = []
    visited = set()

    while node != RDF.nil:
        if node in visited or not isinstance(node, (BNode, URIRef)):
            raise RepositoryVerificationError(
                "Installed shape scope contains an invalid RDF list."
            )
        visited.add(node)

        items = list(graph.objects(node, RDF.first))
        successors = list(graph.objects(node, RDF.rest))
        if (
            len(items) != 1
            or len(successors) != 1
            or not isinstance(items[0], URIRef)
        ):
            raise RepositoryVerificationError(
                "Installed shape scope contains an invalid RDF list."
            )

        values.append(str(items[0]))
        node = successors[0]

    if not values or len(set(values)) != len(values):
        raise RepositoryVerificationError(
            "Installed shape scope must contain distinct data graph IRIs."
        )

    return tuple(values)


def install_shape_set(
    *,
    client: GraphDBClient,
    configuration: RepositoryConfiguration,
) -> None:
    """Persist shapes, scope mappings, and metadata together.

    The repository must already have SHACL enabled and must register
    both MAPPING_GRAPH and SHAPES_GRAPH as SHACL shapes graphs.

    Installing over an existing application shape set is unsupported.
    """
    scope = tuple(configuration.data_graph_iris)
    reserved = {
        str(SHAPES_GRAPH),
        str(MAPPING_GRAPH),
        str(METADATA_GRAPH),
    }

    if (
        not configuration.shapes_version.strip()
        or not scope
        or len(set(scope)) != len(scope)
        or any(
            not isinstance(iri, str)
            or ":" not in iri
            or any(character.isspace() for character in iri)
            or iri in reserved
            for iri in scope
        )
    ):
        raise RepositoryVerificationError(
            "Supply a shape version and distinct absolute data graph IRIs "
            "that do not overlap the utility's internal graphs."
        )

    supplied_bytes = configuration.shapes_path.read_bytes()
    supplied_graph = Graph()
    supplied_graph.parse(data=supplied_bytes, format="turtle")

    if not supplied_graph:
        raise RepositoryVerificationError(
            "The supplied shape set is empty."
        )

    for graph_iri in (SHAPES_GRAPH, METADATA_GRAPH):
        existing = _read_graph(
            client=client,
            configuration=configuration,
            graph_iri=graph_iri,
        )
        if existing:
            raise RepositoryVerificationError(
                "An application shape set or its metadata already exists. "
                "Shape upgrades are outside this operation."
            )

    mappings = _read_graph(
        client=client,
        configuration=configuration,
        graph_iri=MAPPING_GRAPH,
    )
    for data_iri in scope:
        if list(mappings.objects(URIRef(data_iri), SH.shapesGraph)):
            raise RepositoryVerificationError(
                f"A shape mapping already exists for {data_iri}."
            )

    digest = sha256(supplied_bytes).hexdigest()

    stored_shapes = Graph(identifier=SHAPES_GRAPH)
    for triple in supplied_graph:
        stored_shapes.add(triple)

    stored_mappings = Graph(identifier=MAPPING_GRAPH)
    for data_iri in scope:
        stored_mappings.add(
            (URIRef(data_iri), SH.shapesGraph, SHAPES_GRAPH)
        )

    metadata = Graph(identifier=METADATA_GRAPH)
    metadata.add((SHAPE_SET, RDF.type, META.InstalledShapeSet))
    metadata.add((SHAPE_SET, META.shapesGraph, SHAPES_GRAPH))
    metadata.add(
        (
            SHAPE_SET,
            META.version,
            Literal(configuration.shapes_version, datatype=XSD.string),
        )
    )
    metadata.add(
        (
            SHAPE_SET,
            META.contentDigest,
            Literal(digest, datatype=XSD.string),
        )
    )

    scope_head = BNode()
    metadata.add((SHAPE_SET, META.dataGraphs, scope_head))
    Collection(
        metadata,
        scope_head,
        [URIRef(data_iri) for data_iri in scope],
    )

    # One statements request commits all three named graphs together.
    # GraphDB performs its enabled SHACL validation at commit.
    client.request(
        method="POST",
        path=_statements_path(configuration),
        body=_serialize_named_graphs(
            (stored_shapes, stored_mappings, metadata)
        ),
        content_type="application/trig",
    )

    installed = retrieve_shape_set(
        client=client,
        configuration=configuration,
    )
    if (
        installed.version != configuration.shapes_version
        or installed.content_digest != digest
        or installed.data_graph_iris != scope
        or not isomorphic(installed.graph, supplied_graph)
    ):
        raise RepositoryVerificationError(
            "The persisted shape set does not match the supplied shape set."
        )


def retrieve_shape_set(
    *,
    client: GraphDBClient,
    configuration: RepositoryConfiguration,
) -> InstalledShapeSet:
    """Read installed shapes and metadata without reading local files."""
    metadata = _read_graph(
        client=client,
        configuration=configuration,
        graph_iri=METADATA_GRAPH,
    )

    if (SHAPE_SET, RDF.type, META.InstalledShapeSet) not in metadata:
        raise RepositoryVerificationError(
            "No installed application shape set was found."
        )

    if _single_value(metadata, META.shapesGraph) != SHAPES_GRAPH:
        raise RepositoryVerificationError(
            "Installed shape metadata identifies an unexpected shapes graph."
        )

    version = _single_value(metadata, META.version)
    digest = _single_value(metadata, META.contentDigest)

    if (
        not isinstance(version, Literal)
        or not str(version).strip()
        or not isinstance(digest, Literal)
        or len(str(digest)) != 64
        or any(character not in "0123456789abcdef" for character in str(digest))
    ):
        raise RepositoryVerificationError(
            "Installed shape version or content digest is invalid."
        )

    scope = _read_scope(metadata)
    mappings = _read_graph(
        client=client,
        configuration=configuration,
        graph_iri=MAPPING_GRAPH,
    )
    for data_iri in scope:
        if (URIRef(data_iri), SH.shapesGraph, SHAPES_GRAPH) not in mappings:
            raise RepositoryVerificationError(
                f"The installed shape mapping is missing for {data_iri}."
            )

    shapes = _read_graph(
        client=client,
        configuration=configuration,
        graph_iri=SHAPES_GRAPH,
    )
    if not shapes:
        raise RepositoryVerificationError(
            "The installed shapes graph is empty."
        )

    return InstalledShapeSet(
        graph=shapes,
        version=str(version),
        content_digest=str(digest),
        data_graph_iris=scope,
    )