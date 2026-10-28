"""Durable customer-entry records and account-scoped cycle inventory.

Cycle lifecycle operations remain owned by validation_cycles. This adapter
provides account-entry persistence; it does not manufacture validation results.
"""

from contextlib import contextmanager
from pathlib import Path
import os
import sqlite3


def customer_store_path() -> Path:
    configured = os.environ.get("UAD_CUSTOMER_STORE")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[2] / "data" / "customer-validation.sqlite3"


class CustomerValidationStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = (path or customer_store_path()).resolve()

    @contextmanager
    def connection(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS entry_users (
                    user_account_id TEXT PRIMARY KEY,
                    workos_user_id TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    internal_phone_number TEXT NOT NULL,
                    phone_verified INTEGER NOT NULL CHECK (phone_verified IN (0, 1))
                );
                CREATE TABLE IF NOT EXISTS entry_accounts (
                    customer_account_id TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    active INTEGER NOT NULL CHECK (active IN (0, 1))
                );
                CREATE TABLE IF NOT EXISTS entry_memberships (
                    customer_account_id TEXT NOT NULL REFERENCES entry_accounts,
                    user_account_id TEXT NOT NULL REFERENCES entry_users,
                    role TEXT NOT NULL,
                    active INTEGER NOT NULL CHECK (active IN (0, 1)),
                    PRIMARY KEY (customer_account_id, user_account_id, role)
                );
                CREATE TABLE IF NOT EXISTS account_validation_cycles (
                    validation_cycle_id TEXT PRIMARY KEY,
                    customer_account_id TEXT NOT NULL REFERENCES entry_accounts,
                    state TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS entry_audit (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    customer_account_id TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    effective_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def user_for_identity(self, workos_user_id: str) -> dict | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM entry_users WHERE workos_user_id = ?", (workos_user_id,),
            ).fetchone()
            return dict(row) if row is not None else None

    def accounts_for_user(self, user_account_id: str) -> list[dict]:
        with self.connection() as connection:
            rows = connection.execute("""
                SELECT a.customer_account_id, a.label, m.role
                FROM entry_accounts a JOIN entry_memberships m
                  ON a.customer_account_id = m.customer_account_id
                WHERE m.user_account_id = ? AND a.active = 1 AND m.active = 1
                ORDER BY a.label, a.customer_account_id, m.role
            """, (user_account_id,)).fetchall()
        accounts = {}
        for row in rows:
            account = accounts.setdefault(row["customer_account_id"], {
                "customer_account_id": row["customer_account_id"],
                "label": row["label"], "roles": [],
            })
            account["roles"].append(row["role"])
        return list(accounts.values())

    def cycles_for_account(self, customer_account_id: str) -> list[dict]:
        with self.connection() as connection:
            return [dict(row) for row in connection.execute(
                "SELECT validation_cycle_id, state FROM account_validation_cycles "
                "WHERE customer_account_id = ? ORDER BY validation_cycle_id",
                (customer_account_id,),
            ).fetchall()]
