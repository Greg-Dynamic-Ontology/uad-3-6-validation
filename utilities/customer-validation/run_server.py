"""Launch the local UAD server with WorkOS settings confined to its process."""

from getpass import getpass
import os
from pathlib import Path
import secrets
import subprocess
import sys
from urllib.parse import urlsplit


def main() -> int:
    environment = os.environ.copy()
    for name, prompt in (
        ("WORKOS_CLIENT_ID", "WorkOS test Client ID: "),
        ("WORKOS_REDIRECT_URI", "Registered callback URI for this server: "),
    ):
        value = environment.get(name) or input(prompt).strip()
        if not value:
            print(f"{name} is required.", file=sys.stderr)
            return 1
        environment[name] = value
    if not environment.get("WORKOS_API_KEY"):
        environment["WORKOS_API_KEY"] = getpass("WorkOS test API key (hidden): ").strip()
    if not environment["WORKOS_API_KEY"]:
        print("WORKOS_API_KEY is required.", file=sys.stderr)
        return 1
    environment.setdefault("WORKOS_COOKIE_PASSWORD", secrets.token_urlsafe(48))
    callback = urlsplit(environment["WORKOS_REDIRECT_URI"])
    if callback.scheme != "http" or callback.hostname not in {"localhost", "127.0.0.1"} or callback.port != 4000 or callback.path != "/auth/callback" or callback.query or callback.fragment:
        print("Use the registered local callback http://localhost:4000/auth/callback (or 127.0.0.1) for this port-4000 launcher.", file=sys.stderr)
        return 1
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    root = Path(__file__).resolve().parents[2]
    print("Starting UAD on port 4000. WorkOS credentials are passed only to the server process.", flush=True)
    try:
        return subprocess.run(
            [sys.executable, "-B", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "4000"],
            cwd=root, env=environment, check=False,
        ).returncode
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
