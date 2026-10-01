"""Evaluate governed format, precision, and text-length restrictions."""

import hashlib
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
from uuid import uuid4
from xml.etree import ElementTree as ET

from lxml import etree
from rdflib import Graph, Literal, Namespace, RDF

from app.models.common import Provenance
from app.models.enums import RuleType, Severity
from app.models.validation import Finding


B = Namespace("urn:uad36:representation-restriction-binding:")
BINDINGS = (
    Path(__file__).resolve().parents[2]
    / "data/representation-restriction-bindings.ttl"
)
NS = {"m": "http://www.mismo.org/residential/2009/schemas"}
SOURCE_COLUMNS = (
    "Message ID",
    "Unique ID",
    "Primary Data Element",
    "Rule Logic",
    "Severity",
    "Property Affected",
    " xPath",
    "Message Text",
)


def fingerprint(row: dict[str, str]) -> str:
    return hashlib.sha256(
        json.dumps(
            [row.get(key) for key in SOURCE_COLUMNS],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


@lru_cache(maxsize=1)
def load_bindings() -> dict[str, dict[str, object]]:
    graph = Graph().parse(BINDINGS, format="turtle")
    required = (
        "element",
        "evaluationMode",
        "expectedDataLocation",
        "maximumLength",
        "maximumValue",
        "minimumFractionDigits",
        "minimumValue",
        "pattern",
        "ruleId",
        "selectionXPath",
        "sourceFingerprint",
        "violationKind",
    )
    bindings: dict[str, dict[str, object]] = {}
    for node in graph.subjects(RDF.type, B.Binding):
        record: dict[str, object] = {}
        for name in required:
            values = list(graph.objects(node, B[name]))
            if len(values) != 1 or not isinstance(values[0], Literal):
                raise ValueError(f"{node}: expected one literal {name}")
            record[name] = values[0].toPython()
        rule_id = str(record["ruleId"])
        if rule_id in bindings:
            raise ValueError(
                f"Duplicate representation-restriction binding: {rule_id}"
            )
        bindings[rule_id] = record
    return bindings


def binding_for(row: dict[str, str]) -> dict[str, object] | None:
    record = load_bindings().get(row.get("Message ID"))
    if record is not None and fingerprint(row) != record["sourceFingerprint"]:
        raise ValueError(
            f"{row.get('Message ID')}: governed representation definition "
            "changed"
        )
    return record


def scalar_text(value) -> str:
    if isinstance(value, etree._Element):
        return "".join(value.itertext()).strip()
    return str(value).strip()


def valid_full_date(raw: str, pattern: str) -> bool:
    if re.fullmatch(pattern, raw) is None:
        return False
    try:
        date.fromisoformat(raw)
    except ValueError:
        return False
    return True


def valid_year_month(raw: str, pattern: str) -> bool:
    if re.fullmatch(pattern, raw) is None:
        return False
    try:
        year, month = (int(part) for part in raw.split("-"))
    except ValueError:
        return False
    return year > 0 and 1 <= month <= 12


def valid_decimal_precision_range(
    raw: str,
    minimum: str,
    maximum: str,
    minimum_fraction_digits: int,
) -> bool:
    match = re.fullmatch(r"[+-]?\d+(?:\.(\d+))?", raw)
    if match is None:
        return False
    try:
        value = Decimal(raw)
        lower = Decimal(minimum)
        upper = Decimal(maximum)
    except InvalidOperation:
        return False
    fraction = match.group(1) or ""
    return (
        lower <= value <= upper
        and len(fraction) >= minimum_fraction_digits
    )


def violates(raw: str, record: dict[str, object]) -> bool:
    mode = str(record["evaluationMode"])
    if mode == "pattern":
        return re.fullmatch(str(record["pattern"]), raw) is None
    if mode == "full-date":
        return not valid_full_date(raw, str(record["pattern"]))
    if mode == "year-month":
        return not valid_year_month(raw, str(record["pattern"]))
    if mode == "decimal-precision-range":
        return not valid_decimal_precision_range(
            raw,
            str(record["minimumValue"]),
            str(record["maximumValue"]),
            int(record["minimumFractionDigits"]),
        )
    if mode == "max-length":
        return len(raw) > int(record["maximumLength"])
    raise ValueError(f"Unsupported representation mode: {mode}")


def evaluate_representation_restriction(root, investor, row):
    record = binding_for(row)
    if record is None:
        return []

    document = etree.fromstring(ET.tostring(root, encoding="utf-8"))
    invalid = []
    for selected in document.getroottree().xpath(
        str(record["selectionXPath"]), namespaces=NS
    ):
        raw = scalar_text(selected)
        # Missing values are governed by required-data categories.
        if raw and violates(raw, record):
            invalid.append(raw)
    if not invalid:
        return []

    observed = invalid[0]
    if str(record["evaluationMode"]) == "max-length":
        observed = f"length {len(observed)}"

    return [
        Finding(
            finding_id=f"F-{uuid4().hex[:8]}",
            severity=Severity(row["Severity"].casefold()),
            investor=investor,
            rule_type=RuleType.APPENDIX_H,
            rule_id=row["Message ID"],
            row_id=row["Unique ID"],
            primary_data_element=str(record["element"]),
            property_affected=row["Property Affected"],
            violation_kind=str(record["violationKind"]),
            data_location=str(record["expectedDataLocation"]),
            observed_value=observed,
            expected_condition=row["Rule Logic"],
            source=Provenance(
                source_document="data/data-constraints.csv",
                source_version="UAD 3.6",
                source_section=row["Unique ID"],
            ),
            finding=row["Message Text"],
        )
    ]
