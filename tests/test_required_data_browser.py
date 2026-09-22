"""Browser acceptance tests for Required Data Validation."""

import re
import socket
from pathlib import Path
from threading import Thread
from time import monotonic, sleep

import pytest
import uvicorn
from playwright.sync_api import Page, expect

from app.main import app


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = (
    ROOT / "data/uad36-test-suite/tests/fixtures/required_data"
)


@pytest.fixture(scope="module")
def required_data_server_url():
    previous_configuration = app.state.configuration_file
    app.state.configuration_file = (
        ROOT / "config/configuration.developer.ttl"
    )

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
    thread = Thread(
        target=server.run,
        kwargs={"sockets": [server_socket]},
        daemon=True,
    )

    try:
        thread.start()
        deadline = monotonic() + 10
        while not server.started and monotonic() < deadline:
            sleep(0.01)

        if not server.started:
            pytest.fail("The local validation server did not start.")

        yield f"http://{host}:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        server_socket.close()
        app.state.configuration_file = previous_configuration


@pytest.mark.parametrize(
    "relative_file, expected_fatal_count",
    [
        ("baseline/SF1_Appraisal_v1.4.xml", 0),
        (
            "tests/0100.0007-UAD1001-missing-AddressLineText.xml",
            1,
        ),
    ],
    ids=["complete-baseline", "missing-subject-address"],
)
def test_required_data_upload(
    page: Page,
    required_data_server_url: str,
    relative_file: str,
    expected_fatal_count: int,
):
    source = FIXTURES / relative_file
    assert source.is_file(), f"Missing fixture: {source}"

    page.goto(f"{required_data_server_url}/validation/")

    option = page.get_by_role(
        "radio",
        name="Required Data Validation",
        exact=True,
    )
    expect(option).to_be_visible()
    expect(option).to_be_enabled()
    option.check()

    page.locator("#appraisal-file").set_input_files(str(source))

    with page.expect_response(
        lambda response: (
            response.request.method == "POST"
            and "/validate/uad36" in response.url
        )
    ) as pending:
        page.locator("#validate-button").click()

    response = pending.value
    assert response.status == 200, response.text()
    report = response.json()

    assert report["summary"]["fatal"] == expected_fatal_count
    assert report["summary"]["error"] == 0

    results = page.locator("#validation-results-content")
    expect(results).to_be_visible()
    expect(results).to_contain_text("Required Data Validation")

    if expected_fatal_count:
        assert len(report["findings"]) == 1
        finding = report["findings"][0]
        assert finding["rule_id"] == "UAD1001"
        assert finding["row_id"] == "0100.0007"
        assert finding["severity"] == "fatal"

        expect(results).to_contain_text("UAD1001")
        expect(results).to_contain_text("0100.0007")
        expect(results).to_contain_text(
            re.compile(r"\bfatal\b", re.IGNORECASE)
        )
        expect(results).to_contain_text(finding["finding"])
    else:
        assert report["findings"] == []
        expect(results).to_contain_text(
            "No required-data findings"
        )