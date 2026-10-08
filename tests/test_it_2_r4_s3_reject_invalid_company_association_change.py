"""IT-2R4S3: reject a nonexistent company without changing the account."""

from dataclasses import dataclass, field

import pytest

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
        self.accounts[user_account.user_account_id] = user_account
        self.saved_accounts.append(user_account)


def test_it_2_r4_s3_reject_invalid_company_association_change() -> None:
    original_data = {"display_name": "Alex Example"}
    existing = UserAccount(
        user_account_id="user-1",
        user_data=dict(original_data),
        company_id="company-1",
        account_kind=UserAccountKind.COMPANY_USER,
    )
    repository = AccountRepositorySpy(
        accounts={"user-1": existing},
        companies={"company-1": "Example Appraisals"},
    )
    original_companies = dict(repository.companies)
    assert not repository.company_exists("company-missing")

    with pytest.raises(ValueError, match="(?i)company.*does not exist"):
        change_user_company(
            user_account_id="user-1",
            company_id="company-missing",
            account_repository=repository,
        )

    assert repository.saved_accounts == []
    assert set(repository.accounts) == {"user-1"}
    preserved = repository.get_by_id("user-1")
    assert preserved is not None
    assert preserved.user_account_id == "user-1"
    assert preserved.company_id == "company-1"
    assert preserved.account_kind is UserAccountKind.COMPANY_USER
    assert dict(preserved.user_data) == original_data
    assert repository.companies == original_companies
