"""Browser-interface acceptance test for IT-4R3S1."""

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
USER_CONFIGURATION_FILE = (
    PROJECT_ROOT / "config" / "configuration.user.ttl"
)

TECHNICAL_TERMS = (
    "RDF",
    "XML Schema",
    "SHACL",
    "Pipeline Artifacts",
    "Triples",
)


@pytest.fixture(scope="module")
def user_experience_server_url() -> Iterator[str]:
    """Run the application with its User experience configuration."""
    configuration_was_set = hasattr(
        app.state,
        "configuration_file",
    )
    previous_configuration = getattr(
        app.state,
        "configuration_file",
        None,
    )
    app.state.configuration_file = USER_CONFIGURATION_FILE

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


def assert_technical_details_are_not_visible(page: Page) -> None:
    visible_page_text = page.locator("body").inner_text()

    for technical_term in TECHNICAL_TERMS:
        assert technical_term not in visible_page_text


def test_user_experience_hides_rdf_implementation_details(
    page: Page,
    user_experience_server_url: str,
) -> None:
    """The configured pipeline runs without exposing its RDF stage."""
    pipeline_requests: list[str] = []

    page.on(
        "request",
        lambda request: pipeline_requests.append(request.url)
        if request.method == "POST"
        and request.url.endswith("/validate/uad36/pipeline")
        else None,
    )

    page.goto(f"{user_experience_server_url}/validation/")

    assert_technical_details_are_not_visible(page)
    expect(
        page.get_by_role("button", name="Validate Appraisal")
    ).to_be_visible()

    page.locator("#appraisal-file").set_input_files(
        {
            "name": "appraisal.xml",
            "mimeType": "application/xml",
            "buffer": (
                b'<MESSAGE xmlns="https://example.com/uad#" />'
            ),
        }
    )

    page.evaluate(
        """() => {
            const heading = document.getElementById(
                "validation-status-heading"
            );
            window.__observedValidationStatuses = [heading.textContent];
            new MutationObserver(() => {
                window.__observedValidationStatuses.push(
                    heading.textContent
                );
            }).observe(heading, {
                childList: true,
                subtree: true,
                characterData: true,
            });
        }"""
    )

    page.get_by_role("button", name="Validate Appraisal").click()

    expect(page.locator("#validation-status-heading")).to_contain_text(
        "Validation completed"
    )

    observed_statuses = page.evaluate(
        "window.__observedValidationStatuses"
    )
    assert any(
        "Validation in progress" in status
        for status in observed_statuses
    )

    assert pipeline_requests == [
        f"{user_experience_server_url}/validate/uad36/pipeline"
    ]
    assert_technical_details_are_not_visible(page)
