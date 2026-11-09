"""Public exceptions raised by GraphDB utilities."""


class GraphDBError(Exception):
    """Base exception for GraphDB utility failures.

    Messages must not contain credentials or authentication headers.
    """


class GraphDBConfigurationError(GraphDBError):
    """Caller-supplied configuration is missing, invalid, or inconsistent."""


class GraphDBConnectionError(GraphDBError):
    """The GraphDB server cannot be reached or a request times out."""


class GraphDBHTTPError(GraphDBError):
    """GraphDB returned an unsuccessful HTTP response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        response_body: bytes = b"",
        content_type: str = "",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        # Retain server evidence for programmatic classification only.
        # Do not include response content in exception messages or logs:
        # validation reports can contain caller-supplied RDF data.
        self.response_body = response_body
        self.content_type = content_type


class RepositoryConfigurationMismatchError(GraphDBError):
    """An existing repository does not meet the supplied requirements."""


class SHACLValidationError(GraphDBError):
    """RDF data failed SHACL validation."""


class RepositoryVerificationError(GraphDBError):
    """Repository verification could not confirm the required behavior."""
