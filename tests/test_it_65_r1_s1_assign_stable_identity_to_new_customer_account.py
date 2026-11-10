"""IT-65R1S1: assign an account identity independent of its owner.

Service-level test: authentication/linking are supplied prerequisites;
repository and audit doubles exercise the existing service boundaries.
"""

from copy import deepcopy
from dataclasses import dataclass, field

import app.services.customer_accounts as accounts


@dataclass(frozen=True)
class AuthenticatedApplicant:
    human_user_id: str = "uad-user-it65-owner"
    workos_user_id: str = "user_it65_workos_owner"
    internal_phone_number: str = "19999999999"
    phone_number_verified: bool = True
    eligible_to_create_customer_account: bool = True


@dataclass
class AccountRepository:
    """Snapshot aggregates so assertions cannot pass through shared mutation."""

    records: dict = field(default_factory=dict)
    added_ids: list = field(default_factory=list)
    saved_ids: list = field(default_factory=list)

    def add(self, customer_account):
        identifier = customer_account.customer_account_id
        assert identifier not in self.records, "Account creation issued a duplicate ID."
        self.records[identifier] = deepcopy(customer_account)
        self.added_ids.append(identifier)

    def save(self, customer_account):
        identifier = customer_account.customer_account_id
        assert identifier in self.records, "An information update must preserve an existing account ID."
        self.records[identifier] = deepcopy(customer_account)
        self.saved_ids.append(identifier)

    def get(self, customer_account_id):
        return deepcopy(self.records[customer_account_id])


@dataclass
class AuditHistory:
    events: list = field(default_factory=list)

    def record(self, **event):
        self.events.append(dict(event))


def test_it_65_r1_s1_assign_stable_identity_to_new_customer_account():
    generator_type = getattr(accounts, "UniqueCustomerAccountIdGenerator", None)
    assert callable(generator_type), (
        "IT-65R1S1 requires UniqueCustomerAccountIdGenerator implementing "
        "new_customer_account_id(), independent of owner identity."
    )
    update = getattr(accounts, "update_customer_account_information", None)
    assert callable(update), (
        "IT-65R1S1 requires update_customer_account_information(customer_account=..., "
        "display_name=..., actor_id=..., account_repository=..., audit_history=...) "
        "to preserve account identity when account information changes."
    )
    owner = AuthenticatedApplicant()
    repository = AccountRepository()
    audit = AuditHistory()

    # Separate generator instances must not restart an ID sequence. The same
    # owner may own distinct accounts; neither identity can serve as account ID.
    first = accounts.create_customer_account(owner, generator_type(), repository, audit)
    second = accounts.create_customer_account(owner, generator_type(), repository, audit)
    first_id = first.customer_account_id
    second_id = second.customer_account_id
    assert isinstance(first_id, str) and first_id.strip()
    assert isinstance(second_id, str) and second_id.strip()
    assert first_id != second_id, "Distinct accounts must receive distinct IDs."
    for identifier in (first_id, second_id):
        assert identifier not in {owner.human_user_id, owner.workos_user_id}, (
            "An account ID must be separate from both the owner's UAD and WorkOS IDs."
        )
    assert repository.get(first_id).customer_account_id == first_id
    assert repository.get(second_id).customer_account_id == second_id
    original_memberships = deepcopy(first.memberships)
    untouched_second = repository.get(second_id)
    events_before_update = len(audit.events)

    # The owner is authorized through the active owner membership created by
    # the existing service. Exercise real updates, not dataclass replacement in
    # the test, and reload the aggregate between changes.
    for display_name in ("First account name", "Renamed account"):
        updated = update(
            customer_account=repository.get(first_id),
            display_name=display_name,
            actor_id=owner.human_user_id,
            account_repository=repository,
            audit_history=audit,
        )
        assert updated.customer_account_id == first_id
        assert updated.display_name == display_name
        persisted = repository.get(first_id)
        assert persisted.customer_account_id == first_id
        assert persisted.display_name == display_name
        assert persisted.memberships == original_memberships

    assert repository.added_ids == [first_id, second_id]
    assert repository.saved_ids == [first_id, first_id]
    assert set(repository.records) == {first_id, second_id}
    assert repository.get(second_id) == untouched_second
    update_events = audit.events[events_before_update:]
    assert len(update_events) >= 2, "Both account-information changes must be attributable."
    assert all(
        event.get("customer_account_id") == first_id
        and event.get("actor_id") == owner.human_user_id
        for event in update_events
    )
