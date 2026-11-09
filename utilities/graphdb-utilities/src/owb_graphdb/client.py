"""HTTP communication for GraphDB utilities."""

from collections.abc import Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from owb_graphdb.errors import (
    GraphDBConfigurationError,
    GraphDBConnectionError,
    GraphDBHTTPError,
)


class GraphDBClient:
    """Communicate with a caller-specified GraphDB server.

    Credentials and response bodies are excluded from error messages.
    """

    def __init__(
        self,
        *,
        server_url: str,
        headers: Mapping[str, str] | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        parsed = urlsplit(server_url)

        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise GraphDBConfigurationError(
                "The GraphDB server URL must be an HTTP or HTTPS URL."
            )

        if parsed.username or parsed.password:
            raise GraphDBConfigurationError(
                "Supply GraphDB credentials through authentication headers."
            )

        if parsed.query or parsed.fragment:
            raise GraphDBConfigurationError(
                "The GraphDB server URL must not contain a query or fragment."
            )

        if timeout_seconds <= 0:
            raise GraphDBConfigurationError(
                "The request timeout must be greater than zero."
            )

        self._server_url = server_url.rstrip("/")
        self._headers = dict(headers or {})
        self._timeout_seconds = timeout_seconds

    def request(
        self,
        *,
        method: str,
        path: str,
        body: bytes | None = None,
        content_type: str | None = None,
        accept: str | None = None,
    ) -> bytes:
        """Send a request and return the response body.

        Paths are relative to the configured GraphDB server URL.
        HTTP failures retain their status code so callers can
        distinguish conditions such as a missing repository.
        """
        parsed_path = urlsplit(path)

        if (
            parsed_path.scheme
            or parsed_path.netloc
            or parsed_path.fragment
            or path.startswith("//")
        ):
            raise GraphDBConfigurationError(
                "The request path must be relative to the GraphDB server."
            )

        url = f"{self._server_url}/{path.lstrip('/')}"
        headers = dict(self._headers)

        request = Request(
            url=url,
            data=body,
            headers=headers,
            method=method.upper(),
        )

        if content_type is not None:
            request.add_header("Content-Type", content_type)

        if accept is not None:
            request.add_header("Accept", accept)

        try:
            with urlopen(
                request,
                timeout=self._timeout_seconds,
            ) as response:
                return response.read()

        except HTTPError as error:
            status_code = error.code
            response_content_type = (
                error.headers.get("Content-Type", "")
                if error.headers is not None else ""
            )
            try:
                response_body = error.read()
            except OSError:
                # Preserve the HTTP failure if its diagnostic body cannot be
                # retrieved. Missing evidence must not count as SHACL rejection.
                response_body = b""
            finally:
                error.close()
            raise GraphDBHTTPError(
                f"GraphDB returned HTTP status {status_code}.",
                status_code=status_code,
                response_body=response_body,
                content_type=response_content_type,
            ) from None

        except (URLError, TimeoutError, ConnectionError):
            raise GraphDBConnectionError(
                "The GraphDB request could not complete. "
                "Check server availability, connectivity, and timeout."
            ) from None
