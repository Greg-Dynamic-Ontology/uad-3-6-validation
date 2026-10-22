"""IT-53R3S1: reject a bound constraint with no resolvable context."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from rdflib import Dataset, Graph, Literal, Namespace, RDF, URIRef
from rdflib.compare import isomorphic

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
TEST_NAMESPACE = "urn:uad36:test:it53r3s1:"


class _TriXDataset(Dataset):
    """Bridge TriX's legacy iteration call to Dataset's current API."""

    def contexts(self, triple=None):
        return self.graphs(triple)


def _schema_fixture() -> Graph:
    """Provide only PROPERTY/ADDRESS/AddressLineText."""

    def qname(name: str) -> QName:
        return QName(TEST_NAMESPACE, name)

    target = ElementDeclaration(
        name=qname("AddressLineText"),
    )
    address = ElementDeclaration(
        name=qname("ADDRESS"),
        type_name=qname("ADDRESS_TYPE"),
    )
    property_element = ElementDeclaration(
        name=qname("PROPERTY"),
        type_name=qname("PROPERTY_TYPE"),
    )

    definitions = [
        ComplexTypeDefinition(
            name=qname("ADDRESS_TYPE"),
            content=ModelGroup(
                kind=ModelGroupKind.SEQUENCE,
                elements=(target,),
            ),
        ),
        ComplexTypeDefinition(
            name=qname("PROPERTY_TYPE"),
            content=ModelGroup(
                kind=ModelGroupKind.SEQUENCE,
                elements=(address,),
            ),
        ),
    ]

    model = SchemaModel(
        target_namespace=TEST_NAMESPACE,
        elements={
            property_element.name: property_element,
        },
        complex_types={
            definition.name: definition
            for definition in definitions
        },
    )
    return logical_schema_model_to_graph(model)


@pytest.mark.parametrize(
    "unresolved_path",
    (
        "/UNKNOWN/ADDRESS/AddressLineText",
        "/ADDRESS/PROPERTY/AddressLineText",
    ),
    ids=("unknown-ancestor", "known-elements-wrong-order"),
)
def test_it_53_r3_s1_rejects_bound_constraint_without_governed_context(
    unresolved_path: str,
    tmp_path: Path,
) -> None:
    token = uuid4().hex
    source_constraint = URIRef(
        f"{TEST_NAMESPACE}source:{token}"
    )
    governed_source = {
        "unique_id": f"IT-53R3S1-{token}",
        "data_point_name": "AddressLineText",
        "source_rule_id": f"IT-53R3S1-{token}",
        "requirement_text": (
            "Provide the address line in the governed context."
        ),
        "violation_condition": (
            "The address line is absent in the governed context."
        ),
        "severity": "Fatal",
        "context_fields": [
            "Physical Address",
            unresolved_path,
        ],
        "source_locator": str(source_constraint),
        "source_constraint_uri": str(source_constraint),
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

    schema_graph = _schema_fixture()
    bound_graph = Graph()
    bind_normalized_constraint_to_logical_schema(
        normalized_graph=normalized_graph,
        logical_schema_graph=schema_graph,
        constraint_id=str(constraint),
        output_graph=bound_graph,
    )

    bindings = set(
        bound_graph.objects(
            constraint,
            CV.boundLogicalSchemaResource,
        )
    )
    assert len(bindings) == 1, (
        "The constraint must already have a valid IT-52 binding."
    )

    source_context_nodes = set(
        bound_graph.objects(
            constraint,
            CV.hasSourceContext,
        )
    )
    assert source_context_nodes
    assert Literal(unresolved_path) in {
        value
        for node in source_context_nodes
        for value in bound_graph.objects(
            node,
            CV.contextValue,
        )
    }

    bound_before = set(bound_graph)
    schema_before = set(schema_graph)
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
            "IT-53R3S1 requires governed EXCEPTION knowledge "
            "for an unresolved source context, eligible for the "
            "Batch Results Graph. The resolver instead raised "
            f"an uncontracted ValueError: {error}",
            pytrace=False,
        )

    assert set(bound_graph) == bound_before
    assert set(schema_graph) == schema_before
    assert bound_before.issubset(set(output_graph)), (
        "Exception output must preserve the upstream source knowledge."
    )

    assert not list(
        output_graph.objects(
            constraint,
            CV.applicableContext,
        )
    ), "An unresolved constraint must not receive an invented context."

    assert not list(
        output_graph.subjects(
            RDF.type,
            CV.ConstraintContext,
        )
    )
    assert not list(
        output_graph.subject_objects(CV.schemaPath)
    ), "An unresolved constraint must not receive an invented schema path."

    recorded = read_construction_stage_result(
        exchange_graph=output_graph,
        result_id=str(result.result_id),
    )
    assert recorded.constraint_id == str(constraint)
    assert recorded.construction_stage == "context-resolution"
    assert recorded.construction_status == "EXCEPTION"
    assert recorded.available_for_downstream is False
    assert recorded.exception_reason
    assert unresolved_path in recorded.exception_reason, (
        "The exception must identify the unresolved source context."
    )

    assert (
        result.result_id,
        UADEX.forConstraint,
        constraint,
    ) in output_graph
    assert not list(
        output_graph.objects(
            result.result_id,
            UADEX.stageKnowledge,
        )
    ), "An exception must not advertise successful downstream knowledge."

    assert set(
        output_graph.objects(
            constraint,
            CV.hasSourceContext,
        )
    ) == source_context_nodes

    for node in source_context_nodes:
        assert set(
            output_graph.predicate_objects(node)
        ) == set(
            bound_graph.predicate_objects(node)
        ), "The unresolved source-context knowledge must be preserved."

    # TriX serializes the graph identity together with its RDF contents.
    batch_graph_id = URIRef(
        f"{TEST_NAMESPACE}batch-results:{token}"
    )
    dataset = _TriXDataset()
    batch_graph = dataset.graph(batch_graph_id)
    for triple in output_graph:
        batch_graph.add(triple)

    serialized_batch = dataset.serialize(format="trix")

    # Parse through an ordinary Graph sharing the Dataset's store.
    # TriX itself supplies the named graph identity from the document.
    restored_dataset = Dataset()
    parser_graph = Graph(store=restored_dataset.store)
    parser_graph.parse(
        data=serialized_batch,
        format="trix",
    )

    restored_graph_ids = {
        graph.identifier
        for graph in restored_dataset.graphs()
        if len(graph)
    }
    assert restored_graph_ids == {batch_graph_id}, (
        "Serialization must preserve the named Batch Results Graph IRI."
    )

    restored_batch_graph = restored_dataset.graph(
        batch_graph_id
    )
    assert isomorphic(batch_graph, restored_batch_graph), (
        "Serialization must preserve the complete Batch Results Graph."
    )

    restored_result = read_construction_stage_result(
        exchange_graph=restored_batch_graph,
        result_id=str(result.result_id),
    )
    assert restored_result == recorded, (
        "The exception must retain its identity and contracted "
        "metadata in the serialized Batch Results Graph."
    )
    assert (
        constraint,
        CV.hasSourceContext,
        next(iter(source_context_nodes)),
    ) in restored_batch_graph