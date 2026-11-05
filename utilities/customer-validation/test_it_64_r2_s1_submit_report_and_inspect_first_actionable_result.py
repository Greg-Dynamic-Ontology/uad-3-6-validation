"""IT-64R2S1: real browser upload connects lifecycle and production validation.

Prerequisites: running WorkOS-configured server, completed IT-64 customer
profile, and an account authorized for a new cycle (including its existing
credit policy). Complete real hosted sign-in in the visible browser. No auth,
payment, lifecycle, validation, or storage responses are mocked or patched.

The controlled report is a temporary copy of the published SF1 sample with
AddressLineText removed from its first subject PROPERTY/ADDRESS. UAD1001 is
the independent expected governed finding. The published source is never edited.

Proposed observable integration contract:
- Existing #new-cycle-action exposes #new-report and a Validate Appraisal action.
- The browser submits POST /validation-cycles and gets 201/202 JSON identifying
  validation_cycle_id and customer_account_id (possibly with further fields).
- The rendered result exposes [data-validation-cycle-id][data-cycle-state=open].
- GET /validation-cycles/{id}?customer_account_id=... retrieves committed
  cycle, submissions, attempts, current_result, history, and credit_lifecycle_events.
- The current_result carries validation_run plus schema and constraint-set
  provenance, and links the lifecycle cycle/submission/attempt/run identities.
- The existing GET /validation-runs/{run_id} retrieves the same actual engine run.

The JSON fields asserted below are an explicit proposed integration contract,
not a claim that these routes/storage adapters are already implemented. Production
worker invocation is checked through its registered run and independent engine
output; a black-box browser test cannot prove internal call order by itself.
No storage table names or test-only server endpoints are prescribed.
"""

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from uuid import UUID
from xml.etree import ElementTree as ET

from tests.it64_live_auth import visible_sign_in_required, session_state, sign_in, wait_for_verified_account, cycle_baseline

from playwright.sync_api import Browser, expect


ROOT = Path(__file__).resolve().parents[1]
NS = {"m": "http://www.mismo.org/residential/2009/schemas"}
RULE_ID = "UAD1001"
ROW_ID = "0100.0007"


def _timestamp(value):
    assert isinstance(value, str) and value, "Lifecycle time must be recorded."
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert result.tzinfo is not None, "Lifecycle time must include its timezone."
    return result


def _id(record, key):
    value = record.get(key)
    assert isinstance(value, str) and value, f"Missing contracted identity: {key}"
    return value


def _controlled_report(tmp_path):
    published = ROOT / "specs/fannie-mae/Appendix D-1 SF1_Appraisal/SF1_Appraisal_v1.4.xml"
    assert published.is_file(), f"IT-64R2S1 setup: published sample not found: {published}"
    original_digest = sha256(published.read_bytes()).hexdigest()
    tree = ET.parse(published)
    subjects = tree.findall(".//m:PROPERTY[@ValuationUseType='SubjectProperty']", NS)
    assert subjects, "Controlled sample must contain a governed subject-property context."
    address = subjects[0].find("m:ADDRESS", NS)
    assert address is not None, "Controlled sample requires its existing subject ADDRESS."
    lines = address.findall("m:AddressLineText", NS)
    assert lines and any((line.text or "").strip() for line in lines)
    for line in lines:
        address.remove(line)
    content = ET.tostring(tree.getroot(), encoding="utf-8", xml_declaration=True)
    destination = tmp_path / "it64r2s1-subject-address-required.xml"
    destination.write_bytes(content)
    return published, original_digest, destination, content


def _finding_signature(finding):
    # Exclude minted finding IDs and compare governed behavior and XML context.
    return tuple(finding.get(field) for field in (
        "rule_id", "row_id", "severity", "data_location", "finding",
        "primary_data_element", "property_affected", "violation_kind",
    ))


def test_it_64_r2_s1_submits_report_and_inspects_first_actionable_result(
    browser: Browser, tmp_path: Path, pytestconfig,
) -> None:
    visible_sign_in_required(pytestconfig)
    base = os.environ.get("UAD_IT64_BASE_URL", "http://localhost:4000").rstrip("/")
    origin = urlsplit(base)
    assert origin.scheme in {"http", "https"} and origin.netloc
    profile_path = Path(os.environ.get(
        "UAD_IT64_CUSTOMER_PROFILE", str(ROOT / "tests/fixtures/it_64/r1/s1/customer-profile.json")
    )).expanduser()
    assert profile_path.is_file(), f"IT-64R2S1 setup: completed customer profile required: {profile_path}"
    profile = json.loads(profile_path.read_text(encoding="utf-8-sig"))
    for field in ("user_account_id", "customer_account_id"):
        assert isinstance(profile.get(field), str) and profile[field] and not profile[field].startswith("REPLACE_"), (
            f"IT-64R2S1 setup: real {field} required."
        )
    account_id = profile["customer_account_id"]
    query = urlencode({"customer_account_id": account_id})
    published, published_digest, report_path, report_bytes = _controlled_report(tmp_path)
    digest = sha256(report_bytes).hexdigest()
    context = browser.new_context(storage_state=session_state(profile, base))
    page = context.new_page()
    try:
        sign_in(page, profile, base)
        identity_response = context.request.get(base + "/account/context")
        assert identity_response.status == 200, "Setup: sign in as the linked UAD customer."
        identity = identity_response.json()
        assert identity["user_account_id"] == profile["user_account_id"]
        assert any(a["customer_account_id"] == account_id and a["can_validate"] for a in identity["accounts"]), (
            "Setup: this user must have active validation permission in the chosen account."
        )
        inventory_response = context.request.get(base + "/validation-cycles?" + query)
        assert inventory_response.status == 200
        before_ids = {item["validation_cycle_id"] for item in inventory_response.json()["cycles"]}
        response = page.goto(base + "/validation/?" + query, wait_until="domcontentloaded")
        assert response is not None and response.status == 200
        page.get_by_role("button", name="New validation cycle", exact=True).click()
        upload = page.locator("#new-report")
        expect(upload).to_be_visible()
        upload.set_input_files(str(report_path))
        submit = page.get_by_role("button", name="Validate Appraisal", exact=True)
        assert submit.count() == 1, (
            "IT-64R2S1 requires the account page to submit the selected report "
            "through a Validate Appraisal action to create a cycle and return "
            "the production engine's actionable result. File preparation alone is insufficient."
        )
        expect(submit).to_be_visible()
        expect(submit).to_be_enabled()

        # Independent oracle: the real unpatched production engine must detect
        # the known governed violation in the exact bytes about to be uploaded.
        from app.models.validation import ValidationRequest
        from app.services.validation import ValidationService
        from app.services.xml_schema_validator import UAD36_SCHEMA_PATH, UAD36_SCHEMA_VERSION

        oracle = ValidationService().validate(ValidationRequest(
            package_name=report_path.name, xml_text=report_bytes.decode("utf-8"),
        ))
        expected = [f.model_dump(mode="json") for f in oracle.findings if f.rule_id == RULE_ID and f.row_id == ROW_ID]
        assert expected and all(f["data_location"] for f in expected), (
            "Controlled-fixture precondition: the production engine must detect UAD1001 "
            "at the subject address under the active governed workbook."
        )
        started = datetime.now(timezone.utc)
        with page.expect_response(
            lambda result: urlsplit(result.url).netloc == origin.netloc
            and urlsplit(result.url).path == "/validation-cycles"
            and result.request.method == "POST", timeout=120000,
        ) as posted:
            submit.click()
        created = posted.value
        assert created.status in {201, 202}, (
            f"IT-64R2S1 requires browser cycle submission to succeed; received HTTP {created.status}."
        )
        assert "application/json" in created.headers.get("content-type", "")
        creation = created.json()
        cycle_id = _id(creation, "validation_cycle_id")
        UUID(cycle_id)
        assert creation["customer_account_id"] == account_id
        assert cycle_id not in before_ids
        panel = page.locator(f'[data-validation-cycle-id="{cycle_id}"][data-cycle-state="open"]')
        expect(panel).to_be_visible(timeout=120000)
        expect(panel).to_contain_text(RULE_ID)
        expect(panel).to_contain_text(report_path.name)
        for finding in expected:
            expect(panel).to_contain_text(finding["finding"])
            expect(panel).to_contain_text(finding["data_location"])

        saved_response = context.request.get(base + f"/validation-cycles/{cycle_id}?" + query)
        assert saved_response.status == 200, "The lifecycle outcome must be retrievable independently of the submit response."
        saved = saved_response.json()
        cycle = saved["cycle"]
        assert cycle["validation_cycle_id"] == cycle_id
        assert cycle["customer_account_id"] == account_id
        assert cycle["actor_id"] == profile["user_account_id"]
        assert cycle["state"] == "open"
        submissions, attempts = saved["submissions"], saved["attempts"]
        assert len(submissions) == len(attempts) == 1
        submission, attempt = submissions[0], attempts[0]
        submission_id = _id(submission, "validation_submission_id")
        attempt_id = _id(attempt, "validation_attempt_id")
        UUID(submission_id)
        UUID(attempt_id)
        assert submission["validation_cycle_id"] == attempt["validation_cycle_id"] == cycle_id
        assert attempt["validation_submission_id"] == submission_id
        assert submission["integrity_digest"] == digest
        assert _id(submission, "artifact_reference")
        accepted_at = _timestamp(submission["accepted_at"])
        attempt_started = _timestamp(attempt["started_at"])
        assert started <= accepted_at <= attempt_started
        result = saved["current_result"]
        result_id = _id(result, "validation_result_id")
        assert result["validation_cycle_id"] == cycle_id
        assert result["validation_submission_id"] == submission_id
        assert result["validation_attempt_id"] == attempt_id
        assert result["actionable"] is True and result["passed"] is False
        assert cycle["current_validation_result_id"] == result_id
        completed_at = _timestamp(result["completed_at"])
        assert attempt_started <= completed_at
        run = result["validation_run"]
        run_id = _id(run, "run_id")
        assert result["validation_run_id"] == run_id
        assert result["schema"]["version"] == UAD36_SCHEMA_VERSION
        assert result["schema"]["sha256"] == sha256(UAD36_SCHEMA_PATH.read_bytes()).hexdigest()
        assert _id(result["schema"], "source_document")
        coverage = result["constraint_sets"]
        assert isinstance(coverage, list) and coverage
        for constraint_set in coverage:
            for key in ("constraint_set_id", "version", "source_document", "source_sha256"):
                assert _id(constraint_set, key)
        actual = [f for f in run["findings"] if f.get("rule_id") == RULE_ID and f.get("row_id") == ROW_ID]
        assert sorted(map(_finding_signature, actual), key=repr) == sorted(map(_finding_signature, expected), key=repr)
        for finding in actual:
            source = finding.get("source")
            assert source and source.get("source_document"), "Finding must retain governed source provenance."

        # Reuse the existing production run retrieval endpoint, not a test stub.
        actual_run_response = context.request.get(base + f"/validation-runs/{run_id}")
        assert actual_run_response.status == 200
        assert actual_run_response.json() == run
        assert run_id != oracle.run_id
        assert _timestamp(run["created_at"]) >= started

        history = saved["history"]
        assert history and any(event.get("current_state") == "pending" for event in history), (
            "Lifecycle history must preserve the original pending state, not only the final open state."
        )
        assert any(event.get("previous_state") == "pending" and event.get("current_state") == "open" for event in history)
        billable = [event for event in saved["credit_lifecycle_events"]
                    if event.get("event_type") == "billable_validation_service_delivered"]
        assert len(billable) == 1
        assert billable[0]["validation_cycle_id"] == cycle_id
        assert billable[0]["validation_result_id"] == result_id
        assert billable[0]["previous_state"] == "pending" and billable[0]["current_state"] == "open"
        assert billable[0]["billable_validation_service_delivered"] is True
        assert cycle["billable_validation_service_delivered"] is True
        after = context.request.get(base + "/validation-cycles?" + query)
        assert after.status == 200
        after_ids = [item["validation_cycle_id"] for item in after.json()["cycles"]]
        assert len(after_ids) == len(set(after_ids))
        assert set(after_ids) - before_ids == {cycle_id}
        assert before_ids.issubset(after_ids)
        print(f"Created open cycle {cycle_id}; submission, attempt, run, governed finding, and billable event verified.")
    finally:
        context.close()
        assert sha256(published.read_bytes()).hexdigest() == published_digest, "Published source report was changed."
        assert report_path.read_bytes() == report_bytes, "The uploaded report file was changed."
