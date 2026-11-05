"""Authenticated HTTP boundary for durable report-validation cycles."""
from html import escape
from urllib.parse import urlencode
from uuid import uuid4
from functools import partial
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict
from starlette.concurrency import run_in_threadpool

from app.api.customer_validation_entry import _account_context, _selected_account
from app.services.account_cycle_validation import ROOT, CycleStore, submit_new_cycle
from app.services.validation import validation_service


router = APIRouter()


class NewCycleRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    customer_account_id: str
    package_name: str
    xml_text: str


def _authorized(request, account_id):
    context = _account_context(request)
    _selected_account(context, account_id)
    return context


@router.post("/validation-cycles", status_code=201)
async def create_account_cycle(request: Request, customer_account_id: str):
    # Authenticate before parsing client identities or touching lifecycle storage.
    context = _authorized(request, customer_account_id)
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
        raise HTTPException(403, "A same-origin account request is required.")
    try:
        payload = NewCycleRequest.model_validate(await request.json())
    except ValueError:
        raise HTTPException(422, "Provide customer_account_id, package_name, and xml_text.")
    if payload.customer_account_id != customer_account_id:
        raise HTTPException(403, "The submitted account must match the authorized account.")
    if not payload.xml_text.strip() or not payload.package_name.strip():
        raise HTTPException(422, "A named, nonempty XML report is required.")
    if len(payload.xml_text.encode("utf-8")) > 25 * 1024 * 1024:
        raise HTTPException(413, "The XML report exceeds 25 MiB.")
    if Path(request.app.state.configuration_file).resolve() != (ROOT / "config/configuration.ttl").resolve():
        raise HTTPException(503, "This engine currently supports only its governed default configuration.")
    # The existing production engine has one governed default configuration.
    # Do not accept client-provided coverage/version claims or identity headers.
    try:
        cycle_id = await run_in_threadpool(partial(submit_new_cycle,
            account_id=customer_account_id, actor_id=context["user_account_id"],
            package_name=payload.package_name, content=payload.xml_text.encode("utf-8"),
            request_key=request.headers.get("Idempotency-Key") or uuid4().hex,
        ))
    except PermissionError as error:
        raise HTTPException(402, str(error))
    except ValueError as error:
        raise HTTPException(409, str(error))
    except Exception:
        raise HTTPException(503, "Validation could not complete. Any execution credit was restored; inspect cycle history.")
    return {"validation_cycle_id": cycle_id, "customer_account_id": customer_account_id}


@router.get("/validation-cycles/{validation_cycle_id}")
def retrieve_account_cycle(request: Request, validation_cycle_id: str, customer_account_id: str):
    _authorized(request, customer_account_id)
    saved = CycleStore().detail(validation_cycle_id, customer_account_id)
    if saved is None:
        raise HTTPException(404, "Validation cycle not found in this account.")
    return saved


@router.get("/validation-runs/{run_id}")
def retrieve_recorded_run(request: Request, run_id: str):
    saved = CycleStore().run(run_id)
    if saved:
        run, account_id = saved
        _authorized(request, account_id)
        return run
    from app.api.routes import get_validation_run
    return get_validation_run(run_id)


def result_page(request, customer_account_id, cycle_id):
    context = _authorized(request, customer_account_id)
    saved = CycleStore().detail(cycle_id, customer_account_id)
    if saved is None:
        raise HTTPException(404, "Validation cycle not found in this account.")
    cycle, result = saved["cycle"], saved["current_result"]
    e = lambda value: escape(str(value), quote=True)
    title = "Passed and closed" if cycle["state"] == "passed-and-closed" else cycle["state"].title()
    content = "<p>No actionable result is available yet.</p>"
    if result:
        coverage = "".join(f'<li>{e(c["constraint_set_id"])} — {e(c["version"])}; '
                           f'{e(c["supported_rule_count"])} supported rules of {e(c["published_row_count"])} published rows; '
                           f'worksheet {e(c["worksheet"])}</li>' for c in result["constraint_sets"])
        findings = "".join(f'<li><strong>{e(f.get("rule_id") or "Schema")}</strong>: {e(f.get("finding") or f.get("message") or "")} '
                           f'<p>XML context: {e(f.get("data_location") or "/")}</p></li>' for f in result["findings"])
        content = f'''<p>Result: {e(result['validation_result_id'])}</p>
<p>Submission: {e(result['validation_submission_id'])}</p>
<p>Attempt: {e(result['validation_attempt_id'])}</p><p>Run: {e(result['validation_run_id'])}</p>
<h2>Coverage evaluated</h2><p>Schema reference: {e(result['schema']['version'])}</p>
<p>The production engine performed the governed XSD assessment and the selected supported workbook rules.
This result does not certify compliance outside that coverage. SHACL execution was not performed by this run.</p><ul>{coverage}</ul>
<details><summary>Exact evaluated coverage</summary><pre>{e(__import__('json').dumps(result['constraint_sets'], indent=2))}</pre></details>
<h2>Findings</h2><ul>{findings}</ul>'''
    packages = "".join(f'<li>{e(s["package_name"])}</li>' for s in saved["submissions"])
    return HTMLResponse(f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Account validation result</title><link rel="stylesheet" href="/assets/css/site.css"></head>
<body><main class="content-section"><p>Signed in as {e(context['display_name'])}</p>
<section data-validation-cycle-id="{e(cycle_id)}" data-cycle-state="{e(cycle['state'])}">
<h1>{e(title)}</h1><p>Cycle: {e(cycle_id)}</p><ul>{packages}</ul>{content}</section>
<p><a href="/validation/?{e(urlencode({'customer_account_id': customer_account_id}))}">Account validation</a></p>
</main></body></html>''', headers={"Cache-Control": "no-store"})
