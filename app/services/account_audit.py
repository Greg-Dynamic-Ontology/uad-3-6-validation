"""Immutable attribution records for material customer-account actions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol


class MaterialActionOutcome(StrEnum):
    """Possible outcomes recorded for a material account action."""

    ACCEPTED = "accepted"
    DENIED = "denied"


@dataclass(frozen=True)
class MaterialAccountActionRecord:
    """Historical attribution independent of current membership state."""

    customer_account_id: str
    actor_id: str
    action: str
    outcome: MaterialActionOutcome
    effective_time: datetime
    affected_resource_id: str | None = None


class EffectiveTimeClock(Protocol):
    def now(self) -> datetime: ...


class AccountAuditRepository(Protocol):
    def add(self, record: MaterialAccountActionRecord) -> None: ...


def record_material_account_action(
    customer_account_id: str,
    actor_id: str,
    action: str,
    outcome: MaterialActionOutcome,
    clock: EffectiveTimeClock,
    audit_repository: AccountAuditRepository,
    affected_resource_id: str | None = None,
) -> MaterialAccountActionRecord:
    """Append an immutable account-and-actor-attributed action record."""

    record = MaterialAccountActionRecord(
        customer_account_id=customer_account_id,
        actor_id=actor_id,
        action=action,
        outcome=outcome,
        effective_time=clock.now(),
        affected_resource_id=affected_resource_id,
    )
    audit_repository.add(record)
    return record
