"""IT-63R1S3: ingest a published schema through the real local API.

Requires a dedicated UAD development/test server on localhost:4000. This test
posts schema knowledge into that server's store; it does not start a server,
mock ingestion, or use an in-process application client.
"""

import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import ProxyHandler, Request, build_opener
from xml.etree import ElementTree

import pytest


BASE_URL = "http://localhost:4000"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_RELATIVE_PATH = Path(
    "chatgpt-sources/sources/schemas/UAD/GSE_UAD_3.6.0_v1.3/Combined/"
    "GSE_UAD_3.6.0_v1.3.xsd"
)


def _request_json(opener, method: str, path: str, payload=None):
    headers = {"Accept": "application/json"}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")
    url = BASE_URL + path
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with opener.open(request, timeout=30) as response:
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
            f"Cannot reach the UAD API: {method} {url}. "
            f"Start the test server on port 4000. Details: {error}",
            pytrace=False,
        )
    try:
        return json.loads(text)
    except ValueError as error:
        pytest.fail(f"{method} {url} returned invalid JSON: {error}", pytrace=False)


def test_it_63_r1_s3_ingests_and_retrieves_actual_uad_schema_resource() -> None:
    schema_path = PROJECT_ROOT / SCHEMA_RELATIVE_PATH
    assert schema_path.is_file(), f"Required published UAD schema is missing: {schema_path}"
    raw_text = schema_path.read_text(encoding="utf-8-sig")
    schema = ElementTree.fromstring(raw_text)
    xsd = "{http://www.w3.org/2001/XMLSchema}"
    assert schema.tag == xsd + "schema"
    declarations = {
        element.attrib["name"]
        for element in schema.findall(xsd + "element")
        if "name" in element.attrib
    }
    assert "MESSAGE" in declarations, "The published artifact must declare its MESSAGE root."

    provenance = {
        "source_document": SCHEMA_RELATIVE_PATH.as_posix(),
        "source_version": "GSE 3.6.0 Build v1.3",
        "source_section": "Combined UAD XML Schema",
    }
    payload = {
        "schema_name": "Published GSE UAD 3.6 combined schema",
        "schema_version": provenance["source_version"],
        "source_document": provenance["source_document"],
        "source_section": provenance["source_section"],
        "raw_text": raw_text,
    }
    opener = build_opener(ProxyHandler({}))
    ingestion = _request_json(opener, "POST", "/ingest/schema", payload)
    assert isinstance(ingestion, dict)
    resources = ingestion.get("resources_created")
    assert isinstance(resources, list) and resources, (
        "Successful schema ingestion must identify created resources."
    )
    matches = [
        resource for resource in resources
        if isinstance(resource, dict)
        and resource.get("resource_type") == "schema_element"
        and resource.get("label") == "MESSAGE"
    ]
    assert len(matches) == 1, (
        "IT-63R1S3 requires a resource representing the submitted schema's "
        "actual MESSAGE declaration. A successful POST returning only "
        "placeholder resources does not demonstrate schema ingestion."
    )
    created = matches[0]
    assert isinstance(created.get("resource_id"), str) and created["resource_id"]
    assert isinstance(created.get("iri"), str) and created["iri"]
    saved = _request_json(
        opener, "GET", "/resources/" + quote(created["resource_id"], safe=""),
    )
    assert isinstance(saved, dict)
    for field in ("resource_id", "iri", "resource_type", "label"):
        assert saved.get(field) == created[field], f"Retrieval changed {field}."
    for result in (ingestion, created, saved):
        recorded = result.get("provenance")
        assert isinstance(recorded, dict), "Source provenance must be retained."
        for field, expected in provenance.items():
            assert recorded.get(field) == expected, f"Source provenance mismatch: {field}."
