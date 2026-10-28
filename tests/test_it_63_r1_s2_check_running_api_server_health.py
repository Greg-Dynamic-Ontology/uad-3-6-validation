"""IT-63R1S2: check the running UAD server through a real HTTP connection.

The server must already be listening on localhost:4000. This test neither
starts a server nor substitutes an in-process application transport.
"""

import json
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

import pytest


HEALTH_URL = "http://localhost:4000/health"


def test_it_63_r1_s2_checks_health_through_running_api_server() -> None:
    # Bypass environment proxies so this request connects to the local server.
    opener = build_opener(ProxyHandler({}))
    request = Request(HEALTH_URL, headers={"Accept": "application/json"}, method="GET")

    try:
        with opener.open(request, timeout=5) as response:
            status = response.status
            response_url = response.geturl()
            content_type = response.headers.get_content_type()
            encoding = response.headers.get_content_charset() or "utf-8"
            body = response.read()
    except HTTPError as error:
        status = error.code
        error.close()
        pytest.fail(
            f"IT-63R1S2 requires HTTP 200 from {HEALTH_URL}; "
            f"the running server returned HTTP {status}.",
            pytrace=False,
        )
    except (URLError, OSError) as error:
        pytest.fail(
            f"IT-63R1S2 could not reach the running UAD API at {HEALTH_URL}. "
            f"Start the UAD API server on port 4000 and retry. Details: {error}",
            pytrace=False,
        )

    assert response_url == HEALTH_URL, (
        "The health endpoint must respond directly without redirecting "
        f"the request to {response_url}."
    )
    assert status == 200, f"Expected HTTP 200; received HTTP {status}."
    assert content_type == "application/json", (
        f"The health response must be JSON; received {content_type!r}."
    )
    try:
        payload = json.loads(body.decode(encoding))
    except (ValueError, LookupError) as error:
        pytest.fail(f"The health response contains invalid JSON: {error}", pytrace=False)

    assert isinstance(payload, dict), "The health response must be a JSON object."
    assert payload.get("status") == "ok", (
        "The running API must identify its health state as status='ok'; "
        f"received {payload!r}."
    )
