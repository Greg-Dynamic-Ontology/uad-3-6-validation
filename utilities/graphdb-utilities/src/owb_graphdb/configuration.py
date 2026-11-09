"""Caller-supplied configuration for GraphDB repository setup."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RepositoryConfiguration:
    """Describe the repository and SHACL configuration to provision.

    The calling application supplies the Turtle files and identifies
    the shape version and named graphs subject to validation.

    Constructing this object does not read files, contact GraphDB,
    or create a repository. Configuration validation and provisioning
    are separate operations.

    Credentials are supplied separately to the GraphDB client.
    """

    server_url: str
    repository_id: str
    repository_config_path: Path
    shapes_path: Path
    shapes_version: str
    data_graph_iris: tuple[str, ...]