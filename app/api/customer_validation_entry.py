"""Verified browser entry to account-owned validation; no cycle creation."""

from html import escape
import os
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from app.adapters.customer_validation_store import CustomerValidationStore
from app.services.account_authorization import (
    AuthorizationResult, CustomerAccountActivity, authorize_customer_activity,
)
from app.services.customer_accounts import CustomerAccountMembership, CustomerAccountRole
from app.services.operating_modes import OperatingMode, determine_operating_mode


router = APIRouter()


class _CallingCodePolicy:
    def recognize_country_calling_code(self, internal_phone_number: str) -> str:
        return "1" if internal_phone_number.startswith("1") else "other"


class _StandardModePolicy:
    def select_operating_mode(self, internal_phone_number: str) -> OperatingMode:
        return OperatingMode.STANDARD


def _verified_identity(request: Request):
    from app import main

    if not request.cookies.get(main.SESSION_COOKIE_NAME):
        return None
    required = ("WORKOS_API_KEY", "WORKOS_CLIENT_ID", "WORKOS_COOKIE_PASSWORD")
    if any(not os.environ.get(name) for name in required):
        raise HTTPException(503, "Hosted sign-in is not configured in the running server.")
    workos = main.WorkOSClient(
        api_key=os.environ["WORKOS_API_KEY"], client_id=os.environ["WORKOS_CLIENT_ID"],
    )
    return main._authenticated_workos_user(request, workos)


def _account_context(request: Request) -> dict:
    identity = _verified_identity(request)
    if identity is None:
        raise HTTPException(401, "Sign in to use customer-account validation.")
    store = CustomerValidationStore()
    user = store.user_for_identity(str(identity["id"]))
    if user is None:
        raise HTTPException(403, "The authenticated identity has no registered customer user link.")
    if not user["phone_verified"]:
        raise HTTPException(403, "A verified phone number is required for account validation.")
    mode = determine_operating_mode(
        user["internal_phone_number"], _CallingCodePolicy(), _StandardModePolicy(),
    )
    accounts = store.accounts_for_user(user["user_account_id"])
    for account in accounts:
        account["can_validate"] = not mode.demo_limitations_apply and any(
            authorize_customer_activity(
                CustomerAccountMembership(
                    human_user_id=user["user_account_id"],
                    role=CustomerAccountRole(role), active=True,
                    customer_account_id=account["customer_account_id"],
                ),
                account["customer_account_id"],
                CustomerAccountActivity.SUBMIT_REPORTS_AND_MANAGE_VALIDATION_CYCLES,
            ).result is AuthorizationResult.ALLOWED
            for role in account["roles"]
        )
    return {
        "user_account_id": user["user_account_id"],
        "display_name": user["display_name"],
        "operating_mode": mode.mode.value,
        "accounts": accounts,
    }


def _selected_account(context: dict, customer_account_id: str) -> dict:
    for account in context["accounts"]:
        if account["customer_account_id"] == customer_account_id and account["can_validate"]:
            return account
    raise HTTPException(403, "An active validation membership in this customer account is required.")


@router.get("/login")
def start_customer_sign_in():
    from app import main

    required = ("WORKOS_API_KEY", "WORKOS_CLIENT_ID", "WORKOS_COOKIE_PASSWORD", "WORKOS_REDIRECT_URI")
    if any(not os.environ.get(name) for name in required):
        raise HTTPException(503, "Hosted sign-in is not configured in the running server.")
    workos = main.WorkOSClient(
        api_key=os.environ["WORKOS_API_KEY"], client_id=os.environ["WORKOS_CLIENT_ID"],
    )
    authorization_url = workos.user_management.get_authorization_url(
        provider="authkit", redirect_uri=os.environ["WORKOS_REDIRECT_URI"],
    )
    return RedirectResponse(authorization_url, status_code=303)


@router.get("/account/context")
def get_customer_account_context(request: Request):
    return _account_context(request)


@router.get("/validation-cycles")
def list_account_validation_cycles(request: Request, customer_account_id: str):
    context = _account_context(request)
    _selected_account(context, customer_account_id)
    return {
        "customer_account_id": customer_account_id,
        "cycles": CustomerValidationStore().cycles_for_account(customer_account_id),
    }


@router.get("/validation/developer/", response_class=HTMLResponse)
def developer_validation_page(request: Request):
    """Expose technical tools only under the configured Developer experience."""
    from app import main
    from app.api.routes import active_experience

    profile = active_experience(request)
    if not (profile.shows_pipeline_stages and profile.shows_technical_artifacts
            and profile.shows_developer_diagnostics):
        raise HTTPException(403, "Developer validation tools are not enabled by the active experience configuration.")
    content = (main.SITE_DIRECTORY / "validation" / "index.html").read_text(encoding="utf-8")
    content = content.replace("<head>", '<head><base href="/validation/">', 1)
    content = content.replace('<body data-operating-mode="demo">', '<body data-experience="developer">', 1)
    content = content.replace('role="status">Demo Mode</p>', 'role="status">Developer experience</p>', 1)
    content = content.replace('href="index.html" aria-current="page"', 'href="/validation/developer/" aria-current="page"', 1)
    return HTMLResponse(content, headers={"Cache-Control": "no-store"})


@router.get("/validation/", response_class=HTMLResponse)
def account_validation_page(request: Request, customer_account_id: str | None = None, validation_cycle_id: str | None = None):
    from app import main

    # IT-46R4S1: signed-in customers use the same integrated upload API
    # that already enforces their verified identity and local account link.
    # This presentation marker grants no authorization; POST verifies again.
    if not customer_account_id:
        page_path = main.SITE_DIRECTORY / "validation" / "index.html"
        client_id = os.environ.get("WORKOS_CLIENT_ID")
        redirect_uri = os.environ.get("WORKOS_REDIRECT_URI")
        if request.cookies.get(main.SESSION_COOKIE_NAME) and client_id and redirect_uri:
            workos = main.WorkOSClient(
                api_key=os.environ.get("WORKOS_API_KEY"), client_id=client_id,
            )
            identity = main._authenticated_workos_user(request, workos)
            links = getattr(request.app.state, "workos_identity_account_links", {})
            if identity and links.get(str(identity["id"])):
                content = page_path.read_text(encoding="utf-8")
                content = content.replace(
                    '<body data-operating-mode="demo">',
                    '<body data-operating-mode="demo" data-validation-upload="integrated">',
                    1,
                )
                return HTMLResponse(content, headers={
                    "Cache-Control": "no-store", "Vary": "Cookie",
                })
        # Anonymous Demo visitors retain their existing entry behavior.
        return FileResponse(page_path, headers={"Vary": "Cookie"})
    try:
        context = _account_context(request)
    except HTTPException as error:
        if error.status_code != 401:
            raise
        # IT-64R1S3: browser entry needs an actionable authentication challenge.
        # API routes retain their JSON denial; account lookup and cycle creation
        # do not run for this challenge. Do not echo an unverified account ID.
        response = HTMLResponse('''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sign in for account validation</title>
<link rel="stylesheet" href="/assets/css/site.css"></head>
<body><main class="content-section">
<h1>Sign in for account validation</h1>
<p>Sign in to request a validation cycle for your customer account.</p>
<p>No validation cycle or report submission has been created.</p>
<p><a href="/login">Sign in</a></p>
<p><a href="/">Home</a></p>
</main></body></html>''', status_code=401, headers={"Cache-Control": "no-store"})
        if request.cookies.get(main.SESSION_COOKIE_NAME):
            response.delete_cookie(
                main.SESSION_COOKIE_NAME, path="/", secure=True,
                httponly=True, samesite="lax",
            )
        return response
    account = _selected_account(context, customer_account_id)
    if validation_cycle_id:
        from app.api.account_validation_cycles import result_page
        return result_page(request, customer_account_id, validation_cycle_id)
    from app.services.account_cycle_validation import CycleStore
    available_credits = CycleStore().available_credits(customer_account_id)
    validation_disabled = '' if available_credits else 'disabled'
    query = urlencode({"customer_account_id": customer_account_id})
    return HTMLResponse(f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Account report validation</title><link rel="stylesheet" href="/assets/css/site.css"></head>
<body><main class="content-section">
<h1>Account report validation</h1>
<p id="authenticated-user" data-user-account-id="{escape(context['user_account_id'])}">
Signed in as {escape(context['display_name'])}</p>
<p id="selected-customer-account" data-customer-account-id="{escape(customer_account_id)}">
Customer account: {escape(account['label'])}</p>
<p id="operating-mode" data-operating-mode="{escape(context['operating_mode'])}">
{escape(context['operating_mode'].title())} mode</p>
<button type="button" id="new-cycle-action" aria-controls="new-cycle-preparation" aria-expanded="false">
New validation cycle</button>
<section id="new-cycle-preparation" hidden><h2>Prepare a new validation cycle</h2>
<p>Choose the report you intend to validate. No cycle is created by opening this page.</p>
<label for="new-report">Appraisal XML report</label><input id="new-report" type="file" accept=".xml">
<p>Available validation credits: {available_credits}</p>
<button type="button" id="submit-new-cycle" {validation_disabled}>Validate Appraisal</button>
<p id="submission-status" role="status"></p></section>
<p><a href="/validation-cycles?{escape(query)}">View recorded validation cycles</a></p>
<p><a href="/">Home</a></p>
</main><script>
document.getElementById('new-cycle-action').addEventListener('click', (event) => {{
  document.getElementById('new-cycle-preparation').hidden = false;
  event.currentTarget.setAttribute('aria-expanded', 'true');
}});
document.getElementById('submit-new-cycle').addEventListener('click', async (event) => {{
  const file = document.getElementById('new-report').files[0];
  const status = document.getElementById('submission-status');
  if (!file) {{ status.textContent = 'Choose an appraisal XML report.'; return; }}
  event.currentTarget.disabled = true;
  status.textContent = 'Validating the report…';
  try {{
    const account = document.getElementById('selected-customer-account').dataset.customerAccountId;
    const response = await fetch('/validation-cycles?customer_account_id=' + encodeURIComponent(account), {{
      method: 'POST', headers: {{'Content-Type': 'application/json', 'Idempotency-Key': crypto.randomUUID()}},
      body: JSON.stringify({{customer_account_id: account, package_name: file.name, xml_text: await file.text()}})
    }});
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || 'Validation could not complete.');
    window.location.assign('/validation/?customer_account_id=' + encodeURIComponent(account)
      + '&validation_cycle_id=' + encodeURIComponent(result.validation_cycle_id));
  }} catch (error) {{
    status.textContent = error.message;
    document.getElementById('submit-new-cycle').disabled = false;
  }}
}});
</script></body></html>''')


from app.api.account_validation_cycles import router as account_cycle_router
router.include_router(account_cycle_router)
