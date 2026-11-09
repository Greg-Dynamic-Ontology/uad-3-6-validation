"""Coordinate repository creation and SHACL shape-set installation."""

from owb_graphdb.client import GraphDBClient
from owb_graphdb.configuration import RepositoryConfiguration
from owb_graphdb.errors import GraphDBError
from owb_graphdb.provisioning import (
    RepositorySetupResult,
    provision_repository,
)
from owb_graphdb.shapes import install_shape_set


def setup_repository(
    *,
    client: GraphDBClient,
    configuration: RepositoryConfiguration,
) -> RepositorySetupResult:
    """Create and configure a repository without deleting it on failure."""
    provisioning_result = provision_repository(
        client=client,
        configuration=configuration,
    )

    if provisioning_result is not None:
        return provisioning_result

    # Provisioning returns None only after creation and configuration
    # verification have succeeded.
    repository_id = configuration.repository_id

    try:
        install_shape_set(
            client=client,
            configuration=configuration,
        )
    except GraphDBError:
        return RepositorySetupResult(
            success=False,
            ready=False,
            message=(
                f"Repository '{repository_id}' was created but is not ready. "
                "Setup failed at the shape-set installation step. "
                "The repository has been preserved for inspection."
            ),
        )

    return RepositorySetupResult(
        success=True,
        ready=True,
        message=(
            f"Repository '{repository_id}' was created, "
            "and the supplied shape set was installed and verified. "
            "Repository setup is complete."
        ),
    )