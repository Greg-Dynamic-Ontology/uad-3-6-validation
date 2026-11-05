"""IT-64R2S2: real API validation closes a new cycle on its first pass.

Run against the WorkOS-configured server with --headed -s. No authentication,
engine, lifecycle, or storage response is mocked. Uses a dedicated test account;
creates one real cycle and may consume a credit under the configured policy.

Current expected RED: POST /validation-cycles is absent from the running API.
After that API exists, a reviewed passing-case manifest is a prerequisite.
Set UAD_IT64_PASSING_CASE to its JSON filename. Manifest paths are relative to
the manifest directory (absolute paths are also accepted). Required structure:
{
  "report_path": "known-passing.xml",
  "report_sha256": "<independently recorded SHA-256 of the report bytes>",
  "schema": {"version": "<version>", "sha256": "<schema SHA-256>",
             "source_document": "<governed schema source>"},
  "constraint_sets": [
    {"constraint_set_id": "<id>", "version": "<version>",
     "source_document": "<source>", "source_sha256": "<source SHA-256>"}
  ]
}
Do not treat an arbitrary published sample or empty XML as a passing fixture.

Reuses the R2S1 proposed JSON request/detail contract and IT-25's existing
'passed-and-closed' state. Browser retrieval uses /validation/ with account and
validation_cycle_id query parameters. This is a proposed integration contract.
The production run is checked through its independent retrieval endpoint; an
HTTP test cannot alone prove internal worker invocation or transaction ordering.
"""

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import urlencode, urlsplit
from uuid import uuid4

from tests.it64_live_auth import visible_sign_in_required, session_state, sign_in, wait_for_verified_account, cycle_baseline

from playwright.sync_api import Browser, expect


ROOT = Path(__file__).resolve().parents[1]


def _identity(record, key):
    value = record.get(key)
    assert isinstance(value, str) and value.strip(), f"Missing identity: {key}"
    return value


def _time(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None, "Recorded time needs a timezone."
    return parsed


def _coverage(result):
    schema = result["schema"]
    schema_signature = tuple(schema[key] for key in ("version", "sha256", "source_document"))
    sets = result["constraint_sets"]
    assert isinstance(sets, list) and sets, "Passing must identify nonempty governed coverage."
    keys = ("constraint_set_id", "version", "source_document", "source_sha256")
    signatures = [tuple(_identity(item, key) for key in keys) for item in sets]
    assert len(signatures) == len(set(signatures)), "Coverage contains duplicate entries."
    return schema_signature, sorted(signatures)


def test_it_64_r2_s2_closes_new_cycle_on_first_passing_result(
    browser: Browser, pytestconfig,
) -> None:
    visible_sign_in_required(pytestconfig)
    base = os.environ.get("UAD_IT64_BASE_URL", "http://localhost:4000").rstrip("/")
    origin = urlsplit(base)
    context = browser.new_context(storage_state={"cookies": [], "origins": []})
    report_path = None
    original = None
    try:
        # Diagnose the known missing integration before interactive sign-in or
        # fixture selection. Passing this gate alone does not satisfy the test.
        specification = context.request.get(base + "/openapi.json")
        assert specification.status == 200, "Setup: keep the UAD server running."
        operation = specification.json().get("paths", {}).get("/validation-cycles", {}).get("post")
        assert operation is not None, (
            "IT-64R2S2 requires the running API's POST /validation-cycles to "
            "accept a report, execute production validation, and persist a first "
            "passing result as passed-and-closed. That operation is missing."
        )

        manifest_path = Path(os.environ.get(
            "UAD_IT64_PASSING_CASE", str(ROOT / "tests/fixtures/it_64/r2/s2/passing-case.json")
        )).expanduser().resolve()
        assert manifest_path.is_file(), (
            f"Setup: supply a reviewed passing report and coverage manifest: {manifest_path}. "
            "See this test's docstring; do not invent a passing fixture."
        )
        case = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        report_path = (manifest_path.parent / case["report_path"]).resolve()
        original = report_path.read_bytes()
        digest = sha256(original).hexdigest()
        assert digest == case["report_sha256"], "Controlled report changed from its reviewed digest."
        expected_coverage = _coverage(case)
        profile_path = Path(os.environ.get(
            "UAD_IT64_CUSTOMER_PROFILE", str(ROOT / "tests/fixtures/it_64/r1/s1/customer-profile.json")
        )).expanduser()
        profile = json.loads(profile_path.read_text(encoding="utf-8-sig"))
        account_id = _identity(profile, "customer_account_id")
        account_query = urlencode({"customer_account_id": account_id})
        page = context.new_page()
        context.add_cookies(session_state(profile, base)["cookies"])
        sign_in(page, profile, base)
        authenticated = context.request.get(base + "/account/context")
        assert authenticated.status == 200, "Setup: real sign-in must return a linked account identity."
        identity = authenticated.json()
        assert identity["user_account_id"] == profile["user_account_id"]
        assert any(a["customer_account_id"] == account_id and a["can_validate"] for a in identity["accounts"])
        inventory = context.request.get(base + "/validation-cycles?" + account_query)
        assert inventory.status == 200
        before_ids = {c["validation_cycle_id"] for c in inventory.json()["cycles"]}
        started = datetime.now(timezone.utc)
        created = context.request.post(
            base + "/validation-cycles?" + account_query,
            data={"customer_account_id": account_id, "package_name": report_path.name,
                  "xml_text": original.decode("utf-8-sig")},
            headers={"Idempotency-Key": "IT-64R2S2-" + uuid4().hex},
            timeout=120000,
        )
        assert created.status in {201, 202}, (
            f"IT-64R2S2 requires accepted cycle submission; got HTTP {created.status}. "
            "Check authorization/credit prerequisites if the request was denied."
        )
        creation = created.json()
        cycle_id = _identity(creation, "validation_cycle_id")
        assert creation["customer_account_id"] == account_id and cycle_id not in before_ids
        detail_url = base + f"/validation-cycles/{cycle_id}?" + account_query
        deadline = time.monotonic() + 120
        while True:
            response = context.request.get(detail_url)
            assert response.status == 200, "Accepted cycle must be retrievable."
            saved = response.json()
            if saved["cycle"]["state"] != "pending" or time.monotonic() >= deadline:
                break
            time.sleep(0.25)
        cycle = saved["cycle"]
        assert cycle["state"] == "passed-and-closed", (
            "IT-64R2S2 requires the first actionable pass to close the pending cycle directly."
        )
        assert cycle["validation_cycle_id"] == cycle_id
        assert cycle["customer_account_id"] == account_id
        assert cycle["actor_id"] == profile["user_account_id"]
        assert len(saved["submissions"]) == len(saved["attempts"]) == 1
        submission, attempt = saved["submissions"][0], saved["attempts"][0]
        submission_id = _identity(submission, "validation_submission_id")
        attempt_id = _identity(attempt, "validation_attempt_id")
        assert submission["validation_cycle_id"] == attempt["validation_cycle_id"] == cycle_id
        assert attempt["validation_submission_id"] == submission_id
        assert submission["integrity_digest"] == digest
        assert _identity(submission, "artifact_reference")
        assert started <= _time(submission["accepted_at"]) <= _time(attempt["started_at"])
        result = saved["current_result"]
        result_id = _identity(result, "validation_result_id")
        assert result["validation_cycle_id"] == cycle_id
        assert result["validation_submission_id"] == submission_id
        assert result["validation_attempt_id"] == attempt_id
        assert result["actionable"] is True and result["passed"] is True
        assert cycle["current_validation_result_id"] == result_id
        assert _time(result["completed_at"]) >= _time(attempt["started_at"])
        assert _coverage(result) == expected_coverage, "Passing claim must match the reviewed selected coverage."
        run = result["validation_run"]
        run_id = _identity(run, "run_id")
        assert result["validation_run_id"] == run_id
        assert run["findings"] == [], "A passing lifecycle result must not conceal production findings."
        assert all(run["summary"][key] == 0 for key in ("info", "warning", "error", "critical", "fatal"))
        assert _time(run["created_at"]) >= started
        retrieved_run = context.request.get(base + f"/validation-runs/{run_id}")
        assert retrieved_run.status == 200 and retrieved_run.json() == run
        history = saved["history"]
        assert any(event.get("current_state") == "pending" for event in history)
        assert any(event.get("previous_state") == "pending" and
                   event.get("current_state") == "passed-and-closed" for event in history)
        assert not any(event.get("current_state") == "open" for event in history), (
            "A first-result pass must not pass through the correction/open state."
        )
        billable = [e for e in saved["credit_lifecycle_events"]
                    if e.get("event_type") == "billable_validation_service_delivered"]
        assert len(billable) == 1
        assert billable[0]["validation_cycle_id"] == cycle_id
        assert billable[0]["validation_result_id"] == result_id
        assert billable[0]["previous_state"] == "pending"
        assert billable[0]["current_state"] == "passed-and-closed"
        assert billable[0]["billable_validation_service_delivered"] is True
        assert cycle["billable_validation_service_delivered"] is True
        # Retrieve through a fresh page navigation, not a submit-response-only UI.
        response = page.goto(base + "/validation/?" + urlencode({
            "customer_account_id": account_id, "validation_cycle_id": cycle_id,
        }), wait_until="domcontentloaded")
        assert response is not None and response.status == 200
        panel = page.locator(f'[data-validation-cycle-id="{cycle_id}"][data-cycle-state="passed-and-closed"]')
        expect(panel).to_be_visible(timeout=15000)
        expect(panel).to_contain_text(re.compile(r"passed", re.I))
        expect(panel).to_contain_text(report_path.name)
        expect(panel).to_contain_text(case["schema"]["version"])
        for covered in case["constraint_sets"]:
            expect(panel).to_contain_text(covered["constraint_set_id"])
            expect(panel).to_contain_text(covered["version"])
        again = context.request.get(detail_url)
        assert again.status == 200 and again.json() == saved, "Viewing a closed result must not change its lifecycle."
        inventory = context.request.get(base + "/validation-cycles?" + account_query)
        assert inventory.status == 200
        after_ids = [c["validation_cycle_id"] for c in inventory.json()["cycles"]]
        assert len(after_ids) == len(set(after_ids))
        assert set(after_ids) == before_ids | {cycle_id}
    finally:
        context.close()
        if report_path is not None and original is not None:
            assert report_path.read_bytes() == original, "Controlled report bytes were changed."
