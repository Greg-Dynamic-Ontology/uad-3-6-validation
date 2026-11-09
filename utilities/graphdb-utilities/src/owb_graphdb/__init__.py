"""Noninteractive application entry point for GraphDB setup and verification."""

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from rdflib import Graph

from owb_graphdb.client import GraphDBClient
from owb_graphdb.configuration import RepositoryConfiguration
from owb_graphdb.errors import GraphDBError
from owb_graphdb.setup import setup_repository as _setup_repository
from owb_graphdb.shapes import retrieve_shape_set
from owb_graphdb.validation import (
    verify_conforming_dataset,
    verify_nonconforming_dataset,
)

__all__ = ["ApplicationSetupResult", "setup_repository"]


@dataclass(frozen=True)
class ApplicationSetupResult:
    """JSON-compatible fields; serialize with dataclasses.asdict()."""

    success: bool
    ready: bool
    message: str
    server_url: str
    repository_id: str
    shapes_version: str | None = None
    content_digest: str | None = None
    data_graph_iris: tuple[str, ...] = ()
    failed_step: str | None = None
    diagnostics: tuple[str, ...] = ()


def setup_repository(
    *,
    server_url: str,
    repository_id: str,
    repository_config_path: Path,
    shapes_path: Path,
    shapes_version: str,
    data_graph_iris: tuple[str, ...],
    conforming_dataset: Graph,
    nonconforming_dataset: Graph,
    verification_graph_iri: str,
    headers: Mapping[str, str] | None = None,
) -> ApplicationSetupResult:
    """Set up and verify a repository without prompts or diagnostic printing.

    The caller reserves an empty verification graph exclusively for these checks.
    Readiness is returned only after both dataset checks and cleanup succeed.
    Credentials are used only by the HTTP client and excluded from results.
    """
    secrets = set()
    for value in (headers or {}).values():
        if isinstance(value, str) and value:
            secrets.add(value)
    authorization = next(
        (value for name, value in (headers or {}).items()
         if name.lower() == "authorization"),
        "",
    )
    if isinstance(authorization, str) and " " in authorization:
        secrets.add(authorization.split(" ", 1)[1])

    # Never return userinfo, query strings, or fragments from a supplied URL.
    # The client separately rejects unsupported URL forms before making requests.
    try:
        parsed = urlsplit(server_url)
        if parsed.username:
            secrets.add(parsed.username)
        if parsed.password:
            secrets.add(parsed.password)
        safe_url = urlunsplit((
            parsed.scheme, parsed.netloc.rsplit("@", 1)[-1],
            parsed.path.rstrip("/"), "", "",
        ))
    except ValueError:
        safe_url = ""

    def sanitized(value: str) -> str:
        for secret in sorted(secrets, key=len, reverse=True):
            if secret:
                value = value.replace(secret, "[REDACTED]")
        return value

    safe_url = sanitized(safe_url)
    safe_id = sanitized(repository_id)
    step = "configuration"

    def failure(detail: str) -> ApplicationSetupResult:
        return ApplicationSetupResult(
            success=False,
            ready=False,
            message=f"Repository setup failed during {step}.",
            server_url=safe_url,
            repository_id=safe_id,
            failed_step=step,
            diagnostics=(sanitized(detail),),
        )

    try:
        if not isinstance(conforming_dataset, Graph) or not conforming_dataset:
            return failure("Supply a nonempty conforming RDF dataset.")
        if not isinstance(nonconforming_dataset, Graph) or not nonconforming_dataset:
            return failure("Supply a nonempty nonconforming RDF dataset.")
        if verification_graph_iri not in data_graph_iris:
            return failure("The verification graph must be within the supplied validation scope.")
        configuration = RepositoryConfiguration(
            server_url=server_url,
            repository_id=repository_id,
            repository_config_path=Path(repository_config_path),
            shapes_path=Path(shapes_path),
            shapes_version=shapes_version,
            data_graph_iris=tuple(data_graph_iris),
        )
        client = GraphDBClient(server_url=server_url, headers=headers, timeout_seconds=30)

        step = "provisioning"
        setup_result = _setup_repository(client=client, configuration=configuration)
        if not setup_result.success or not setup_result.ready:
            return failure(setup_result.message)

        step = "conforming_verification"
        positive = verify_conforming_dataset(
            client=client,
            configuration=configuration,
            dataset=conforming_dataset,
            verification_graph_iri=verification_graph_iri,
        )
        # The existing conforming operation returns None on success and an
        # explicit failure result if cleanup could not be completed.
        if positive is not None and not positive.success:
            step = "verification_cleanup"
            return failure(positive.message)

        step = "nonconforming_verification"
        negative = verify_nonconforming_dataset(
            client=client,
            configuration=configuration,
            dataset=nonconforming_dataset,
            verification_graph_iri=verification_graph_iri,
        )
        if not negative.success:
            step = "verification_cleanup"
            return failure(negative.message)

        step = "result_metadata"
        installed = retrieve_shape_set(client=client, configuration=configuration)
        if (
            installed.version != configuration.shapes_version
            or installed.content_digest != sha256(configuration.shapes_path.read_bytes()).hexdigest()
            or set(installed.data_graph_iris) != set(configuration.data_graph_iris)
        ):
            return failure("Installed shape metadata changed or no longer matches the verified inputs.")
        return ApplicationSetupResult(
            success=True,
            ready=True,
            message="Repository setup, verification, and verification cleanup succeeded.",
            server_url=safe_url,
            repository_id=safe_id,
            shapes_version=sanitized(installed.version),
            content_digest=sanitized(installed.content_digest),
            data_graph_iris=tuple(sanitized(iri) for iri in installed.data_graph_iris),
        )
    except GraphDBError as error:
        # Utility exceptions carry controlled diagnostics. Raw HTTP response
        # bodies and chained transport exceptions are deliberately excluded.
        return failure(str(error))
    except (OSError, ValueError, TypeError):
        return failure("A required input could not be read or processed; check the supplied inputs.")
