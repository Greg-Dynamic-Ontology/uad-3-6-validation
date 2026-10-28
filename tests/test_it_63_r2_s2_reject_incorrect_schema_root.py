"""IT-63R2S2: reject well-formed XML whose root is not an XSD schema.

Requires a dedicated test server on localhost:4000. A defective handler may
accept these requests and write resources to its store. Requests use real HTTP.
"""

import json
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener
from uuid import uuid4
from xml.etree import ElementTree

import pytest


INGEST_URL = "http://localhost:4000/ingest/schema"
EXPECTED_ROOT = "{http://www.w3.org/2001/XMLSchema}schema"


@pytest.mark.parametrize(
    "root_name, namespace",
    [
        ("document", "http://www.w3.org/2001/XMLSchema"),
        ("Schema", "http://www.w3.org/2001/XMLSchema"),
        ("schema", "urn:example:other"),
        ("schema", ""),
    ],
    ids=["wrong-local-name", "case-sensitive-local-name", "wrong-namespace", "absent-namespace"],
)
def test_it_63_r2_s2_rejects_incorrect_schema_root_through_running_api(
    root_name: str, namespace: str,
) -> None:
    actual_root = f"{{{namespace}}}{root_name}" if namespace else root_name
    # Construct known well-formed XML so rejection concerns root identity.
    raw_text = ElementTree.tostring(ElementTree.Element(actual_root), encoding="unicode")
    assert ElementTree.fromstring(raw_text).tag == actual_root
    token = uuid4().hex
    payload = {
        "schema_name": f"Incorrect schema root case {token}",
        "schema_version": "IT-63R2S2 fixture version 1",
        "source_document": f"urn:test:it63r2s2:{token}",
        "source_section": "Incorrect schema root rejection fixture",
        "raw_text": raw_text,
    }
    request = Request(
        INGEST_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    opener = build_opener(ProxyHandler({}))
    try:
        response = opener.open(request, timeout=10)
    except HTTPError as error:
        response = error
    except (URLError, OSError) as error:
        pytest.fail(
            f"Cannot reach the test API at {INGEST_URL}. "
            f"Start the server on port 4000. Details: {error}",
            pytrace=False,
        )

    with response:
        status = response.code
        response_url = response.geturl()
        content_type = response.headers.get_content_type()
        encoding = response.headers.get_content_charset() or "utf-8"
        body = response.read().decode(encoding)

    assert response_url == INGEST_URL, "The gatekeeper must respond without redirecting."
    assert status == 400, (
        "IT-63R2S2 requires rejection of an incorrect XML Schema root "
        f"with HTTP 400. Submitted {actual_root!r}; received HTTP {status}."
    )
    assert content_type == "application/json", "Rejection must provide a JSON diagnostic."
    try:
        rejection = json.loads(body)
    except ValueError as error:
        pytest.fail(f"Invalid JSON rejection response: {error}", pytrace=False)
    assert isinstance(rejection, dict)
    diagnostic = rejection.get("detail")
    assert diagnostic, "The response must explain the incorrect schema root."

    # The diagnostic contract uses explicit fields to distinguish a missing
    # namespace from the expected namespace mentioned in the same message.
    assert isinstance(diagnostic, dict), (
        "Return structured detail with expected_root, actual_root_name, "
        "and actual_root_namespace so each root identity is unambiguous."
    )
    assert diagnostic.get("expected_root") == EXPECTED_ROOT
    assert diagnostic.get("actual_root_name") == root_name
    assert diagnostic.get("actual_root_namespace") == namespace, (
        "Report an absent namespace explicitly as an empty string."
    )

    # These check the visible rejection response. Proving that no internal
    # writes or analysis occurred also requires service-level checks or audit access.
    assert rejection.get("resources_created") in (None, [])
    assert rejection.get("schema_resource_id") is None
    assert rejection.get("candidate_id") is None
    assert rejection.get("accepted") is not True
    assert rejection.get("analysis_started") is not True
