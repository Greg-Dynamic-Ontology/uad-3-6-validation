"""User-account services for IT-2.

Both account kinds share the requirement that display_name contains
non-whitespace text. Additional user-data requirements can be added as
they are defined.
"""

from __future__ import annotations

from dataclasses import dataclass
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
    def add(self, user_account: UserAccount) -> None: ...


def create_user_account(
    user_data: Mapping[str, str],
    company_id: str | None,
    id_generator: UserAccountIdGenerator,
    account_repository: UserAccountRepository,
) -> UserAccount:
    """Create either account kind using the same user data and persistence.

    For company-user creation, the caller supplies an existing company ID.
    Checking company existence is the separate IT-2R2 requirement.
    """

    display_name = user_data.get("display_name")
    if not isinstance(display_name, str) or not display_name.strip():
        raise ValueError("display_name is required and must contain non-whitespace text.")

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
