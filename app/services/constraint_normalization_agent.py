"""Normalize governed source constraints into stable RDF knowledge."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from rdflib import Graph, Literal, Namespace, RDF, URIRef


UADCON = Namespace("https://dynamicontology.com/uad36/constraint/")
UADCV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")
PROV = Namespace("http://www.w3.org/ns/prov#")

NORMALIZATION_STAGE = "normalized-constraint-representation"


@dataclass(frozen=True)
class NormalizedConstraintResult:
    """Identity summary for one normalized governed constraint."""

    constraint_id: str
    unique_id: str
    data_point_name: str
    source_rule_id: str


@dataclass(frozen=True)
class NormalizationException:
    """Contracted knowledge exception returned by the bounded worker."""

    kind: str
    constraint_id: str
    stage: str
    requires_review: bool
    message: str


@dataclass(frozen=True)
class ConstraintNormalizationExecutionResult:
    """Contracted result of one bounded normalization-agent execution."""

    status: str
    output: NormalizedConstraintResult | None
    exception: NormalizationException | None


def _is_missing_required_value(value: object) -> bool:
    """Return whether a required governed value is absent or empty."""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return not value
    return False


def _format_ambiguous_value(value: object) -> str:
    """Format all candidate values deterministically for a review exception."""
    if isinstance(value, set):
        value = sorted(value, key=repr)
    elif isinstance(value, dict):
        value = dict(sorted(value.items(), key=lambda item: repr(item[0])))
    return repr(value)


def _normalized_constraint_iri(governed_source: dict) -> URIRef:
    """Mint a valid, row-specific IRI from governed source identity."""

    source_identity = governed_source.get("source_constraint_uri")
    if _is_missing_required_value(source_identity):
        source_identity = governed_source.get("source_locator")

    if _is_missing_required_value(source_identity):
        raise ValueError(
            "Insufficient governed source knowledge; missing: "
            "source_constraint_uri or source_locator"
        )

    identity_digest = sha256(str(source_identity).encode("utf-8")).hexdigest()
    return URIRef(f"{UADCON}{identity_digest}")


def normalize_governed_constraint(
    *,
    governed_source: dict,
    output_graph,
) -> NormalizedConstraintResult:
    """Produce normalized constraint RDF from sufficient governed source knowledge."""

    required_fields = (
        "unique_id",
        "data_point_name",
        "source_rule_id",
        "requirement_text",
        "violation_condition",
        "severity",
        "context_fields",
        "source_locator",
    )
    missing_fields = [
        field
        for field in required_fields
        if field not in governed_source
        or _is_missing_required_value(governed_source[field])
    ]
    if missing_fields:
        raise ValueError(
            "Insufficient governed source knowledge; missing: "
            + ", ".join(missing_fields)
        )

    scalar_fields = (
        "unique_id",
        "data_point_name",
        "source_rule_id",
        "requirement_text",
        "violation_condition",
        "severity",
        "source_locator",
    )
    ambiguous_fields = [
        field
        for field in scalar_fields
        if isinstance(governed_source[field], (list, tuple, set, dict))
    ]
    if ambiguous_fields:
        ambiguity_details = ", ".join(
            f"{field}={_format_ambiguous_value(governed_source[field])}"
            for field in ambiguous_fields
        )
        raise ValueError(
            "Ambiguous governed source knowledge; multiple values supplied for: "
            + ambiguity_details
        )

    unique_id = str(governed_source["unique_id"])
    constraint = _normalized_constraint_iri(governed_source)

    output_graph.add((constraint, RDF.type, UADCV.NormalizedConstraint))
    output_graph.add(
        (constraint, UADCV.governedUniqueId, Literal(unique_id))
    )
    output_graph.add(
        (
            constraint,
            UADCV.dataPointName,
            Literal(governed_source["data_point_name"]),
        )
    )
    output_graph.add(
        (
            constraint,
            UADCV.sourceRuleId,
            Literal(governed_source["source_rule_id"]),
        )
    )
    output_graph.add(
        (
            constraint,
            UADCV.requirementText,
            Literal(governed_source["requirement_text"]),
        )
    )
    output_graph.add(
        (
            constraint,
            UADCV.violationCondition,
            Literal(governed_source["violation_condition"]),
        )
    )
    output_graph.add(
        (
            constraint,
            UADCV.severity,
            Literal(governed_source["severity"]),
        )
    )
    output_graph.add(
        (
            constraint,
            UADCV.sourceLocator,
            Literal(governed_source["source_locator"]),
        )
    )

    for index, context_value in enumerate(
        governed_source["context_fields"],
        start=1,
    ):
        context_node = URIRef(f"{constraint}/source-context/{index}")
        output_graph.add(
            (constraint, UADCV.hasSourceContext, context_node)
        )
        output_graph.add(
            (context_node, UADCV.contextOrder, Literal(index))
        )
        output_graph.add(
            (
                context_node,
                UADCV.contextValue,
                Literal(context_value),
            )
        )

    return NormalizedConstraintResult(
        constraint_id=str(constraint),
        unique_id=unique_id,
        data_point_name=str(governed_source["data_point_name"]),
        source_rule_id=str(governed_source["source_rule_id"]),
    )


def normalize_governed_constraint_to_file(
    *,
    governed_source: dict,
    output_path: str | Path,
) -> NormalizedConstraintResult:
    """Normalize one governed source constraint and write its RDF as Turtle."""

    source_constraint_uri = governed_source.get("source_constraint_uri")
    if not source_constraint_uri:
        raise ValueError(
            "Insufficient governed source knowledge; missing: "
            "source_constraint_uri"
        )

    output_graph = Graph()
    result = normalize_governed_constraint(
        governed_source=governed_source,
        output_graph=output_graph,
    )

    normalized_constraint = URIRef(result.constraint_id)
    output_graph.add(
        (
            normalized_constraint,
            PROV.wasDerivedFrom,
            URIRef(str(source_constraint_uri)),
        )
    )

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    output_graph.serialize(
        destination=str(destination),
        format="turtle",
    )

    return result


def normalize_governed_constraint_from_workbook(
    *,
    workbook_path,
    worksheet_name: str,
    cell_range: str,
    output_graph,
) -> NormalizedConstraintResult:
    """
    Read one governed source row and normalize its knowledge into RDF.

    The source reader owns extraction. The normalization agent owns the
    transformation from materialized governed source knowledge to the stable,
    implementation-independent normalized constraint representation.
    """
    from app.services.governed_constraint_source_reader import (
        read_governed_constraint_row,
    )

    governed_source = read_governed_constraint_row(
        workbook_path=workbook_path,
        worksheet_name=worksheet_name,
        cell_range=cell_range,
    )

    return normalize_governed_constraint(
        governed_source=governed_source,
        output_graph=output_graph,
    )


def execute_constraint_normalization(
    *,
    governed_source: dict,
    output_graph,
) -> ConstraintNormalizationExecutionResult:
    """
    Execute normalization as a bounded worker.

    Knowledge insufficiency or ambiguity is converted into a contracted
    exception result rather than escaping as an unbounded implementation
    exception. Successful normalization returns only the contracted output.
    """
    try:
        output = normalize_governed_constraint(
            governed_source=governed_source,
            output_graph=output_graph,
        )
    except ValueError as exc:
        message = str(exc)
        if message.startswith("Insufficient governed source knowledge"):
            kind = "insufficient-governed-knowledge"
        elif message.startswith("Ambiguous governed source knowledge"):
            kind = "ambiguous-governed-knowledge"
        else:
            raise

        return ConstraintNormalizationExecutionResult(
            status="exception",
            output=None,
            exception=NormalizationException(
                kind=kind,
                constraint_id=str(governed_source.get("unique_id", "")),
                stage=NORMALIZATION_STAGE,
                requires_review=True,
                message=message,
            ),
        )

    return ConstraintNormalizationExecutionResult(
        status="success",
        output=output,
        exception=None,
    )


__all__ = [
    "ConstraintNormalizationExecutionResult",
    "NormalizationException",
    "NormalizedConstraintResult",
    "execute_constraint_normalization",
    "normalize_governed_constraint",
    "normalize_governed_constraint_from_workbook",
    "normalize_governed_constraint_to_file",
]