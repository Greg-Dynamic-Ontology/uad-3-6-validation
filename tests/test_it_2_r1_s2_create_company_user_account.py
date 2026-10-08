"""IT-2R1S2: save a user account linked to an existing company.

The repository spy supplies the existing-company precondition. This tests
the service persistence boundary, not database durability or rejection of
nonexistent companies (IT-2R2).
"""

from dataclasses import dataclass, field

from app.services.user_accounts import (
    UserAccount,
    UserAccountKind,
    create_user_account,
)


@dataclass(frozen=True)
class CompanyRecord:
    company_id: str
    name: str


class UserAccountIdGeneratorStub:
    def new_user_account_id(self) -> str:
        return "company-user-account-1"


@dataclass
class AccountRepositorySpy:
    companies: dict[str, CompanyRecord]
    saved_accounts: list[UserAccount] = field(default_factory=list)

    def add(self, user_account: UserAccount) -> None:
        self.saved_accounts.append(user_account)


def test_it_2_r1_s2_create_company_user_account() -> None:
    # Use the same representative user-data shape as the single-user case.
    # This example does not declare which fields are mandatory.
    user_data = {"display_name": "Alex Example"}
    original_data = dict(user_data)
    company = CompanyRecord("company-1", "Example Appraisals")
    repository = AccountRepositorySpy(companies={company.company_id: company})
    original_companies = dict(repository.companies)
    assert repository.companies[company.company_id] == company

    account = create_user_account(
        user_data=user_data,
        company_id=company.company_id,
        id_generator=UserAccountIdGeneratorStub(),
        account_repository=repository,
    )

    assert isinstance(account, UserAccount)
    assert len(repository.saved_accounts) == 1
    saved = repository.saved_accounts[0]
    assert saved == account
    assert saved.user_account_id == "company-user-account-1"
    assert dict(saved.user_data) == original_data
    assert saved.company_id == company.company_id
    assert repository.companies[saved.company_id] == company
    assert saved.account_kind is UserAccountKind.COMPANY_USER
    assert user_data == original_data, "Creation changed the caller's user data."
    assert repository.companies == original_companies
