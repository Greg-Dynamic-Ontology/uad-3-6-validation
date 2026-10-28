import os
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict
from workos import WorkOSClient

from app.api.routes import router
from app.core.config import settings
from app.services.user_accounts import UserAccount, create_user_account
from app.api.customer_validation_entry import router as customer_validation_entry_router


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SITE_DIRECTORY = PROJECT_ROOT / "site"
ACTIVE_CONFIGURATION_FILE = (
    PROJECT_ROOT / "config" / "configuration.ttl"
)

SESSION_COOKIE_NAME = "wos_session"
ACCOUNT_SETUP_PATH = "/account/setup"


class AccountSetupRequest(BaseModel):
    """Shared UAD account data and an optional company association."""

    model_config = ConfigDict(extra="forbid")

    user_data: dict[str, str]
    company_id: str | None = None


class _ApplicationUserAccountIdGenerator:
    def new_user_account_id(self) -> str:
        return f"user-{uuid4()}"


class _ApplicationUserAccountRepository:
    """Store account records in the current application process."""

    def __init__(self, application: FastAPI) -> None:
        self.application = application

    def company_exists(self, company_id: str) -> bool:
        return company_id in self.application.state.companies

    def add(self, user_account: UserAccount) -> None:
        self.application.state.user_accounts[
            user_account.user_account_id
        ] = user_account


def _user_account_response(
    account: UserAccount,
) -> dict[str, object]:
    return {
        "user_account_id": account.user_account_id,
        "user_data": dict(account.user_data),
        "company_id": account.company_id,
        "account_kind": account.account_kind.value,
    }


app = FastAPI(title=settings.app_name, version="0.1.0")
app.state.configuration_file = ACTIVE_CONFIGURATION_FILE
app.state.workos_identity_account_links: dict[str, str] = {}
app.state.user_accounts: dict[str, UserAccount] = {}
app.state.companies: dict[str, object] = {}
app.state.authorized_company_ids_by_workos_user: dict[str, set[str]] = {}


def _authenticated_workos_user(
    request: Request,
    workos: WorkOSClient,
) -> dict[str, object] | None:
    sealed_session = request.cookies.get(SESSION_COOKIE_NAME)
    cookie_password = os.getenv("WORKOS_COOKIE_PASSWORD")

    if not sealed_session or not cookie_password:
        return None

    try:
        session = workos.user_management.load_sealed_session(
            session_data=sealed_session,
            cookie_password=cookie_password,
        )
        authentication = session.authenticate()
    except Exception:
        return None

    if not getattr(authentication, "authenticated", False):
        return None

    user = getattr(authentication, "user", None)
    if hasattr(user, "to_dict"):
        user = user.to_dict()

    if not isinstance(user, dict) or not user.get("id"):
        return None

    return user


@app.middleware("http")
async def protect_validation_with_workos_session(
    request: Request,
    call_next,
):
    if (
        request.method == "POST"
        and request.url.path == "/validate/uad36"
    ):
        client_id = os.getenv("WORKOS_CLIENT_ID")
        redirect_uri = os.getenv("WORKOS_REDIRECT_URI")

        if not client_id or not redirect_uri:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": (
                        "Hosted AuthKit sign-in is not configured."
                    )
                },
            )

        workos = WorkOSClient(
            api_key=os.getenv("WORKOS_API_KEY"),
            client_id=client_id,
        )

        user = _authenticated_workos_user(request, workos)

        if user:
            workos_user_id = user["id"]
            account_links = getattr(
                request.app.state,
                "workos_identity_account_links",
                {},
            )

            if account_links.get(workos_user_id):
                return await call_next(request)

            return RedirectResponse(
                url=ACCOUNT_SETUP_PATH,
                status_code=303,
            )

        authorization_url = (
            workos.user_management.get_authorization_url(
                provider="authkit",
                redirect_uri=redirect_uri,
            )
        )
        return RedirectResponse(
            url=authorization_url,
            status_code=303,
        )

    return await call_next(request)


@app.post(
    ACCOUNT_SETUP_PATH,
    status_code=201,
    response_model=None,
)
def complete_account_setup(
    request: Request,
    account_request: AccountSetupRequest,
) -> dict[str, object] | JSONResponse:
    """Create an account or return the account already linked to this identity."""

    api_key = os.getenv("WORKOS_API_KEY")
    client_id = os.getenv("WORKOS_CLIENT_ID")
    cookie_password = os.getenv("WORKOS_COOKIE_PASSWORD")

    if not api_key or not client_id or not cookie_password:
        raise HTTPException(
            status_code=503,
            detail="WorkOS authentication is not configured.",
        )

    workos = WorkOSClient(
        api_key=api_key,
        client_id=client_id,
    )
    user = _authenticated_workos_user(request, workos)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="A validated WorkOS session is required.",
        )

    workos_user_id = str(user["id"])
    account_links = request.app.state.workos_identity_account_links
    existing_account_id = account_links.get(workos_user_id)

    if existing_account_id:
        existing_account = request.app.state.user_accounts.get(
            existing_account_id
        )
        if existing_account is None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "The WorkOS identity link does not resolve to a "
                    "local UAD account."
                ),
            )

        return JSONResponse(
            status_code=200,
            content=_user_account_response(existing_account),
        )

    forbidden_user_data = {
        "password",
        "password_hash",
        "credential",
        "credentials",
    }
    supplied_keys = {
        key.casefold()
        for key in account_request.user_data
    }
    if supplied_keys.intersection(forbidden_user_data):
        raise HTTPException(
            status_code=422,
            detail="UAD account data must not contain credentials.",
        )

    company_id = account_request.company_id
    if company_id is not None:
        authorized_company_ids = (
            request.app.state.authorized_company_ids_by_workos_user.get(
                workos_user_id,
                set(),
            )
        )
        if company_id not in authorized_company_ids:
            raise HTTPException(
                status_code=403,
                detail=(
                    "The WorkOS identity is not authorized to join "
                    "that company."
                ),
            )

    repository = _ApplicationUserAccountRepository(request.app)

    try:
        account = create_user_account(
            user_data=account_request.user_data,
            company_id=company_id,
            id_generator=_ApplicationUserAccountIdGenerator(),
            account_repository=repository,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    account_links[workos_user_id] = account.user_account_id

    return _user_account_response(account)


@app.get("/auth/callback")
def workos_authentication_callback(
    code: str | None = None,
):
    if not code:
        return JSONResponse(
            status_code=400,
            content={"detail": "An authentication code is required."},
        )

    api_key = os.getenv("WORKOS_API_KEY")
    client_id = os.getenv("WORKOS_CLIENT_ID")
    cookie_password = os.getenv("WORKOS_COOKIE_PASSWORD")

    if not api_key or not client_id or not cookie_password:
        return JSONResponse(
            status_code=503,
            content={
                "detail": (
                    "WorkOS authentication is not configured."
                )
            },
        )

    workos = WorkOSClient(
        api_key=api_key,
        client_id=client_id,
    )

    try:
        authentication = workos.user_management.authenticate_with_code(
            code=code,
        )
        user = authentication.user.to_dict()
        impersonator = (
            authentication.impersonator.to_dict()
            if authentication.impersonator is not None
            else None
        )
        from workos.session import seal_session_from_auth_response

        sealed_session = seal_session_from_auth_response(
            access_token=authentication.access_token,
            refresh_token=authentication.refresh_token,
            user=user,
            impersonator=impersonator,
            cookie_password=cookie_password,
        )
    except Exception:
        return JSONResponse(
            status_code=401,
            content={
                "detail": (
                    "The WorkOS authentication result could not be validated."
                )
            },
        )

    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=sealed_session,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    return response


app.include_router(customer_validation_entry_router)
app.include_router(router)
app.mount(
    "/",
    StaticFiles(directory=SITE_DIRECTORY, html=True),
    name="site",
)