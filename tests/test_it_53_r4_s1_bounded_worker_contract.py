"""IT-53R4S1: context resolution remains a bounded construction worker."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from rdflib import Graph, Namespace, RDF, URIRef
from rdflib.namespace import PROV

from app.models.schema_model import (
    ComplexTypeDefinition,
    ElementDeclaration,
    ModelGroup,
    ModelGroupKind,
    QName,
    SchemaModel,
)
from app.services.construction_exchange import (
    UADEX,
    ConstructionStageResultRecord,
    read_construction_stage_result,
)
from app.services.constraint_normalization_agent import (
    normalize_governed_constraint_to_file,
)
from app.services.context_resolution_agent import (
    resolve_bound_constraint_context,
)
from app.services.logical_schema_binding_agent import (
    bind_normalized_constraint_to_logical_schema,
)
from app.services.logical_schema_serializer import (
    logical_schema_model_to_graph,
)


CV = Namespace(
    "https://dynamicontology.com/uad36/constraint-vocabulary#"
)
TEST_NAMESPACE = "urn:uad36:test:it53r4s1:"
SHACL_NAMESPACE = "http://www.w3.org/ns/shacl#"

# The bounded worker may add context knowledge, exchange metadata,
# RDF-list structure, and common provenance. Later-stage knowledge
# falls outside this output contract.
ALLOWED_ADDED_PREDICATES = {
    RDF.type,
    RDF.first,
    RDF.rest,
    CV.applicableContext,
    CV.schemaPath,
    CV.hasSourceContext,
    CV.candidateContext,
    UADEX.forConstraint,
    UADEX.constructionStage,
    UADEX.constructionStatus,
    UADEX.availableForDownstream,
    UADEX.exceptionReason,
    UADEX.requiresReview,
    UADEX.stageKnowledge,
}
ALLOWED_ADDED_TYPES = {
    CV.ConstraintContext,
    UADEX.ConstructionStageResult,
    PROV.Entity,
    PROV.Activity,
    PROV.Agent,
}


def _schema_fixture(ambiguous: bool) -> Graph:
    """Supply one or two contexts sharing one terminal declaration."""
    target = ElementDeclaration(
        name=QName(TEST_NAMESPACE, "AddressLineText"),
    )
    namespaces = [f"{TEST_NAMESPACE}context-a:"]
    if ambiguous:
        namespaces.append(f"{TEST_NAMESPACE}context-b:")

    roots = {}
    definitions = {}

    for namespace in namespaces:
        address_type_name = QName(namespace, "ADDRESS_TYPE")
        property_type_name = QName(namespace, "PROPERTY_TYPE")

        address = ElementDeclaration(
            name=QName(namespace, "ADDRESS"),
            type_name=address_type_name,
        )
        property_element = ElementDeclaration(
            name=QName(namespace, "PROPERTY"),
            type_name=property_type_name,
        )
        roots[property_element.name] = property_element

        definitions[address_type_name] = ComplexTypeDefinition(
            name=address_type_name,
            content=ModelGroup(
                kind=ModelGroupKind.SEQUENCE,
                elements=(target,),
            ),
        )
        definitions[property_type_name] = ComplexTypeDefinition(
            name=property_type_name,
            content=ModelGroup(
                kind=ModelGroupKind.SEQUENCE,
                elements=(address,),
            ),
        )

    model = SchemaModel(
        target_namespace=TEST_NAMESPACE,
        namespaces=frozenset(
            [TEST_NAMESPACE, *namespaces]
        ),
        elements=roots,
        complex_types=definitions,
    )
    return logical_schema_model_to_graph(model)


@pytest.mark.parametrize(
    "outcome",
    ("success", "unresolved", "ambiguous"),
)
def test_it_53_r4_s1_returns_only_contracted_output_or_exception(
    outcome: str,
    tmp_path: Path,
) -> None:
    token = uuid4().hex
    source_identity = f"{TEST_NAMESPACE}source:{token}"
    source_path = (
        "/UNKNOWN/ADDRESS/AddressLineText"
        if outcome == "unresolved"
        else "/PROPERTY/ADDRESS/AddressLineText"
    )
    governed_source = {
        "unique_id": f"IT-53R4S1-{token}",
        "data_point_name": "AddressLineText",
        "source_rule_id": f"IT-53R4S1-{token}",
        "requirement_text": (
            "Provide the address line in the governed context."
        ),
        "violation_condition": (
            "The address line is absent in the governed context."
        ),
        "severity": "Fatal",
        "context_fields": [source_path],
        "source_locator": source_identity,
        "source_constraint_uri": source_identity,
    }

    normalized_path = tmp_path / "normalized-constraint.ttl"
    normalization = normalize_governed_constraint_to_file(
        governed_source=governed_source,
        output_path=normalized_path,
    )
    normalized_graph = Graph().parse(
        normalized_path,
        format="turtle",
    )
    constraint = URIRef(normalization.constraint_id)

    schema_graph = _schema_fixture(
        ambiguous=outcome == "ambiguous",
    )
    bound_graph = Graph()
    bind_normalized_constraint_to_logical_schema(
        normalized_graph=normalized_graph,
        logical_schema_graph=schema_graph,
        constraint_id=str(constraint),
        output_graph=bound_graph,
    )

    original_bindings = set(
        bound_graph.objects(
            constraint,
            CV.boundLogicalSchemaResource,
        )
    )
    assert len(original_bindings) == 1

    bound_before = set(bound_graph)
    schema_before = set(schema_graph)
    prior_stage_results = set(
        bound_graph.subjects(
            RDF.type,
            UADEX.ConstructionStageResult,
        )
    )

    output_graph = Graph()
    try:
        result = resolve_bound_constraint_context(
            bound_graph=bound_graph,
            logical_schema_graph=schema_graph,
            constraint_id=str(constraint),
            output_graph=output_graph,
        )
    except ValueError as error:
        pytest.fail(
            "A valid governed binding must produce a contracted "
            "context result or a governed context-resolution exception; "
            f"the worker raised ValueError: {error}",
            pytrace=False,
        )

    assert isinstance(result, ConstructionStageResultRecord)
    assert result.constraint_id == str(constraint)
    assert result.construction_stage == "context-resolution"

    expected_status = (
        "GREEN" if outcome == "success" else "EXCEPTION"
    )
    assert result.construction_status == expected_status
    assert result.available_for_downstream is (
        outcome == "success"
    )
    assert result.requires_review is (outcome != "success")

    assert set(bound_graph) == bound_before, (
        "The worker must not modify the governed input binding."
    )
    assert set(schema_graph) == schema_before, (
        "The worker must not modify the Logical Schema Model."
    )
    assert bound_before.issubset(set(output_graph)), (
        "The worker must preserve all upstream knowledge."
    )

    # Preservation requires exact original values, not merely retaining
    # old triples while adding conflicting values.
    for subject, predicate in set(
        normalized_graph.subject_predicates()
    ):
        assert set(
            output_graph.objects(subject, predicate)
        ) == set(
            normalized_graph.objects(subject, predicate)
        ), (
            "Context resolution must not change normalized "
            f"governed meaning for {subject} / {predicate}."
        )

    assert set(
        output_graph.objects(
            constraint,
            CV.boundLogicalSchemaResource,
        )
    ) == original_bindings

    expected_constraint_predicates = set(
        bound_graph.predicates(constraint)
    )
    if outcome == "success":
        expected_constraint_predicates.add(
            CV.applicableContext
        )
    assert set(
        output_graph.predicates(constraint)
    ) == expected_constraint_predicates, (
        "The worker must not attach behavior classification, "
        "Instance RDF bindings, or finding definitions to the constraint."
    )

    added_triples = set(output_graph) - bound_before
    for subject, predicate, value in added_triples:
        assert (
            predicate in ALLOWED_ADDED_PREDICATES
            or str(predicate).startswith(str(PROV))
        ), (
            "The worker generated knowledge outside its "
            f"context-resolution contract: {(subject, predicate, value)!r}"
        )

        if predicate == RDF.type:
            assert value in ALLOWED_ADDED_TYPES, (
                "The worker must not create validation behavior, "
                "Instance RDF bindings, shapes, or report findings."
            )

        assert not any(
            isinstance(term, URIRef)
            and str(term).startswith(SHACL_NAMESPACE)
            for term in (subject, predicate, value)
        ), "The context-resolution worker must not generate SHACL."

    new_stage_results = set(
        output_graph.subjects(
            RDF.type,
            UADEX.ConstructionStageResult,
        )
    ) - prior_stage_results
    assert new_stage_results == {result.result_id}, (
        "The worker must produce only its own stage result."
    )

    contexts = set(
        output_graph.objects(
            constraint,
            CV.applicableContext,
        )
    )
    if outcome == "success":
        assert len(contexts) == 1
        assert set(
            output_graph.objects(
                result.result_id,
                UADEX.stageKnowledge,
            )
        ) == contexts
        assert result.exception_reason is None
    else:
        assert not contexts
        assert result.exception_reason
        assert not list(
            output_graph.objects(
                result.result_id,
                UADEX.stageKnowledge,
            )
        )

    # The return value and serialized exchange graph must describe
    # the same contracted outcome.
    downstream_graph = Graph().parse(
        data=output_graph.serialize(format="turtle"),
        format="turtle",
    )
    recorded = read_construction_stage_result(
        exchange_graph=downstream_graph,
        result_id=str(result.result_id),
    )
    assert recorded == result