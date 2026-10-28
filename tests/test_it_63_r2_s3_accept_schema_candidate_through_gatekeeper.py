"""IT-63R2S3: record XML Schema candidates through the running HTTP API.

Run against a dedicated development/test server on localhost:4000. This test
stores candidate submissions. It does not use TestClient or start a server.

Proposed candidate contract:
- POST response: candidate_id, ingestion_status='accepted_for_analysis'.
- GET /resources/{candidate_id}: resource_id, iri,
  resource_type='xml_schema_candidate', raw_text, content_sha256,
  ingestion_status='accepted_for_analysis', and provenance.

Candidate acceptance is a syntax/root check, not schema compilation. The
missing dependencies and unresolved type below must not prevent acceptance.
"""

from hashlib import sha256
import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import ProxyHandler, Request, build_opener
from uuid import uuid4
from xml.etree import ElementTree

import pytest


BASE_URL = "http://localhost:4000"
SCHEMA_ROOT = "{http://www.w3.org/2001/XMLSchema}schema"


def _request_json(opener, method: str, path: str, payload=None):
    headers = {"Accept": "application/json"}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    url = BASE_URL + path
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with opener.open(request, timeout=10) as response:
            assert response.geturl() == url, "The API must respond without redirecting."
            assert 200 <= response.status < 300
            assert response.headers.get_content_type() == "application/json"
            encoding = response.headers.get_content_charset() or "utf-8"
            text = response.read().decode(encoding)
    except HTTPError as error:
        status = error.code
        error.close()
        pytest.fail(f"{method} {url} returned HTTP {status}.", pytrace=False)
    except (URLError, OSError) as error:
        pytest.fail(
            f"Cannot reach the running UAD test API at {url}. "
            f"Start the server on port 4000. Details: {error}",
            pytrace=False,
        )
    try:
        result = json.loads(text)
    except ValueError as error:
        pytest.fail(f"{url} returned invalid JSON: {error}", pytrace=False)
    assert isinstance(result, dict), "The API response must be a JSON object."
    return result


@pytest.mark.parametrize(
    "raw_text",
    [
        '<schema xmlns="http://www.w3.org/2001/XMLSchema"/>',
        '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"/>',
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<vocab:schema xmlns:vocab="http://www.w3.org/2001/XMLSchema">\n'
        '  <!-- Preserve spacing and text: café -->\n'
        '</vocab:schema>\n',
        '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">'
        '<xs:import namespace="urn:test:unavailable" '
        'schemaLocation="unavailable-import-it63r2s3.xsd"/>'
        '</xs:schema>',
        '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">'
        '<xs:include schemaLocation="unavailable-include-it63r2s3.xsd"/>'
        '</xs:schema>',
        '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" '
        'xmlns:t="urn:test:unresolved" targetNamespace="urn:test:unresolved">'
        '<xs:element name="Item" type="t:UndefinedType"/>'
        '</xs:schema>',
    ],
    ids=[
        "default-namespace",
        "xs-prefix",
        "alternate-prefix-and-exact-content",
        "import-only-unresolved-dependency",
        "include-only-unresolved-dependency",
        "candidate-with-unresolved-type",
    ],
)
def test_it_63_r2_s3_records_schema_candidate_for_further_analysis(raw_text: str) -> None:
    assert ElementTree.fromstring(raw_text).tag == SCHEMA_ROOT
    token = uuid4().hex
    provenance = {
        "source_document": f"urn:test:it63r2s3:{token}",
        "source_version": "IT-63R2S3 candidate fixture version 1",
        "source_section": "Schema gatekeeper acceptance",
    }
    payload = {
        "schema_name": f"Schema candidate {token}",
        "schema_version": provenance["source_version"],
        "source_document": provenance["source_document"],
        "source_section": provenance["source_section"],
        "raw_text": raw_text,
    }
    opener = build_opener(ProxyHandler({}))
    ingestion = _request_json(opener, "POST", "/ingest/schema", payload)
    candidate_id = ingestion.get("candidate_id")
    assert isinstance(candidate_id, str) and candidate_id.strip(), (
        "IT-63R2S3 requires the response to identify a recorded schema "
        "candidate. Placeholder schema components do not satisfy candidate acceptance."
    )
    assert ingestion.get("ingestion_status") == "accepted_for_analysis", (
        "Acceptance must distinguish a candidate from a validated or fully analyzed schema."
    )
    candidate = _request_json(
        opener, "GET", "/resources/" + quote(candidate_id, safe=""),
    )
    assert candidate.get("resource_id") == candidate_id
    assert isinstance(candidate.get("iri"), str) and candidate["iri"]
    assert candidate.get("resource_type") == "xml_schema_candidate"
    assert candidate.get("ingestion_status") == "accepted_for_analysis"
    assert candidate.get("raw_text") == raw_text, (
        "The recorded candidate must preserve the exact submitted content, "
        "including whitespace, namespace prefixes, and Unicode characters."
    )
    assert candidate.get("content_sha256") == sha256(raw_text.encode("utf-8")).hexdigest()
    for result in (ingestion, candidate):
        recorded = result.get("provenance")
        assert isinstance(recorded, dict)
        for field, expected in provenance.items():
            assert recorded.get(field) == expected, f"Candidate provenance mismatch: {field}."
        assert result.get("schema_validated") is not True
        assert result.get("component_analysis_complete") is not True
