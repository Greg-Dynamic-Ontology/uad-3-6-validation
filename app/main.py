import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from workos import WorkOSClient
from workos.session import seal_session_from_auth_response

from app.api.routes import router
from app.core.config import settings


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SITE_DIRECTORY = PROJECT_ROOT / "site"
ACTIVE_CONFIGURATION_FILE = (
    PROJECT_ROOT / "config" / "configuration.ttl"
)

SESSION_COOKIE_NAME = "wos_session"
ACCOUNT_SETUP_PATH = "/account/setup"

app = FastAPI(title=settings.app_name, version="0.1.0")
app.state.configuration_file = ACTIVE_CONFIGURATION_FILE

# IT-2R6 must replace this in-memory seam with persisted identity links.
# Until then, no WorkOS identity resolves to a local UAD account.
app.state.workos_identity_account_links: dict[str, str] = {}


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

        sealed_session = request.cookies.get(SESSION_COOKIE_NAME)
        cookie_password = os.getenv("WORKOS_COOKIE_PASSWORD")

        if sealed_session and cookie_password:
            try:
                session = workos.user_management.load_sealed_session(
                    session_data=sealed_session,
                    cookie_password=cookie_password,
                )
                authentication = session.authenticate()
            except Exception:
                authentication = None

            if getattr(authentication, "authenticated", False):
                user = getattr(authentication, "user", None)
                workos_user_id = (
                    user.get("id")
                    if isinstance(user, dict)
                    else None
                )

                if workos_user_id:
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


app.include_router(router)
app.mount(
    "/",
    StaticFiles(directory=SITE_DIRECTORY, html=True),
    name="site",
)