"""IT-63R2S1: the live ingestion gatekeeper rejects malformed XML.

Run against a dedicated development/test server on localhost:4000. A broken
handler may accept these submissions and write to its store. This test uses
real HTTP, without starting a server or substituting application functions.
"""

import json
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener
from uuid import uuid4

import pytest


INGEST_URL = "http://localhost:4000/ingest/schema"


@pytest.mark.parametrize(
    "raw_text",
    [
        '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">',
        '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">'
        '<xs:element name="Item"></xs:schema>',
        '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"/>'
        '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"/>',
    ],
    ids=["unclosed-root", "mismatched-tags", "multiple-document-elements"],
)
def test_it_63_r2_s1_rejects_malformed_xml_through_running_api(raw_text: str) -> None:
    token = uuid4().hex
    payload = {
        "schema_name": f"Malformed XML gatekeeper case {token}",
        "schema_version": "IT-63R2S1 fixture version 1",
        "source_document": f"urn:test:it63r2s1:{token}",
        "source_section": "Malformed XML rejection fixture",
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
        # HTTP 400 is an expected response to inspect, not a transport failure.
        response = error
    except (URLError, OSError) as error:
        pytest.fail(
            f"Cannot reach the running UAD API at {INGEST_URL}. "
            f"Start the test server on port 4000. Details: {error}",
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
        "IT-63R2S1 requires the gatekeeper to reject malformed schema XML "
        f"with HTTP 400; received HTTP {status}. A successful ingestion "
        "response means malformed XML was incorrectly accepted."
    )
    assert content_type == "application/json", "Rejection must provide a JSON diagnostic."
    try:
        rejection = json.loads(body)
    except ValueError as error:
        pytest.fail(f"The rejection response is not valid JSON: {error}", pytrace=False)
    assert isinstance(rejection, dict)
    diagnostic = rejection.get("detail")
    assert diagnostic, "The rejection response must explain why the XML was rejected."
    text = json.dumps(diagnostic, ensure_ascii=False).casefold()
    assert "xml" in text and any(
        phrase in text
        for phrase in ("malformed", "not well-formed", "not well formed")
    ), f"The diagnostic must identify malformed XML as the reason: {diagnostic!r}"

    # Observable rejection contract: no accepted candidate or created resources
    # are returned. Internal non-persistence and worker calls require separate
    # service-level tests or a candidate/audit inspection API.
    assert rejection.get("resources_created") in (None, [])
    assert rejection.get("schema_resource_id") is None
    assert rejection.get("candidate_id") is None
    assert rejection.get("accepted") is not True
    assert rejection.get("analysis_started") is not True
