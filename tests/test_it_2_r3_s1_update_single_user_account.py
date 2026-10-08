"""IT-2R3S1: save updated user data without changing account identity or company.

Exercises the service persistence boundary with an existing stored account.
"""

from dataclasses import dataclass, field

from app.services.user_accounts import UserAccount, UserAccountKind, update_user_account


@dataclass
class UserAccountRepositorySpy:
    accounts: dict[str, UserAccount]
    saved_accounts: list[UserAccount] = field(default_factory=list)

    def get_by_id(self, user_account_id: str) -> UserAccount | None:
        return self.accounts.get(user_account_id)

    def save(self, user_account: UserAccount) -> None:
        assert user_account.user_account_id in self.accounts
        self.accounts[user_account.user_account_id] = user_account
        self.saved_accounts.append(user_account)


def test_it_2_r3_s1_update_single_user_account() -> None:
    existing = UserAccount(
        user_account_id="user-account-1",
        user_data={"display_name": "Alex Example"},
        company_id=None,
        account_kind=UserAccountKind.SINGLE_USER,
    )
    repository = UserAccountRepositorySpy(accounts={existing.user_account_id: existing})
    replacement_data = {"display_name": "Alex Updated"}

    result = update_user_account(
        user_account_id=existing.user_account_id,
        user_data=replacement_data,
        account_repository=repository,
    )

    assert len(repository.saved_accounts) == 1
    saved = repository.saved_accounts[0]
    assert isinstance(saved, UserAccount)
    assert result == saved
    assert set(repository.accounts) == {"user-account-1"}
    assert repository.get_by_id("user-account-1") == saved
    assert saved.user_account_id == existing.user_account_id
    assert dict(saved.user_data) == {"display_name": "Alex Updated"}
    assert saved.company_id is None
    assert saved.account_kind is UserAccountKind.SINGLE_USER
    assert replacement_data == {"display_name": "Alex Updated"}
