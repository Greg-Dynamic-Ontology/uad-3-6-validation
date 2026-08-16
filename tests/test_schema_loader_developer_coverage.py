"""Browser-interface acceptance test for IT-5R6S1."""

from __future__ import annotations

import socket
from pathlib import Path
from threading import Thread
from time import monotonic, sleep
from typing import Iterator

import pytest
import uvicorn
from playwright.sync_api import Page, expect

from app.main import app
from app.models.schema_model import (
    ComponentProcessingDisposition,
    SchemaModel,
)
from app.services.schema_loader.processing_coverage import (
    report_component_processing_coverage,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEVELOPER_CONFIGURATION_FILE = (
    PROJECT_ROOT / "config" / "configuration.developer.ttl"
)

EXPECTED_FOUND_COUNTS = {
    "annotation": 5260,
    "any": 368,
    "anyAttribute": 1,
    "attribute": 993,
    "attributeGroup": 1144,
    "choice": 4,
    "complexType": 1297,
    "documentation": 5269,
    "element": 2221,
    "enumeration": 1313,
    "extension": 202,
    "fractionDigits": 1,
    "group": 12,
    "import": 3,
    "maxInclusive": 1,
    "maxLength": 5,
    "minInclusive": 3,
    "minLength": 2,
    "pattern": 5,
    "restriction": 222,
    "sequence": 1093,
    "simpleContent": 202,
    "simpleType": 224,
    "union": 2,
}


def test_coverage_identifies_np_and_incomplete_kinds() -> None:
    """Classify zero and partial processing without tying UAD to either."""

    source_document = Path("example.xsd")
    schema = SchemaModel(
        component_counts={
            "notProcessed": 2,
            "partiallyProcessed": 3,
        },
        processing_dispositions=(
            ComponentProcessingDisposition(
                component_kind="partiallyProcessed",
                source_document=source_document,
                source_index=0,
                action="represent",
                governing_decision="TEST",
                processed=True,
            ),
        ),
    )

    report = report_component_processing_coverage(schema)
    rows = {
        row.component_kind: row
        for row in report.component_kinds
    }

    assert rows["notProcessed"].processed == 0
    assert rows["notProcessed"].status == "NP"
    assert rows["partiallyProcessed"].processed == 1
    assert rows["partiallyProcessed"].status == "Incomplete"


@pytest.fixture(scope="module")
def developer_experience_server_url() -> Iterator[str]:
    """Run the app with its Developer experience configuration."""

    configuration_was_set = hasattr(
        app.state,
        "configuration_file",
    )
    previous_configuration = getattr(
        app.state,
        "configuration_file",
        None,
    )
    app.state.configuration_file = DEVELOPER_CONFIGURATION_FILE

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("127.0.0.1", 0))
    host, port = server_socket.getsockname()

    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="error",
            ws="none",
        )
    )
    server_thread = Thread(
        target=server.run,
        kwargs={"sockets": [server_socket]},
        daemon=True,
    )
    server_thread.start()

    deadline = monotonic() + 10
    while not server.started and monotonic() < deadline:
        sleep(0.01)

    if not server.started:
        server.should_exit = True
        server_thread.join(timeout=5)
        server_socket.close()
        pytest.fail("The local validation server did not start")

    try:
        yield f"http://{host}:{port}"
    finally:
        server.should_exit = True
        server_thread.join(timeout=10)
        server_socket.close()
        if configuration_was_set:
            app.state.configuration_file = previous_configuration
        else:
            del app.state.configuration_file


def test_developer_sees_uad_component_processing_coverage(
    page: Page,
    developer_experience_server_url: str,
) -> None:
    """Show found and processed counts for all 24 UAD component kinds."""

    coverage_requests: list[str] = []
    page.on(
        "request",
        lambda request: coverage_requests.append(request.url)
        if request.method == "GET"
        and request.url.endswith(
            "/schema/uad36/component-processing-coverage"
        )
        else None,
    )

    page.goto(f"{developer_experience_server_url}/validation/")

    coverage_section = page.locator(
        "#schema-component-processing-coverage"
    )
    expect(coverage_section).to_be_visible()

    rows = coverage_section.locator("tbody tr")
    expect(rows).to_have_count(len(EXPECTED_FOUND_COUNTS))

    for component_kind, found_count in EXPECTED_FOUND_COUNTS.items():
        row = coverage_section.locator(
            f'tbody tr[data-component-kind="{component_kind}"]'
        )
        expect(row).to_have_count(1)
        expect(row.locator('[data-column="found"]')).to_have_text(
            str(found_count)
        )

        processed_count = int(
            row.locator('[data-column="processed"]').inner_text()
        )
        status = row.locator('[data-column="status"]').inner_text()

        assert 0 <= processed_count <= found_count
        if processed_count == 0:
            assert status == "NP"
        elif processed_count < found_count:
            assert status == "Incomplete"
        else:
            assert status == "Processed"

    assert coverage_requests == [
        f"{developer_experience_server_url}"
        "/schema/uad36/component-processing-coverage"
    ]
