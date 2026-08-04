"""Browser acceptance test for single-selection RDF Projection."""

from __future__ import annotations

import re
import socket
from threading import Thread
from time import monotonic, sleep
from typing import Iterator

import pytest
import uvicorn
from playwright.sync_api import Page, expect

from app.main import app


@pytest.fixture(scope="module")
def validation_server_url() -> Iterator[str]:
    """Run the FastAPI application on an available local port."""
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


def test_rdf_projection_does_not_request_appraisal_again(
    page: Page,
    validation_server_url: str,
) -> None:
    """Feature: IT-4R1S2.

    The user selects one appraisal, runs RDF Projection, and reaches a
    completed state without another file-selection interaction.
    """
    file_chooser_events: list[object] = []
    pipeline_requests: list[str] = []

    page.on(
        "filechooser",
        lambda file_chooser: file_chooser_events.append(file_chooser),
    )
    page.on(
        "request",
        lambda request: pipeline_requests.append(request.url)
        if request.method == "POST"
        and request.url.endswith("/validate/uad36/pipeline")
        else None,
    )

    page.goto(f"{validation_server_url}/validation/")

    file_input = page.locator("#appraisal-file")
    file_input.set_input_files(
        {
            "name": "appraisal.xml",
            "mimeType": "application/xml",
            "buffer": b"""<?xml version="1.0" encoding="UTF-8"?>
<uad:MESSAGE xmlns:uad="https://example.com/uad#" />
""",
        }
    )

    rdf_projection = page.locator(
        'input[name="pipeline"][value="rdf-projection"]'
    )
    expect(rdf_projection).to_be_enabled()
    rdf_projection.check()

    page.get_by_role("button", name="Validate").click()

    expect(page.locator("#validation-status-heading")).to_contain_text(
        "RDF Projection completed"
    )
    expect(file_input).to_have_value(re.compile(r"appraisal\.xml$"))

    assert pipeline_requests == [
        f"{validation_server_url}/validate/uad36/pipeline"
    ]
    assert file_chooser_events == []
