"""Run IT-64 with visible real sign-in and explicit local prerequisites."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    root = Path(__file__).resolve().parents[2]
    environment = os.environ.copy()
    base = environment.get("UAD_IT64_BASE_URL", "http://localhost:4000").rstrip("/")
    profile_path = Path(environment.get("UAD_IT64_CUSTOMER_PROFILE", str(root / "tests/fixtures/it_64/r1/s1/customer-profile.json"))).resolve()
    store_path = Path(environment.get("UAD_CUSTOMER_STORE", str(root / "data/customer-validation.sqlite3"))).resolve()
    if not profile_path.is_file() or not store_path.is_file():
        raise ValueError(f"Use the prepared test profile and initialized server store. Profile: {profile_path}; store: {store_path}")
    profile = json.loads(profile_path.read_text(encoding="utf-8-sig"))
    with sqlite3.connect(store_path.as_uri() + "?mode=ro", uri=True) as db:
        user = db.execute("SELECT workos_user_id FROM entry_users WHERE user_account_id=?", (profile["user_account_id"],)).fetchone()
        if not user or not user[0].startswith("user_"):
            raise ValueError("The local identity must link to a WorkOS user_ ID, not a client_ application ID.")
    try:
        with urlopen(base + "/health", timeout=10) as response:
            if response.status != 200:
                raise ValueError("The application health check failed.")
        with urlopen(base + "/openapi.json", timeout=10) as response:
            specification = json.load(response)
        if "post" not in specification.get("paths", {}).get("/validation-cycles", {}):
            raise ValueError("Install the cycle API repair and restart the server; POST /validation-cycles is still missing.")
        try:
            build_opener(NoRedirect()).open(Request(base + "/login"), timeout=10)
            raise ValueError("/login did not redirect to hosted authentication.")
        except HTTPError as response:
            if response.code not in (302, 303, 307):
                raise ValueError(f"/login returned HTTP {response.code}; check the server's WorkOS configuration.")
            redirect = parse_qs(urlsplit(response.headers.get("Location", "")).query).get("redirect_uri", [None])[0]
            if redirect != base + "/auth/callback":
                raise ValueError(f"The server callback must exactly match {base}/auth/callback. Use the same hostname and port for the server and tests.")
    except URLError as error:
        raise ValueError(f"Cannot reach {base}. Keep run_server.py running in its own terminal. Do not stop it to run pytest.") from error
    environment["UAD_IT64_CUSTOMER_PROFILE"] = str(profile_path)
    environment["UAD_CUSTOMER_STORE"] = str(store_path)
    print("Server reachable and cycle operation present. Keep Outlook open for the test user's verification code.", flush=True)
    print("Complete sign-in in the visible pytest browser, not an unrelated browser window. Passwords/session state are not saved by this launcher.", flush=True)
    args = sys.argv[1:] or ["tests", "-k", "it_64"]
    return subprocess.run([sys.executable, "-B", "-m", "pytest", *args, "--headed", "-s", "-q", "--tb=short", "-p", "no:cacheprovider"], cwd=root, env=environment, check=False).returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, sqlite3.Error) as error:
        print(f"IT-64 setup: {error}", file=sys.stderr)
        raise SystemExit(2)
