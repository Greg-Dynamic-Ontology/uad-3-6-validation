"""Browser-interface acceptance test for IT-4R3S2."""

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


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEVELOPER_CONFIGURATION_FILE = (
    PROJECT_ROOT / "config" / "configuration.developer.ttl"
)


@pytest.fixture(scope="module")
def developer_experience_server_url() -> Iterator[str]:
    """Run the application with its Developer experience configuration."""
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


def test_developer_experience_shows_rdf_projection_status(
    page: Page,
    developer_experience_server_url: str,
) -> None:
    """The Developer experience exposes projection status and artifacts."""
    pipeline_requests: list[str] = []

    page.on(
        "request",
        lambda request: pipeline_requests.append(request.url)
        if request.method == "POST"
        and request.url.endswith("/validate/uad36/pipeline")
        else None,
    )

    page.goto(f"{developer_experience_server_url}/validation/developer/")

    pipeline_selection = page.locator("#technical-pipeline-selection")
    technical_artifacts = page.locator("#technical-artifacts-section")
    expect(pipeline_selection).to_be_visible()
    expect(technical_artifacts).to_be_visible()

    page.locator("#appraisal-file").set_input_files(
        {
            "name": "appraisal.xml",
            "mimeType": "application/xml",
            "buffer": (
                b'<MESSAGE xmlns="https://example.com/uad#" />'
            ),
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
    expect(page.locator("#validation-results-content")).to_contain_text(
        "RDF Projection"
    )
    expect(page.locator("#validation-results-content")).to_contain_text(
        "RDF instance graph"
    )
    expect(page.locator("#validation-results-content")).to_contain_text(
        "Triples"
    )
    expect(page.locator("#validation-results-content")).to_contain_text(
        "1"
    )
    expect(page.locator("#artifact-rdf-status")).to_contain_text(
        "Generated"
    )

    assert pipeline_requests == [
        f"{developer_experience_server_url}/validate/uad36/pipeline"
    ]


def test_it_4_r3_s2_developer_entry_preserves_demo_and_respects_profile(
    page: Page, developer_experience_server_url: str, monkeypatch,
) -> None:
    """Developer configuration must not turn the default Demo page technical."""
    page.goto(f"{developer_experience_server_url}/validation/")
    expect(page.locator("#technical-pipeline-selection")).to_be_hidden()
    expect(page.locator("#technical-artifacts-section")).to_be_hidden()
    expect(page.locator(".demo-mode-indicator")).to_have_text("Demo Mode")
    page.goto(f"{developer_experience_server_url}/validation/developer/")
    expect(page.locator("#technical-pipeline-selection")).to_be_visible()
    expect(page.locator(".demo-mode-indicator")).to_have_text("Developer experience")
    with monkeypatch.context() as policy:
        policy.setattr(app.state, "configuration_file", PROJECT_ROOT / "config/configuration.user.ttl")
        response = page.goto(f"{developer_experience_server_url}/validation/developer/")
        assert response is not None and response.status == 403
        expect(page.locator("#technical-pipeline-selection")).to_have_count(0)
