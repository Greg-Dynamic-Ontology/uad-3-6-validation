"""Browser-interface acceptance test for IT-5R6S3."""

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
COVERAGE_PATH = "/schema/uad36/component-processing-coverage"


@pytest.fixture(scope="module")
def user_experience_server_url() -> Iterator[str]:
    """Run the app with its User experience configuration."""

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


def test_user_experience_hides_schema_implementation_details(
    page: Page,
    user_experience_server_url: str,
) -> None:
    """Do not request, display, or expose developer schema diagnostics."""

    coverage_requests: list[str] = []
    page.on(
        "request",
        lambda request: coverage_requests.append(request.url)
        if request.url.endswith(COVERAGE_PATH)
        else None,
    )

    page.goto(f"{user_experience_server_url}/validation/")
    page.wait_for_load_state("networkidle")

    coverage_section = page.locator(
        "#schema-component-processing-coverage"
    )
    expect(coverage_section).to_be_hidden()
    assert coverage_requests == []
    assert "XML Schema Component-Processing Coverage" not in (
        page.locator("body").inner_text()
    )

    response = page.request.get(
        f"{user_experience_server_url}{COVERAGE_PATH}"
    )
    assert response.status == 404
