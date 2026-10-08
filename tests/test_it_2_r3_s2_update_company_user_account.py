"""IT-2R3S2: update shared user data and preserve the existing company link.

Exercises the application service's persistence boundary, not WorkOS or
database durability.
"""

from dataclasses import dataclass, field

from app.services.user_accounts import UserAccount, UserAccountKind, update_user_account


@dataclass
class UserAccountRepositorySpy:
    accounts: dict[str, UserAccount]
    companies: dict[str, str]
    saved_accounts: list[UserAccount] = field(default_factory=list)

    def get_by_id(self, user_account_id: str) -> UserAccount | None:
        return self.accounts.get(user_account_id)

    def save(self, user_account: UserAccount) -> None:
        assert user_account.user_account_id in self.accounts
        self.accounts[user_account.user_account_id] = user_account
        self.saved_accounts.append(user_account)


def test_it_2_r3_s2_update_company_user_account() -> None:
    existing = UserAccount(
        user_account_id="company-user-1",
        user_data={"display_name": "Alex Example"},
        company_id="company-1",
        account_kind=UserAccountKind.COMPANY_USER,
    )
    repository = UserAccountRepositorySpy(
        accounts={existing.user_account_id: existing},
        companies={"company-1": "Example Appraisals", "company-2": "Other Appraisals"},
    )
    original_companies = dict(repository.companies)
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
    assert set(repository.accounts) == {"company-user-1"}
    assert repository.get_by_id("company-user-1") == saved
    assert saved.user_account_id == existing.user_account_id
    assert dict(saved.user_data) == {"display_name": "Alex Updated"}
    assert saved.company_id == existing.company_id == "company-1"
    assert saved.account_kind is UserAccountKind.COMPANY_USER
    assert repository.companies == original_companies
    assert replacement_data == {"display_name": "Alex Updated"}
