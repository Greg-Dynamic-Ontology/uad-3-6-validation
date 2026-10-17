"""IT-60R1S1: read governed rows from the configured workbook tab."""

from __future__ import annotations

from importlib import import_module, util
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIGURATION_FILE = PROJECT_ROOT / "config" / "configuration.ttl"
SOURCE_MODULE = "app.services.gse_constraint_sources"
READER_NAME = "read_active_compliance_workbook_rows"

REQUIRED_SOURCE_FIELDS = {
    "Message ID",
    "Unique ID",
    "Primary Data Element",
    "Rule Logic",
    "Severity",
    "Property Affected",
    " xPath",
    "Message Text",
}


def _configured_workbook_reader() -> Any:
    """Return the reader required by IT-60R1S1, or fail as a test assertion."""
    module_spec = util.find_spec(SOURCE_MODULE)
    assert module_spec is not None, (
        "IT-60R1S1 requires the governed GSE source service "
        f"{SOURCE_MODULE}."
    )

    module = import_module(SOURCE_MODULE)
    reader = getattr(module, READER_NAME, None)
    assert callable(reader), (
        "IT-60R1S1 requires "
        "read_active_compliance_workbook_rows(configuration_path=...)."
    )
    return reader


def test_it_60_r1_s1_reads_governed_rows_from_configured_workbook_tab() -> None:
    """Read source rows from the active workbook and its configured tab."""
    assert CONFIGURATION_FILE.is_file(), (
        "IT-60R1S1 requires the project configuration file: "
        f"{CONFIGURATION_FILE}"
    )

    read_active_compliance_workbook_rows = _configured_workbook_reader()
    source = read_active_compliance_workbook_rows(
        configuration_path=CONFIGURATION_FILE,
    )

    workbook_path = Path(source.workbook_path)
    worksheet_name = source.worksheet_name
    rows = source.rows

    assert workbook_path.is_file(), (
        "The configured active compliance workbook must exist: "
        f"{workbook_path}"
    )
    assert workbook_path.suffix.casefold() in {".xlsx", ".xlsm"}, (
        "Governed rows must be read from the configured Excel workbook, "
        f"not an intermediate file: {workbook_path}"
    )
    assert isinstance(worksheet_name, str) and worksheet_name.strip(), (
        "The configured active workbook must identify its worksheet."
    )
    assert rows, (
        "The configured workbook worksheet must contain governed rows."
    )

    for row_number, row in enumerate(rows, start=1):
        assert isinstance(row, dict), (
            f"Governed source row {row_number} must be returned as a mapping."
        )
        assert REQUIRED_SOURCE_FIELDS <= row.keys(), (
            f"Governed source row {row_number} is missing required fields: "
            f"{sorted(REQUIRED_SOURCE_FIELDS - row.keys())}"
        )
        for field in REQUIRED_SOURCE_FIELDS:
            assert isinstance(row[field], str), (
                f"Governed source field {field!r} in row {row_number} "
                "must be returned as text."
            )