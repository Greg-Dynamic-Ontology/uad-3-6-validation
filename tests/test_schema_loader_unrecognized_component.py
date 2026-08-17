"""Acceptance test for IT-5R6S2."""

import json
import socket
from pathlib import Path
from threading import Thread
from time import monotonic, sleep
from typing import Iterator

import pytest
import uvicorn
from playwright.sync_api import Page, expect

from app.main import app
from app.services.schema_loader import SchemaLoader
from app.services.schema_loader.processing_coverage import (
    report_component_processing_coverage,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEVELOPER_CONFIGURATION_FILE = (
    PROJECT_ROOT / "config" / "configuration.developer.ttl"
)


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


def test_unrecognized_component_remains_visible_as_np(
    tmp_path: Path,
) -> None:
    """Keep an unhandled XML Schema component in the coverage report."""

    schema_path = tmp_path / "future-component.xsd"
    schema_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:futureComponent />
</xs:schema>
""",
        encoding="utf-8",
    )

    schema = SchemaLoader().load(schema_path)
    report = report_component_processing_coverage(schema)
    rows = {
        row.component_kind: row
        for row in report.component_kinds
    }

    assert set(rows) == {"futureComponent"}
    assert rows["futureComponent"].found == 1
    assert rows["futureComponent"].processed == 0
    assert rows["futureComponent"].status == "NP"


def test_developer_sees_unrecognized_component_as_np(
    page: Page,
    developer_experience_server_url: str,
) -> None:
    """Render an unrecognized report row rather than filtering it out."""

    coverage_url = (
        f"{developer_experience_server_url}"
        "/schema/uad36/component-processing-coverage"
    )
    page.route(
        coverage_url,
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "component_kinds": [
                        {
                            "component_kind": "futureComponent",
                            "found": 1,
                            "processed": 0,
                            "status": "NP",
                        }
                    ]
                }
            ),
        ),
    )

    page.goto(f"{developer_experience_server_url}/validation/")

    row = page.locator(
        "#schema-component-processing-coverage "
        'tbody tr[data-component-kind="futureComponent"]'
    )
    expect(row).to_be_visible()
    expect(row.locator('[data-column="component-kind"]')).to_have_text(
        "futureComponent"
    )
    expect(row.locator('[data-column="found"]')).to_have_text("1")
    expect(row.locator('[data-column="processed"]')).to_have_text("0")
    expect(row.locator('[data-column="status"]')).to_have_text("NP")
