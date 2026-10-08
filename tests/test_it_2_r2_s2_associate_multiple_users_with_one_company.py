"""IT-2R2S2: two independent UAD accounts share one existing company.

Exercises the application service and persistence boundary, not WorkOS
authentication or database durability.
"""

from dataclasses import dataclass, field

from app.services.user_accounts import UserAccount, UserAccountKind, create_user_account


class UserAccountIdGeneratorStub:
    def __init__(self) -> None:
        self.identifiers = iter(("user-alex", "user-jordan"))

    def new_user_account_id(self) -> str:
        return next(self.identifiers)


@dataclass
class AccountRepositorySpy:
    companies: dict[str, str] = field(
        default_factory=lambda: {"company-1": "Example Appraisals"}
    )
    saved_accounts: list[UserAccount] = field(default_factory=list)

    def company_exists(self, company_id: str) -> bool:
        return company_id in self.companies

    def add(self, user_account: UserAccount) -> None:
        self.saved_accounts.append(user_account)


def test_it_2_r2_s2_associate_multiple_users_with_one_company() -> None:
    repository = AccountRepositorySpy()
    company_id = "company-1"
    original_companies = dict(repository.companies)
    assert repository.company_exists(company_id)
    id_generator = UserAccountIdGeneratorStub()
    alex_data = {"display_name": "Alex Example"}
    jordan_data = {"display_name": "Jordan Example"}

    alex = create_user_account(
        user_data=alex_data, company_id=company_id,
        id_generator=id_generator, account_repository=repository,
    )
    jordan = create_user_account(
        user_data=jordan_data, company_id=company_id,
        id_generator=id_generator, account_repository=repository,
    )

    assert len(repository.saved_accounts) == 2
    saved = {account.user_account_id: account for account in repository.saved_accounts}
    assert set(saved) == {"user-alex", "user-jordan"}
    assert saved["user-alex"] == alex
    assert saved["user-jordan"] == jordan
    assert alex is not jordan
    assert dict(saved["user-alex"].user_data) == {"display_name": "Alex Example"}
    assert dict(saved["user-jordan"].user_data) == {"display_name": "Jordan Example"}
    for account in saved.values():
        assert account.company_id == company_id
        assert account.account_kind is UserAccountKind.COMPANY_USER
        assert repository.companies[account.company_id] == "Example Appraisals"
    assert repository.companies == original_companies
    assert alex_data == {"display_name": "Alex Example"}
    assert jordan_data == {"display_name": "Jordan Example"}
