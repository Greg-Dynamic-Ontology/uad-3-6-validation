"""GDB-1R5S2: Application invocation is noninteractive and returns safe data.

Exercise an unreachable-server outcome at the HTTP boundary. No real server
is contacted. Verification inputs are supplied even though provisioning fails.
"""

import inspect
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from urllib.error import URLError

import pytest
from rdflib import Graph

import owb_graphdb

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
SERVER_URL = "http://127.0.0.1:7200"
REPOSITORY_ID = "owb-graphdb-test"
VERIFICATION_GRAPH = "urn:owb:graphdb:test:verification"


def test_gdb_1_r5_s2_invoke_setup_without_interactive_prompts(monkeypatch, capsys, caplog):
    # All values are synthetic; no real credentials are read or printed.
    token = "gdb-r5-s2-synthetic-token-8342"
    password = "gdb-r5-s2-synthetic-password-9421"
    headers = {"Authorization": f"Bearer {token}", "X-Test-Password": password}
    conforming = Graph().parse(FIXTURES / "conforming-data.ttl", format="turtle")
    nonconforming = Graph().parse(FIXTURES / "nonconforming-data.ttl", format="turtle")
    requests = []

    def forbid_prompt(*args, **kwargs):
        pytest.fail("Application setup must not request interactive input.")

    def refuse_connection(request, *args, **kwargs):
        requests.append((request.get_method(), request.full_url))
        # Deliberately unsafe upstream detail: the public result must not echo it.
        raise URLError(f"Connection refused; Authorization: Bearer {token}; password={password}")

    monkeypatch.setattr("builtins.input", forbid_prompt)
    monkeypatch.setattr("getpass.getpass", forbid_prompt)
    monkeypatch.setattr("owb_graphdb.client.urlopen", refuse_connection)

    inputs = dict(
        server_url=SERVER_URL,
        repository_id=REPOSITORY_ID,
        repository_config_path=FIXTURES / "repository-config.ttl",
        shapes_path=FIXTURES / "shapes.ttl",
        shapes_version="1.0.0",
        data_graph_iris=(VERIFICATION_GRAPH,),
        headers=headers,
        conforming_dataset=conforming,
        nonconforming_dataset=nonconforming,
        verification_graph_iri=VERIFICATION_GRAPH,
    )

    # Establish the application input contract with an intentional assertion,
    # rather than allowing an unexpected-keyword TypeError during invocation.
    parameters = inspect.signature(owb_graphdb.setup_repository).parameters
    accepts_keywords = any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    )
    missing = sorted(set(inputs) - set(parameters)) if not accepts_keywords else []
    assert not missing, (
        "GDB-1R5S2 requires the application entry point to accept all setup "
        f"and verification inputs; missing parameters: {', '.join(missing)}"
    )

    result = owb_graphdb.setup_repository(**inputs)
    assert requests == [("GET", f"{SERVER_URL}/rest/repositories")], (
        "The simulated connection failure must stop setup before any writes."
    )
    assert result is not None, "Application setup must return a machine-readable result."
    if is_dataclass(result) and not isinstance(result, type):
        fields = asdict(result)
    else:
        assert isinstance(result, dict), "Return a dataclass or a dictionary of result fields."
        fields = result
    try:
        encoded = json.dumps(fields, allow_nan=False)
        decoded = json.loads(encoded)
    except (TypeError, ValueError):
        pytest.fail("Result fields must serialize as JSON without custom conversion.")

    # Check redaction before assertions that could expose diagnostic contents.
    captured = capsys.readouterr()
    surfaced = encoded + repr(result) + captured.out + captured.err + caplog.text
    assert all(secret not in surfaced for secret in (token, password)), (
        "Result or diagnostic output exposed a supplied authentication secret."
    )
    assert not ({"headers", "authorization", "credentials", "password", "token"}
                & {str(key).lower() for key in fields}), (
        "Public result fields must not expose authentication material."
    )

    assert decoded.get("success") is False, "Connection failure must report success=False."
    assert decoded.get("ready") is False, "Failed setup must not report repository readiness."
    assert decoded.get("failed_step") == "provisioning", (
        "The failure result must identify provisioning as the failed step."
    )
    diagnostics = decoded.get("diagnostics")
    assert isinstance(diagnostics, (str, list, dict)) and diagnostics, (
        "The failure result must include available, sanitized diagnostic details."
    )
    detail = json.dumps(diagnostics).lower()
    assert "connect" in detail and SERVER_URL in detail, (
        "Diagnostics must identify the connection problem and configured server."
    )
