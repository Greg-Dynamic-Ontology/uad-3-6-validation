"""Configure WorkOS and check availability before running regression tests."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def main() -> int:
    project_root = Path(__file__).resolve().parent
    environment = os.environ.copy()

    print(f"WorkOS test launcher: {Path(__file__).resolve()}", flush=True)

    for name, description in (
        ("WORKOS_CLIENT_ID", "WorkOS staging Client ID"),
        ("WORKOS_REDIRECT_URI", "Registered WorkOS Redirect URI"),
    ):
        value = environment.get(name, "").strip()

        if not value:
            value = input(f"{description}: ").strip()

        if not value:
            print(f"ERROR: {name} is blank.", file=sys.stderr)
            return 1

        environment[name] = value
        print(f"{name}: configured", flush=True)

    focused_arguments = [
        "tests/test_it_2_r5_s1_workos_authkit_availability.py",
        "-q",
        "--tb=short",
        "-p",
        "no:cacheprovider",
    ]

    print("\nChecking hosted WorkOS availability first...", flush=True)

    focused_result = subprocess.run(
        [sys.executable, "-B", "-m", "pytest", *focused_arguments],
        cwd=project_root,
        env=environment,
        check=False,
    )

    if focused_result.returncode != 0:
        print(
            "\nWorkOS check failed. Full regression was not started.",
            flush=True,
        )
        return focused_result.returncode

    if not sys.argv[1:]:
        return 0

    print("\nWorkOS check passed. Starting requested tests...", flush=True)

    regression_result = subprocess.run(
        [sys.executable, "-B", "-m", "pytest", *sys.argv[1:]],
        cwd=project_root,
        env=environment,
        check=False,
    )
    return regression_result.returncode


if __name__ == "__main__":
    raise SystemExit(main())