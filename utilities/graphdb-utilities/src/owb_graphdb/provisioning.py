"""Coordinate GraphDB repository provisioning and verification."""

import json
from dataclasses import dataclass
from hashlib import sha256
from urllib.parse import quote
from uuid import uuid4

from rdflib import BNode, Graph, Literal, Namespace, RDF, XSD
from rdflib.compare import isomorphic

from owb_graphdb.client import GraphDBClient
from owb_graphdb.configuration import RepositoryConfiguration
from owb_graphdb.errors import (
    GraphDBConfigurationError,
    GraphDBConnectionError,
    GraphDBError,
    GraphDBHTTPError,
    RepositoryVerificationError,
)
from owb_graphdb.shapes import retrieve_shape_set

REP = Namespace("http://www.openrdf.org/config/repository#")
SAIL = Namespace("http://www.openrdf.org/config/sail#")
SHACL_CONFIG = Namespace("http://rdf4j.org/config/sail/shacl#")


@dataclass(frozen=True)
class RepositorySetupResult:
    """Report the outcome of a repository setup attempt."""

    success: bool
    ready: bool
    message: str
    server_url: str | None = None
    repository_id: str | None = None
    shapes_version: str | None = None
    content_digest: str | None = None
    data_graph_iris: tuple[str, ...] = ()


def _configuration_boolean(value) -> bool | None:
    """Interpret supported Boolean representations in configuration."""
    if not isinstance(value, Literal):
        return None

    if value.language is not None:
        return None

    if value.datatype not in (None, XSD.string, XSD.boolean):
        return None

    lexical_value = str(value).strip()

    if lexical_value in ("true", "1"):
        return True

    if lexical_value in ("false", "0"):
        return False

    return None


def _normalized_configuration(configuration: Graph) -> Graph:
    """Normalize the SHACL validation-enabled configuration value."""
    normalized = Graph()

    for subject, predicate, obj in configuration:
        if predicate == SHACL_CONFIG.validationEnabled:
            boolean_value = _configuration_boolean(obj)
            if boolean_value is not None:
                obj = Literal(boolean_value)

        normalized.add((subject, predicate, obj))

    return normalized


def _shacl_enabled(configuration: Graph) -> bool:
    """Require an explicit, unambiguous enabled setting on a SHACL sail."""
    for sail in configuration.subjects(
        SAIL.sailType,
        Literal("rdf4j:ShaclSail"),
    ):
        values = list(
            configuration.objects(sail, SHACL_CONFIG.validationEnabled)
        )

        if values and all(
            _configuration_boolean(value) is True for value in values
        ):
            return True

    return False


def _read_required_configuration(
    configuration: RepositoryConfiguration,
) -> tuple[bytes, Graph]:
    """Read and check configuration before making GraphDB changes."""
    if not configuration.repository_id.strip():
        raise GraphDBConfigurationError(
            "A nonempty repository ID is required."
        )

    try:
        content = configuration.repository_config_path.read_bytes()
        required = Graph().parse(data=content, format="turtle")
    except Exception:
        raise GraphDBConfigurationError(
            "The repository configuration could not be read as Turtle."
        ) from None

    repositories = list(required.subjects(RDF.type, REP.Repository))
    if len(repositories) != 1:
        raise GraphDBConfigurationError(
            "The configuration must describe exactly one repository."
        )

    identifiers = list(
        required.objects(repositories[0], REP.repositoryID)
    )
    if identifiers != [Literal(configuration.repository_id)]:
        raise GraphDBConfigurationError(
            "The configuration repository ID must match the requested ID."
        )

    if not _shacl_enabled(required):
        raise GraphDBConfigurationError(
            "The configuration must explicitly enable SHACL validation."
        )

    return content, required


def _check_shape_set(
    configuration: RepositoryConfiguration,
) -> RepositorySetupResult | None:
    """Reject unreadable or unparseable shapes before contacting GraphDB."""
    try:
        content = configuration.shapes_path.read_bytes()
    except OSError:
        return RepositorySetupResult(
            success=False,
            ready=False,
            message=(
                "Invalid shape set: the supplied shape file "
                "could not be read."
            ),
        )

    try:
        Graph().parse(data=content, format="turtle")
    except Exception:
        return RepositorySetupResult(
            success=False,
            ready=False,
            message=(
                "Invalid shape set: the supplied shapes "
                "could not be parsed as Turtle."
            ),
        )

    return None


def _multipart_configuration(content: bytes) -> tuple[bytes, str]:
    """Encode the configuration file as a multipart form field."""
    boundary = f"owb-graphdb-{uuid4().hex}"

    while boundary.encode("ascii") in content:
        boundary = f"owb-graphdb-{uuid4().hex}"

    prefix = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="config"; '
        'filename="repository-config.ttl"\r\n'
        "Content-Type: text/turtle\r\n"
        "\r\n"
    ).encode("ascii")

    suffix = f"\r\n--{boundary}--\r\n".encode("ascii")
    body = prefix + content + suffix
    content_type = f"multipart/form-data; boundary={boundary}"

    return body, content_type


def _matches_requirements(required: Graph, actual: Graph) -> bool:
    """Match required configuration independently of blank-node labels."""
    required = _normalized_configuration(required)
    actual = _normalized_configuration(actual)
    variables: dict[BNode, str] = {}

    def term(value) -> str:
        if isinstance(value, BNode):
            if value not in variables:
                variables[value] = f"?node{len(variables)}"
            return variables[value]

        return value.n3()

    patterns = "\n".join(
        f"{term(subject)} {term(predicate)} {term(obj)} ."
        for subject, predicate, obj in required
    )

    result = actual.query(f"ASK WHERE {{\n{patterns}\n}}")
    return bool(result.askAnswer)


def _normalized_shape_graph(graph: Graph) -> Graph:
    """Treat plain strings and explicit xsd:string literals equivalently."""
    normalized = Graph()

    for subject, predicate, obj in graph:
        if (
            isinstance(obj, Literal)
            and obj.language is None
            and obj.datatype in (None, XSD.string)
        ):
            obj = Literal(str(obj), datatype=XSD.string)

        normalized.add((subject, predicate, obj))

    return normalized


def _incompatible_settings(required: Graph, actual: Graph) -> str:
    """Identify unmet settings along their repository configuration paths.

    Compare RDF patterns rather than blank-node identifiers. Keep diagnostic
    output to predicate IRIs; caller-supplied values may contain secrets.
    """
    incompatible: set[str] = set()
    roots = list(required.subjects(RDF.type, REP.Repository))

    def visit(subject, path, ancestors):
        for predicate, obj in required.predicate_objects(subject):
            triple = (subject, predicate, obj)
            probe = Graph()
            for edge in path:
                probe.add(edge)
            probe.add(triple)
            if not _matches_requirements(probe, actual):
                incompatible.add(str(predicate))
                continue
            if isinstance(obj, BNode) and obj not in ancestors:
                visit(obj, path + (triple,), ancestors | {obj})

    for root in roots:
        anchor = tuple(required.triples((root, REP.repositoryID, None)))
        visit(root, anchor, {root})

    if incompatible:
        return "incompatible settings: " + ", ".join(sorted(incompatible)) + "."

    # Individual paths can match while their combined blank-node relationships
    # do not. Preserve failure and identify the settings involved in that case.
    predicates = sorted({str(predicate) for _, predicate, _ in required})
    return (
        "incompatible configuration relationships involving settings: "
        + ", ".join(predicates)
        + "."
    )

def _verify_existing_repository(
    *,
    client: GraphDBClient,
    configuration: RepositoryConfiguration,
    required: Graph,
) -> RepositorySetupResult:
    """Verify only the requested repository, without modifying it."""
    repository_id = configuration.repository_id
    encoded_id = quote(repository_id, safe="")

    def failure(reason: str) -> RepositorySetupResult:
        return RepositorySetupResult(
            success=False,
            ready=False,
            message=(
                f"Existing repository '{repository_id}' is not ready: "
                f"{reason} No repository changes were made."
            ),
        )

    try:
        response = client.request(
            method="GET",
            path=f"/rest/repositories/{encoded_id}",
            accept="text/turtle",
        )
    except GraphDBError:
        return failure(
            "its configuration could not be retrieved."
        )

    try:
        actual = Graph().parse(data=response, format="turtle")
    except Exception:
        return failure(
            "its configuration could not be read as Turtle."
        )

    if not _shacl_enabled(actual):
        return failure(
            "SHACL validation is not explicitly enabled."
        )

    if not _matches_requirements(required, actual):
        return failure(
            _incompatible_settings(required, actual)
        )

    try:
        supplied_content = configuration.shapes_path.read_bytes()
        supplied_graph = Graph().parse(
            data=supplied_content,
            format="turtle",
        )
    except Exception:
        return failure(
            "the supplied shape set could not be read as Turtle."
        )

    try:
        installed = retrieve_shape_set(
            client=client,
            configuration=configuration,
        )
    except GraphDBError:
        return failure(
            "the installed shape set or its metadata could not be verified."
        )

    if installed.version != configuration.shapes_version:
        return failure(
            "the installed shape version differs from the supplied version."
        )

    expected_digest = sha256(supplied_content).hexdigest()

    if installed.content_digest != expected_digest:
        return failure("the installed shape digest differs from the supplied digest.")

    if not isomorphic(
        _normalized_shape_graph(supplied_graph),
        _normalized_shape_graph(installed.graph),
    ):
        return failure("the installed shapes differ from the supplied shapes.")

    if set(installed.data_graph_iris) != set(configuration.data_graph_iris):
        return failure("the installed SHACL data-graph scope differs from the supplied scope.")

    return RepositorySetupResult(
        success=True,
        ready=True,
        server_url=configuration.server_url.rstrip("/"),
        repository_id=repository_id,
        shapes_version=installed.version,
        content_digest=installed.content_digest,
        data_graph_iris=tuple(installed.data_graph_iris),
        message=(
            f"Existing repository '{repository_id}' is ready. "
            "Configuration and installed shapes match the supplied requirements. "
            "No repository changes were made."
        ),
    )


def provision_repository(
    *,
    client: GraphDBClient,
    configuration: RepositoryConfiguration,
) -> RepositorySetupResult | None:
    """Verify an existing repository or create and verify a missing one.

    Return None only when a newly created repository is ready for shape
    installation. Existing repositories are inspected without writes.
    """
    repository_id = configuration.repository_id
    created = False

    def failure(reason: str) -> RepositorySetupResult:
        state = (
            "was created but is not ready; it has been preserved for inspection"
            if created else "is not ready"
        )
        return RepositorySetupResult(
            success=False,
            ready=False,
            message=f"Repository '{repository_id}' {state}. {reason}",
        )

    try:
        content, required = _read_required_configuration(configuration)
    except GraphDBConfigurationError as error:
        return failure(str(error))

    shape_error = _check_shape_set(configuration)
    if shape_error is not None:
        return shape_error

    try:
        response = client.request(
            method="GET",
            path="/rest/repositories",
            accept="application/json",
        )
        try:
            repositories = json.loads(response)
            if not isinstance(repositories, list) or any(
                not isinstance(item, dict) or not isinstance(item.get("id"), str)
                for item in repositories
            ):
                return failure("The server returned an invalid repository listing.")
        except (ValueError, UnicodeError):
            return failure("The server returned an unreadable repository listing.")

        if any(item["id"] == repository_id for item in repositories):
            return _verify_existing_repository(
                client=client,
                configuration=configuration,
                required=required,
            )

        body, content_type = _multipart_configuration(content)
        client.request(
            method="POST",
            path="/rest/repositories",
            body=body,
            content_type=content_type,
        )
        created = True

        response = client.request(
            method="GET",
            path=f"/rest/repositories/{quote(repository_id, safe='')}",
            accept="text/turtle",
        )
        try:
            actual = Graph().parse(data=response, format="turtle")
        except Exception:
            return failure("Created repository configuration could not be read as Turtle.")

        if not _shacl_enabled(actual):
            return failure("SHACL validation is not explicitly enabled.")
        if not _matches_requirements(required, actual):
            return failure("Created repository configuration does not match supplied requirements.")

    except GraphDBConnectionError:
        return failure(f"Cannot connect to the configured server {configuration.server_url}.")
    except GraphDBHTTPError as error:
        if error.status_code in (401, 403):
            return failure("The operator is not authorized to provision the repository.")
        return failure(f"Repository provisioning failed with HTTP status {error.status_code}.")
    except GraphDBError:
        return failure("Repository provisioning or verification failed.")

    return None


