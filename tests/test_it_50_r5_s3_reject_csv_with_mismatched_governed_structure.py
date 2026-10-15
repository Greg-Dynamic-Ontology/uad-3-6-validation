"""IT-50R5S3 — reject CSV input with mismatched governed headers."""

from __future__ import annotations

import csv
from importlib import import_module
from pathlib import Path
from typing import Callable

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GOVERNED_CSV = PROJECT_ROOT / "data" / "data-constraints.csv"
SOURCE_READER_MODULE = "app.services.governed_constraint_source_reader"


def _governed_headers_and_selector() -> tuple[list[str], str]:
    """Get headers and a selector from the governed CSV for test setup."""

    assert GOVERNED_CSV.is_file(), (
        "The governed CSV is required to build the malformed-header test "
        f"input: {GOVERNED_CSV}"
    )

    with GOVERNED_CSV.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as source_file:
        reader = csv.DictReader(source_file)
        assert reader.fieldnames, (
            f"The governed CSV has no header row: {GOVERNED_CSV}"
        )

        first_row = next(reader, None)
        assert first_row is not None, (
            f"The governed CSV has no data rows: {GOVERNED_CSV}"
        )
        selector = (first_row.get("Unique ID") or "").strip()
        assert selector, (
            "The first governed CSV row must have a Unique ID to supply "
            "the selection parameter."
        )
        return list(reader.fieldnames), selector


def _csv_row_reader() -> Callable:
    """Load the CSV row reader required by the governed-source contract."""

    try:
        module = import_module(SOURCE_READER_MODULE)
    except ModuleNotFoundError as error:
        if error.name != SOURCE_READER_MODULE:
            raise
        pytest.fail(
            "IT-50R5S3 requires the governed CSV source-reader module.",
            pytrace=False,
        )

    reader = getattr(module, "read_governed_constraint_row_from_csv", None)
    assert callable(reader), (
        "IT-50R5S3 requires "
        "read_governed_constraint_row_from_csv(csv_path, unique_id) "
        "to read and validate governed CSV input."
    )
    return reader


def test_it_50_r5_s3_rejects_csv_with_mismatched_governed_headers(
    tmp_path: Path,
) -> None:
    """Reject a CSV with a missing governed column before selecting a row."""

    headers, source_selector = _governed_headers_and_selector()
    assert len(headers) > 1, (
        "The governed CSV must have multiple columns to test a missing header."
    )

    malformed_csv = tmp_path / "missing-governed-header.csv"
    with malformed_csv.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as malformed_file:
        writer = csv.writer(malformed_file)
        writer.writerow(headers[:-1])

    read_row = _csv_row_reader()

    with pytest.raises(
        ValueError,
        match=r"(?i)(header|column|structure)",
    ):
        read_row(
            csv_path=malformed_csv,
            unique_id=source_selector,
        )