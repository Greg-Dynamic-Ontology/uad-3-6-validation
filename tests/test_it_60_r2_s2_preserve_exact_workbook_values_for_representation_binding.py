"""IT-60R2S2: compare representation bindings with exact workbook values."""

from __future__ import annotations

from pathlib import Path

from app.services import gse_constraint_sources
from app.services import representation_restriction_required_data


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIGURATION_PATH = PROJECT_ROOT / "config" / "configuration.ttl"


def test_it_60_r2_s2_checks_representation_bindings_against_exact_workbook_values() -> None:
    source = gse_constraint_sources.read_active_compliance_workbook_rows(
        configuration_path=CONFIGURATION_PATH,
    )
    bindings = representation_restriction_required_data.load_bindings()
    bound_rows = [
        row
        for row in source.rows
        if row.get("Message ID") in bindings
    ]

    assert bound_rows, (
        "The active governed workbook must contain at least one row with a "
        "configured representation binding."
    )

    checked_message_ids: list[str] = []
    for row in bound_rows:
        message_id = row["Message ID"]
        assert isinstance(row.get("Unique ID"), str), (
            f"{message_id}: the workbook identifier must remain text."
        )
        assert (
            representation_restriction_required_data.fingerprint(row)
            == bindings[message_id]["sourceFingerprint"]
        ), (
            f"{message_id}: the binding fingerprint must be calculated from "
            "the exact active-workbook source values."
        )
        resolved_binding = (
            representation_restriction_required_data.binding_for(row)
        )
        assert resolved_binding == bindings[message_id], (
            f"{message_id}: the exact workbook row must resolve to its "
            "configured representation binding."
        )
        checked_message_ids.append(message_id)

    assert checked_message_ids, (
        "At least one configured representation binding must be checked "
        "against an active-workbook row."
    )
