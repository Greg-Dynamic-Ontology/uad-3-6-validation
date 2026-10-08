"""User-account services for IT-2.

Both account kinds share the requirement that display_name contains
non-whitespace text. Additional user-data requirements can be added as
they are defined.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Mapping, Protocol


class UserAccountKind(StrEnum):
    SINGLE_USER = "single_user"
    COMPANY_USER = "company_user"


@dataclass(frozen=True)
class UserAccount:
    user_account_id: str
    user_data: Mapping[str, str]
    company_id: str | None
    account_kind: UserAccountKind


class UserAccountIdGenerator(Protocol):
    def new_user_account_id(self) -> str: ...


class UserAccountRepository(Protocol):
    def company_exists(self, company_id: str) -> bool: ...

    def add(self, user_account: UserAccount) -> None: ...


class UserAccountUpdateRepository(Protocol):
    """Retrieve and save an existing UAD account."""

    def get_by_id(self, user_account_id: str) -> UserAccount | None: ...

    def save(self, user_account: UserAccount) -> None: ...


class UserCompanyAssociationRepository(UserAccountUpdateRepository, Protocol):
    """Retrieve and save accounts and check company records."""

    def company_exists(self, company_id: str) -> bool: ...


def _validate_user_data(user_data: Mapping[str, str]) -> None:
    display_name = user_data.get("display_name")
    if not isinstance(display_name, str) or not display_name.strip():
        raise ValueError("display_name is required and must contain non-whitespace text.")


def create_user_account(
    user_data: Mapping[str, str],
    company_id: str | None,
    id_generator: UserAccountIdGenerator,
    account_repository: UserAccountRepository,
) -> UserAccount:
    """Create either account kind using the same user data and persistence.

    Company links are checked against existing records before account creation.
    """

    _validate_user_data(user_data)

    if company_id is not None and not account_repository.company_exists(company_id):
        raise ValueError(f"Company {company_id!r} does not exist.")

    account = UserAccount(
        user_account_id=id_generator.new_user_account_id(),
        user_data=dict(user_data),
        company_id=company_id,
        account_kind=(
            UserAccountKind.SINGLE_USER
            if company_id is None
            else UserAccountKind.COMPANY_USER
        ),
    )
    account_repository.add(account)
    return account


def update_user_account(
    user_account_id: str,
    user_data: Mapping[str, str],
    account_repository: UserAccountUpdateRepository,
) -> UserAccount:
    """Update shared user data while preserving identity and company membership.

    user_data supplies the complete replacement shared-data mapping.
    """
    _validate_user_data(user_data)
    existing = account_repository.get_by_id(user_account_id)
    if existing is None:
        raise ValueError(f"User account {user_account_id!r} does not exist.")

    updated = replace(existing, user_data=dict(user_data))
    account_repository.save(updated)
    return updated


def change_user_company(
    user_account_id: str,
    company_id: str | None,
    account_repository: UserCompanyAssociationRepository,
) -> UserAccount:
    """Change the company link while preserving account identity and user data."""
    existing = account_repository.get_by_id(user_account_id)
    if existing is None:
        raise ValueError(f"User account {user_account_id!r} does not exist.")
    if company_id is not None and not account_repository.company_exists(company_id):
        raise ValueError(f"Company {company_id!r} does not exist.")

    updated = replace(
        existing,
        company_id=company_id,
        account_kind=(
            UserAccountKind.SINGLE_USER
            if company_id is None
            else UserAccountKind.COMPANY_USER
        ),
    )
    account_repository.save(updated)
    return updated
