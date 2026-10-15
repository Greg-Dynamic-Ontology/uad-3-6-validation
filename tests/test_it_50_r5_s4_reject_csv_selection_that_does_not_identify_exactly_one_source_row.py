"""IT-50R5S4: reject CSV selections that identify zero or multiple rows."""

from __future__ import annotations

import csv
import uuid
from pathlib import Path

import pytest

from app.services.governed_constraint_source_reader import (
    read_governed_constraint_row_from_csv,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GOVERNED_CSV = PROJECT_ROOT / "data" / "data-constraints.csv"


def read_governed_csv() -> tuple[list[str], list[list[str]]]:
    assert GOVERNED_CSV.is_file(), (
        "The governed source CSV is missing: "
        f"{GOVERNED_CSV}"
    )

    with GOVERNED_CSV.open("r", encoding="utf-8-sig", newline="") as source_file:
        reader = csv.reader(source_file)
        headers = next(reader, None)
        assert headers is not None, "The governed source CSV is empty."
        rows = list(reader)

    assert rows, "The governed source CSV has no data rows."
    return headers, rows


@pytest.mark.parametrize(
    ("matching_rows", "reason"),
    [
        (0, "no matching governed source row"),
        (2, "multiple matching governed rows"),
    ],
)
def test_it_50_r5_s4_rejects_csv_selection_that_does_not_identify_exactly_one_source_row(
    tmp_path: Path,
    matching_rows: int,
    reason: str,
) -> None:
    headers, source_rows = read_governed_csv()
    unique_id_column = headers.index("Unique ID")

    if matching_rows == 0:
        existing_ids = {row[unique_id_column] for row in source_rows}
        selected_unique_id = f"__missing__{uuid.uuid4().hex}"
        while selected_unique_id in existing_ids:
            selected_unique_id = f"__missing__{uuid.uuid4().hex}"

        csv_path = GOVERNED_CSV
    else:
        selected_row = source_rows[0]
        selected_unique_id = selected_row[unique_id_column]
        csv_path = tmp_path / GOVERNED_CSV.name

        with csv_path.open("w", encoding="utf-8", newline="") as output_file:
            writer = csv.writer(output_file)
            writer.writerow(headers)
            writer.writerow(selected_row)
            writer.writerow(selected_row)

    with pytest.raises(ValueError) as raised:
        read_governed_constraint_row_from_csv(
            csv_path=csv_path,
            unique_id=selected_unique_id,
        )

    message = str(raised.value).lower()
    assert "row" in message, (
        f"The reader should explain that the selection identifies {reason}; "
        f"got: {raised.value}"
    )

    if matching_rows == 0:
        assert "no" in message or "found" in message, (
            "The reader should explain that no governed source row matched; "
            f"got: {raised.value}"
        )
    else:
        assert "multiple" in message or "more than one" in message, (
            "The reader should explain that multiple governed rows matched; "
            f"got: {raised.value}"
        )