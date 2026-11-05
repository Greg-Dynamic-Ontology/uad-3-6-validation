"""Provision explicitly synthetic credits for the dedicated local IT-64 test.

This utility does not represent a purchase or completed payment. Never use it
on a production store. A deliberate development-data acknowledgement is required.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--quantity", type=int, default=2, help="Required available test credits (default: two live submission tests).")
    args = parser.parse_args()
    if not 1 <= args.quantity <= 10:
        parser.error("--quantity must be between 1 and 10")
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root))
    from app.services.account_cycle_validation import CycleStore

    profile = json.loads((root / "tests/fixtures/it_64/r1/s1/customer-profile.json").read_text(encoding="utf-8-sig"))
    store = CycleStore()
    account_id, user_id = profile["customer_account_id"], profile["user_account_id"]
    print(f"DEVELOPMENT TEST DATA ONLY. Store: {store.store.path}")
    print(f"Account from the IT-64 test profile: {account_id}")
    print("Synthetic test credits; no money or WorkOS settings are changed.")
    if not args.apply:
        print("Preview only. To provision, run with --apply.")
        return
    if input("Confirm this is the dedicated local development test store (type DEVELOPMENT TEST DATA): ").strip() != "DEVELOPMENT TEST DATA":
        raise ValueError("No test credit provisioned.")
    # Take a SQLite-consistent backup before initializing new cycle tables.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = store.store.path.parent / "it64-setup-backups" / stamp
    backup.mkdir(parents=True)
    with sqlite3.connect(store.store.path.as_uri() + "?mode=ro", uri=True) as source:
        with sqlite3.connect(backup / store.store.path.name) as target:
            source.backup(target)
    store.initialize()
    with store.store.connection() as db:
        db.execute("BEGIN IMMEDIATE")
        membership = db.execute("SELECT 1 FROM entry_memberships WHERE customer_account_id=? AND user_account_id=? AND role='validator' AND active=1", (account_id, user_id)).fetchone()
        if not membership:
            raise ValueError("The profile does not identify an active test validator membership.")
        available = db.execute("SELECT COALESCE(SUM(remaining),0) FROM cv_credit_lots WHERE account_id=?", (account_id,)).fetchone()[0]
        if available >= args.quantity:
            print(f"Account already has {available} available credits. No credits added.")
            return
        quantity = args.quantity - available
        lot_id = "development-test-" + uuid4().hex
        db.execute("INSERT INTO cv_credit_lots VALUES(?,?,?,?)", (lot_id, account_id, "SYNTHETIC-TEST-NOT-A-PAYMENT", quantity))
        db.execute("INSERT INTO cv_credit_history(document) VALUES(?)", (json.dumps({
            "event_type": "development_test_credit_provisioned", "customer_account_id": account_id,
            "actor_id": user_id, "quantity": quantity, "validation_credit_lot_id": lot_id,
            "synthetic_test_data": True, "effective_at": datetime.now(timezone.utc).isoformat(),
        }),))
    print(f"Development test credits provisioned. Backup: {backup}")


if __name__ == "__main__":
    main()
