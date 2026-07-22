"""
XML Schema validation service.

This module validates an XML instance document against an XML Schema (XSD)
and returns a SchemaValidationReport.
"""

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
from xml.parsers import expat

import xmlschema

from app.models.schema_validation import (
    SchemaFindingSeverity,
    SchemaValidationFinding,
    SchemaValidationReport,
    SchemaValidationStatus,
    SchemaValidationSummary,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
UAD36_SCHEMA_PATH = (
    PROJECT_ROOT
    / "specs"
    / "UAD"
    / "GSE_UAD_3.6.0_v1.3"
    / "Combined"
    / "GSE_UAD_3.6.0_v1.3.xsd"
)
UAD36_SCHEMA_VERSION = "GSE 3.6.0 Build v1.3"


def validate_uad36_xml_bytes(
    *,
    package_name: str,
    xml_bytes: bytes,
) -> SchemaValidationReport:
    """Validate uploaded bytes against the authoritative UAD 3.6 schema."""
    safe_package_name = Path(package_name).name or "uploaded-uad36-package.xml"

    with TemporaryDirectory(prefix="uad36-validation-") as directory_name:
        xml_path = Path(directory_name) / safe_package_name
        xml_path.write_bytes(xml_bytes)

        return validate_xml_schema(
            xml_path=xml_path,
            schema_path=UAD36_SCHEMA_PATH,
            schema_version=UAD36_SCHEMA_VERSION,
        )


@dataclass(frozen=True)
class _SourceLocation:
    line: int
    column: int


def validate_xml_schema(
    xml_path: Path,
    schema_path: Path,
    schema_version: str | None = None,
) -> SchemaValidationReport:
    """
    Validate an XML instance document against an XML Schema.

    Malformed XML, unreadable files, invalid schemas, and schema-validation
    errors are returned as findings rather than raised to the caller.
    """
    report_id = str(uuid4())

    try:
        source_locations = _collect_source_locations(xml_path)
    except expat.ExpatError as error:
        finding = SchemaValidationFinding(
            severity=SchemaFindingSeverity.ERROR,
            message=str(error),
            line=error.lineno,
            column=error.offset + 1,
        )

        return _build_report(
            report_id=report_id,
            xml_path=xml_path,
            schema_path=schema_path,
            schema_version=schema_version,
            well_formed=False,
            schema_valid=False,
            findings=[finding],
        )
    except OSError as error:
        finding = SchemaValidationFinding(
            severity=SchemaFindingSeverity.ERROR,
            message=str(error),
            line=None,
            column=None,
        )

        return _build_report(
            report_id=report_id,
            xml_path=xml_path,
            schema_path=schema_path,
            schema_version=schema_version,
            well_formed=False,
            schema_valid=False,
            findings=[finding],
        )

    try:
        schema = xmlschema.XMLSchema(schema_path)
    except (xmlschema.XMLSchemaException, OSError) as error:
        finding = _finding_from_schema_exception(error)

        return _build_report(
            report_id=report_id,
            xml_path=xml_path,
            schema_path=schema_path,
            schema_version=schema_version,
            well_formed=True,
            schema_valid=False,
            findings=[finding],
        )

    try:
        validation_errors = list(schema.iter_errors(xml_path))
    except (xmlschema.XMLSchemaException, OSError) as error:
        finding = _finding_from_schema_exception(error)

        return _build_report(
            report_id=report_id,
            xml_path=xml_path,
            schema_path=schema_path,
            schema_version=schema_version,
            well_formed=True,
            schema_valid=False,
            findings=[finding],
        )

    findings = [
        _finding_from_validation_error(
            error=error,
            source_locations=source_locations,
        )
        for error in validation_errors
    ]

    return _build_report(
        report_id=report_id,
        xml_path=xml_path,
        schema_path=schema_path,
        schema_version=schema_version,
        well_formed=True,
        schema_valid=not validation_errors,
        findings=findings,
    )


def _collect_source_locations(
    xml_path: Path,
) -> dict[str, _SourceLocation]:
    """
    Parse an XML document and record the actual line and column at which each
    element begins.

    Paths use local element names and one-based sibling indexes, for example:

        /Appraisal[1]/Identifier[1]
    """
    xml_bytes = xml_path.read_bytes()
    parser = expat.ParserCreate(namespace_separator="}")

    locations: dict[str, _SourceLocation] = {}
    path_stack: list[str] = []
    sibling_counts_stack: list[defaultdict[str, int]] = [
        defaultdict(int)
    ]

    def start_element(
        qualified_name: str,
        attributes: dict[str, str],
    ) -> None:
        del attributes

        local_name = _local_name(qualified_name)
        sibling_counts = sibling_counts_stack[-1]
        sibling_counts[local_name] += 1
        sibling_index = sibling_counts[local_name]

        path_stack.append(f"{local_name}[{sibling_index}]")
        path = "/" + "/".join(path_stack)

        locations[path] = _SourceLocation(
            line=parser.CurrentLineNumber,
            column=parser.CurrentColumnNumber + 1,
        )

        sibling_counts_stack.append(defaultdict(int))

    def end_element(
        qualified_name: str,
    ) -> None:
        del qualified_name

        sibling_counts_stack.pop()
        path_stack.pop()

    parser.StartElementHandler = start_element
    parser.EndElementHandler = end_element
    parser.Parse(xml_bytes, True)

    return locations


def _finding_from_validation_error(
    *,
    error: xmlschema.XMLSchemaValidationError,
    source_locations: dict[str, _SourceLocation],
) -> SchemaValidationFinding:
    error_path = getattr(error, "path", None)
    normalized_path = _normalize_xmlschema_path(error_path)

    location = source_locations.get(normalized_path)

    if location is None:
        location = _nearest_known_location(
            normalized_path=normalized_path,
            source_locations=source_locations,
        )

    reason = getattr(error, "reason", None)
    message = reason if reason else str(error)

    return SchemaValidationFinding(
        severity=SchemaFindingSeverity.ERROR,
        message=message,
        line=location.line if location is not None else None,
        column=location.column if location is not None else None,
    )


def _finding_from_schema_exception(
    error: Exception,
) -> SchemaValidationFinding:
    line: int | None = None
    column: int | None = None

    position = getattr(error, "position", None)

    if (
        isinstance(position, tuple)
        and len(position) == 2
        and isinstance(position[0], int)
        and isinstance(position[1], int)
    ):
        line = position[0]
        column = position[1] + 1
    else:
        line = _positive_integer_or_none(
            getattr(error, "sourceline", None)
        )

    return SchemaValidationFinding(
        severity=SchemaFindingSeverity.ERROR,
        message=str(error),
        line=line,
        column=column,
    )


def _normalize_xmlschema_path(
    path: object,
) -> str:
    """
    Convert an xmlschema XPath into the local-name indexed form used by the
    source-location map.
    """
    if not isinstance(path, str) or not path:
        return ""

    normalized_parts: list[str] = []

    for raw_part in path.strip("/").split("/"):
        if not raw_part:
            continue

        name_part, separator, index_part = raw_part.partition("[")

        if name_part.startswith("{") and "}" in name_part:
            name_part = name_part.split("}", 1)[1]
        elif ":" in name_part:
            name_part = name_part.split(":", 1)[1]

        if separator:
            normalized_parts.append(
                f"{name_part}[{index_part}"
            )
        else:
            normalized_parts.append(f"{name_part}[1]")

    if not normalized_parts:
        return ""

    return "/" + "/".join(normalized_parts)


def _nearest_known_location(
    *,
    normalized_path: str,
    source_locations: dict[str, _SourceLocation],
) -> _SourceLocation | None:
    """
    Return the location of the nearest known ancestor.

    Some schema errors are associated with a required child that does not
    exist. Such an element has no source location, so its containing element
    is the truthful location available in the source document.
    """
    candidate = normalized_path

    while candidate:
        location = source_locations.get(candidate)

        if location is not None:
            return location

        if "/" not in candidate.lstrip("/"):
            break

        candidate = candidate.rsplit("/", 1)[0]

    return None


def _local_name(
    qualified_name: str,
) -> str:
    if "}" in qualified_name:
        return qualified_name.rsplit("}", 1)[1]

    if ":" in qualified_name:
        return qualified_name.rsplit(":", 1)[1]

    return qualified_name


def _build_report(
    *,
    report_id: str,
    xml_path: Path,
    schema_path: Path,
    schema_version: str | None,
    well_formed: bool,
    schema_valid: bool,
    findings: list[SchemaValidationFinding],
) -> SchemaValidationReport:
    error_count = sum(
        1
        for finding in findings
        if finding.severity == SchemaFindingSeverity.ERROR
    )

    warning_count = sum(
        1
        for finding in findings
        if finding.severity == SchemaFindingSeverity.WARNING
    )

    summary = SchemaValidationSummary(
        finding_count=len(findings),
        error_count=error_count,
        warning_count=warning_count,
    )

    status = (
        SchemaValidationStatus.PASSED
        if well_formed and schema_valid
        else SchemaValidationStatus.FAILED
    )

    return SchemaValidationReport(
        report_id=report_id,
        package_name=xml_path.name,
        schema_name=schema_path.name,
        schema_version=schema_version,
        well_formed=well_formed,
        schema_valid=schema_valid,
        status=status,
        summary=summary,
        findings=findings,
    )


def _positive_integer_or_none(
    value: object,
) -> int | None:
    if not isinstance(value, int):
        return None

    if value < 1:
        return None

    return value