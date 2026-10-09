"""Live WorkOS setup prerequisite for IT-2R5S1, not full sign-in acceptance.

Reads non-secret configuration from process environment, never from .env files.
Requires network access. Does not authenticate a user or create a UAD session.
"""

import os
import secrets
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

import pytest


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def test_it_2_r5_s1_workos_accepts_hosted_authkit_request() -> None:
    client_id = os.environ.get("WORKOS_CLIENT_ID", "").strip()
    redirect_uri = os.environ.get("WORKOS_REDIRECT_URI", "").strip()
    assert client_id and redirect_uri, (
        "WorkOS setup incomplete: set WORKOS_CLIENT_ID and WORKOS_REDIRECT_URI "
        "in this terminal after configuring your WorkOS environment. "
        "This is setup RED, not a failure of UAD sign-in behavior."
    )
    assert client_id.startswith("client_"), "Expected a WorkOS client ID."
    callback = urlsplit(redirect_uri)
    assert callback.hostname and callback.scheme in {"http", "https"}, (
        "WORKOS_REDIRECT_URI must be the callback URL registered with WorkOS."
    )
    query = urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "provider": "authkit",
        "state": secrets.token_urlsafe(32),
    })
    request = Request("https://api.workos.com/user_management/authorize?" + query)
    try:
        response = build_opener(NoRedirect()).open(request, timeout=20)
    except HTTPError as exc:
        response = exc
    except (URLError, TimeoutError):
        pytest.fail("Cannot reach WorkOS; check network access and service availability.", pytrace=False)

    with response:
        assert response.code in {302, 303, 307, 308}, (
            f"WorkOS did not return a hosted sign-in redirect (HTTP {response.code}). "
            "Check the client ID, registered redirect URI, and AuthKit setup."
        )
        location = urlsplit(response.headers.get("Location", ""))
        assert location.scheme == "https" and location.hostname, (
            "WorkOS did not provide an HTTPS hosted sign-in destination."
        )
        assert (location.netloc, location.path) != (callback.netloc, callback.path), (
            "WorkOS redirected directly to the callback instead of hosted sign-in."
        )
