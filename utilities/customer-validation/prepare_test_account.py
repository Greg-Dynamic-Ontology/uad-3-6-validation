"""Provision durable IT-64 test-account preconditions for a real WorkOS user.

This local development utility is not a public registration or phone-verification
endpoint. The operator must supply an existing WorkOS identity and attest that
the test person's phone has already been verified. It creates no WorkOS users,
sessions, passwords, credits, reports, or validation cycles.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import sys
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.adapters.customer_validation_store import CustomerValidationStore
from app.services.customer_accounts import create_customer_account
from app.services.user_accounts import create_user_account
from app.services.operating_modes import (
    OperatingMode, is_designated_developer_phone_number,
)


def required(prompt: str) -> str:
    value = input(prompt).strip()
    if not value:
        raise ValueError("All test-account details are required.")
    return value


@dataclass
class _Applicant:
    human_user_id: str
    internal_phone_number: str
    phone_number_verified: bool = True
    eligible_to_create_customer_account: bool = True


class _Identifiers:
    def new_user_account_id(self):
        return "user-" + uuid4().hex

    def new_customer_account_id(self):
        return "customer-" + uuid4().hex


def main() -> int:
    print("Prepare a dedicated, already verified real WorkOS test identity.")
    print("This records local test preconditions; hosted sign-in must still authenticate the identity.")
    try:
        workos_id = required("Existing WorkOS user ID: ")
        name = required("Test user display name: ")
        phone = required("Already verified internal phone number (11 digits, starting with 1): ")
        if len(phone) != 11 or not phone.isascii() or not phone.isdigit() or not phone.startswith("1"):
            raise ValueError("Use an already verified 11-digit country-code-1 test phone number.")
        if required("Confirm the test phone is already verified (type YES): ") != "YES":
            raise ValueError("Phone verification is a prerequisite.")
        label = required("Customer account label: ")
        hosted_hostname = required("Hosted WorkOS sign-in hostname (hostname only): ")
        if any(character in hosted_hostname for character in "/: "):
            raise ValueError("Enter the hosted sign-in hostname without a scheme or path.")
        profile_path = PROJECT_ROOT / "tests" / "fixtures" / "it_64" / "r1" / "s1" / "customer-profile.json"
        if profile_path.exists():
            previous = json.loads(profile_path.read_text(encoding="utf-8-sig"))
            is_template = (
                str(previous.get("user_account_id", "")).startswith("REPLACE_")
                and str(previous.get("customer_account_id", "")).startswith("REPLACE_")
            )
            if not is_template:
                raise ValueError(f"A completed profile already exists; it was not overwritten: {profile_path}")
        store = CustomerValidationStore()
        if store.user_for_identity(workos_id) is not None:
            raise ValueError("That WorkOS identity is already registered locally; its records were not replaced.")
        identifiers = _Identifiers()
        with store.connection() as connection:
            class UserRepository:
                def company_exists(self, company_id):
                    return False

                def add(self, user):
                    connection.execute(
                        "INSERT INTO entry_users VALUES (?, ?, ?, ?, 1)",
                        (user.user_account_id, workos_id, name, phone),
                    )

            class AccountRepository:
                def add(self, account):
                    connection.execute("INSERT INTO entry_accounts VALUES (?, ?, 1)", (account.customer_account_id, label))
                    for membership in account.memberships:
                        connection.execute(
                            "INSERT INTO entry_memberships VALUES (?, ?, ?, 1)",
                            (account.customer_account_id, membership.human_user_id, membership.role.value),
                        )

            class Audit:
                def record(self, **event):
                    connection.execute(
                        "INSERT INTO entry_audit (event_type, customer_account_id, actor_id) VALUES (?, ?, ?)",
                        (event["event_type"], event["customer_account_id"], event["actor_id"]),
                    )

            user = create_user_account(
                user_data={"display_name": name}, company_id=None,
                id_generator=identifiers, account_repository=UserRepository(),
            )
            account = create_customer_account(
                _Applicant(user.user_account_id, phone), identifiers, AccountRepository(), Audit(),
            )
            # The existing authorization policy separates ownership and validation.
            connection.execute(
                "INSERT INTO entry_memberships VALUES (?, ?, 'validator', 1)",
                (account.customer_account_id, user.user_account_id),
            )
            Audit().record(event_type="test_validator_membership_registered", customer_account_id=account.customer_account_id, actor_id=user.user_account_id)
        profile = {
            "user_account_id": user.user_account_id,
            "display_name": name,
            "customer_account_id": account.customer_account_id,
            "customer_account_label": label,
            "operating_mode": "developer" if is_designated_developer_phone_number(phone) else "standard",
            "hosted_sign_in_hostname": hosted_hostname,
            "preexisting_cycle_ids": [],
        }
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
        print(f"Durable store: {store.path}")
        print(f"Test profile: {profile_path}")
        print(f"UAD user: {user.user_account_id}")
        print(f"Customer account: {account.customer_account_id}")
        print("No validation cycle was created.")
        return 0
    except (ValueError, OSError) as error:
        print(f"Test-account setup failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
