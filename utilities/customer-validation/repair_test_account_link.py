"""Repair only the known IT-64 development identity link and profile hostname.

Preview by default. Stop the development server before using --apply.
No credentials, WorkOS changes, new accounts, or validation cycles are created.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys

WORKOS_USER = "user_01M64GJ8EK0PKDZXZR767W1Y8P"
HOSTNAME = "intelligent-silk-36-sandbox.authkit.app"
LOCAL_USER = "user-4836ddcea29040fea725e1944d5eb2b1"
ACCOUNT = "customer-d72bc78198a4453ea10c5369c14a087e"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--store", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    profile_path = root / "tests/fixtures/it_64/r1/s1/customer-profile.json"
    store_path = (args.store or root / "data/customer-validation.sqlite3").resolve()
    original = profile_path.read_bytes()
    profile = json.loads(original.decode("utf-8-sig"))
    if profile.get("user_account_id") != LOCAL_USER or profile.get("customer_account_id") != ACCOUNT:
        raise ValueError("Profile does not identify the reviewed test user/account; nothing changed.")
    connection = sqlite3.connect(store_path.as_uri() + "?mode=rw", uri=True)
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT workos_user_id, display_name FROM entry_users WHERE user_account_id = ?",
            (LOCAL_USER,),
        ).fetchone()
        if row is None or not (row[0].startswith("client_") or row[0] == WORKOS_USER):
            raise ValueError("Existing identity is not the known Client-ID mistake or repaired identity.")
        if row[1] != profile.get("display_name"):
            raise ValueError("Profile display name disagrees with the stored user.")
        collision = connection.execute(
            "SELECT user_account_id FROM entry_users WHERE workos_user_id = ? AND user_account_id <> ?",
            (WORKOS_USER, LOCAL_USER),
        ).fetchone()
        if collision:
            raise ValueError("WorkOS identity already belongs to another local user; nothing changed.")
        membership = connection.execute(
            "SELECT 1 FROM entry_memberships m JOIN entry_accounts a "
            "ON a.customer_account_id=m.customer_account_id "
            "WHERE m.user_account_id=? AND m.customer_account_id=? "
            "AND m.role='validator' AND m.active=1 AND a.active=1",
            (LOCAL_USER, ACCOUNT),
        ).fetchone()
        if membership is None:
            raise ValueError("Expected active validation membership is missing; nothing changed.")
        cycle_ids = {r[0] for r in connection.execute(
            "SELECT validation_cycle_id FROM account_validation_cycles WHERE customer_account_id=?",
            (ACCOUNT,),
        )}
        if cycle_ids != set(profile.get("preexisting_cycle_ids", [])):
            raise ValueError("Cycle inventory differs from the profile baseline; review before repair.")
        print(f"Store: {store_path}")
        print(f"Profile: {profile_path}")
        print(f"Existing link: {row[0]}")
        print(f"Correct WorkOS user: {WORKOS_USER}")
        print(f"Hosted sign-in hostname: {HOSTNAME}")
        changed = row[0] != WORKOS_USER or profile.get("hosted_sign_in_hostname") != HOSTNAME
        if not changed:
            print("Already repaired. No files or records changed.")
            return
        if not args.apply:
            print("Preview only. Stop the development server, then run with --apply.")
            return
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup_dir = store_path.parent / "it64-setup-backups" / stamp
        backup_dir.mkdir(parents=True, exist_ok=False)
        # Use SQLite's backup API to include committed WAL contents correctly.
        with sqlite3.connect(store_path.as_uri() + "?mode=ro", uri=True) as source:
            with sqlite3.connect(backup_dir / store_path.name) as backup:
                source.backup(backup)
        (backup_dir / profile_path.name).write_bytes(original)
        connection.execute(
            "UPDATE entry_users SET workos_user_id=? WHERE user_account_id=?",
            (WORKOS_USER, LOCAL_USER),
        )
        connection.execute(
            "INSERT INTO entry_audit(event_type,customer_account_id,actor_id) VALUES(?,?,?)",
            ("test_workos_identity_link_repaired", ACCOUNT, LOCAL_USER),
        )
        profile["hosted_sign_in_hostname"] = HOSTNAME
        replacement = profile_path.with_suffix(".json.repair-tmp")
        try:
            replacement.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
            replacement.replace(profile_path)
            connection.commit()
        except Exception:
            connection.rollback()
            profile_path.write_bytes(original)
            raise
        print(f"Repair saved. Backups: {backup_dir}")
        print("Local user/account IDs, names, phone, permissions, and cycles preserved.")
        print("Real hosted sign-in and email verification are still required.")
    finally:
        connection.rollback()
        connection.close()


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, sqlite3.Error) as error:
        print(f"Repair stopped: {error}", file=sys.stderr)
        sys.exit(1)
