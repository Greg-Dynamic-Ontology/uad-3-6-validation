"""IT-2R4S1: associate an existing single-user account with a company.

Checks the local application service and persistence boundary, not WorkOS.
"""

from dataclasses import dataclass, field

from app.services.user_accounts import UserAccount, UserAccountKind, change_user_company


@dataclass
class AccountRepositorySpy:
    accounts: dict[str, UserAccount]
    companies: dict[str, str]
    saved_accounts: list[UserAccount] = field(default_factory=list)

    def get_by_id(self, user_account_id: str) -> UserAccount | None:
        return self.accounts.get(user_account_id)

    def company_exists(self, company_id: str) -> bool:
        return company_id in self.companies

    def save(self, user_account: UserAccount) -> None:
        assert user_account.user_account_id in self.accounts
        self.accounts[user_account.user_account_id] = user_account
        self.saved_accounts.append(user_account)


def test_it_2_r4_s1_associate_single_user_with_company() -> None:
    original_data = {"display_name": "Alex Example"}
    existing = UserAccount(
        user_account_id="user-1",
        user_data=dict(original_data),
        company_id=None,
        account_kind=UserAccountKind.SINGLE_USER,
    )
    repository = AccountRepositorySpy(
        accounts={"user-1": existing},
        companies={"company-1": "Example Appraisals", "company-2": "Other Appraisals"},
    )
    original_companies = dict(repository.companies)
    assert repository.company_exists("company-1")

    result = change_user_company(
        user_account_id="user-1",
        company_id="company-1",
        account_repository=repository,
    )

    assert len(repository.saved_accounts) == 1
    saved = repository.saved_accounts[0]
    assert isinstance(saved, UserAccount)
    assert result == saved
    assert repository.get_by_id("user-1") == saved
    assert set(repository.accounts) == {"user-1"}
    assert saved.user_account_id == existing.user_account_id
    assert saved.company_id == "company-1"
    assert saved.account_kind is UserAccountKind.COMPANY_USER
    assert dict(saved.user_data) == original_data
    assert repository.companies == original_companies
