"""IT-2R1S1: create and save a single-user account.

Tests the application service's persistence boundary using a repository spy.
It does not claim database durability or define shared field validation.
"""

from dataclasses import dataclass, field

from app.services.user_accounts import (
    UserAccount,
    UserAccountKind,
    create_user_account,
)


class UserAccountIdGeneratorStub:
    def new_user_account_id(self) -> str:
        return "user-account-1"


@dataclass
class UserAccountRepositorySpy:
    saved_accounts: list[UserAccount] = field(default_factory=list)

    def add(self, user_account: UserAccount) -> None:
        self.saved_accounts.append(user_account)


def test_it_2_r1_s1_create_single_user_account() -> None:
    # Representative supplied data, not a declaration of mandatory fields.
    user_data = {"display_name": "Alex Example"}
    original_data = dict(user_data)
    repository = UserAccountRepositorySpy()

    account = create_user_account(
        user_data=user_data,
        company_id=None,
        id_generator=UserAccountIdGeneratorStub(),
        account_repository=repository,
    )

    assert isinstance(account, UserAccount)
    assert len(repository.saved_accounts) == 1
    saved = repository.saved_accounts[0]
    assert saved == account
    assert saved.user_account_id == "user-account-1"
    assert dict(saved.user_data) == original_data
    assert saved.company_id is None
    assert saved.account_kind is UserAccountKind.SINGLE_USER
    assert user_data == original_data, "Creation changed the caller's user data."
