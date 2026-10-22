"""IT-53R1S1: resolve one applicable context for a bound constraint."""

from __future__ import annotations

from importlib import import_module
from importlib.util import find_spec
from pathlib import Path
from uuid import uuid4

import pytest
from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.collection import Collection
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
    read_construction_stage_result,
)
from app.services.constraint_normalization_agent import (
    normalize_governed_constraint_to_file,
)
from app.services.logical_schema_binding_agent import (
    bind_normalized_constraint_to_logical_schema,
)
from app.services.logical_schema_serializer import (
    LOGICAL_SCHEMA_MODEL_IRI,
    logical_schema_model_to_graph,
)


CV = Namespace(
    "https://dynamicontology.com/uad36/constraint-vocabulary#"
)
LSM = Namespace(
    "https://dynamicontology.com/uad36/logical-schema#"
)
TEST_NAMESPACE = "urn:uad36:test:it53r1s1:"
RESOLVER_MODULE = "app.services.context_resolution_agent"


def _fixture_schema() -> Graph:
    """Create two governed schema paths sharing one terminal declaration."""

    def qname(local_name: str) -> QName:
        return QName(TEST_NAMESPACE, local_name)

    target = ElementDeclaration(
        name=qname("AddressLineText"),
    )
    address = ElementDeclaration(
        name=qname("ADDRESS"),
        type_name=qname("ADDRESS_TYPE"),
    )

    roots = [
        ElementDeclaration(
            name=qname(parent),
            type_name=qname(f"{parent}_TYPE"),
        )
        for parent in ("PROPERTY", "BORROWER")
    ]

    address_type = ComplexTypeDefinition(
        name=qname("ADDRESS_TYPE"),
        content=ModelGroup(
            kind=ModelGroupKind.SEQUENCE,
            elements=(target,),
        ),
    )
    parent_types = [
        ComplexTypeDefinition(
            name=qname(f"{parent}_TYPE"),
            content=ModelGroup(
                kind=ModelGroupKind.SEQUENCE,
                elements=(address,),
            ),
        )
        for parent in ("PROPERTY", "BORROWER")
    ]

    model = SchemaModel(
        target_namespace=TEST_NAMESPACE,
        elements={
            declaration.name: declaration
            for declaration in roots
        },
        complex_types={
            definition.name: definition
            for definition in [address_type, *parent_types]
        },
    )

    graph = logical_schema_model_to_graph(model)

    # Pass RDF across the same serialization boundary used by stages.
    return Graph().parse(
        data=graph.serialize(format="turtle"),
        format="turtle",
    )


def _schema_qname(graph: Graph, local_name: str) -> URIRef:
    matches = {
        subject
        for subject in graph.subjects(
            LSM.local_name,
            Literal(local_name),
        )
        if (
            subject,
            RDF.type,
            LSM.QName,
        ) in graph
    }
    assert len(matches) == 1, (
        f"Test fixture must identify one QName for {local_name!r}; "
        f"found {len(matches)}."
    )

    resource = next(iter(matches))
    assert isinstance(resource, URIRef)
    return resource


def _load_context_resolver():
    """Missing behavior fails during the test, not during collection."""
    assert find_spec(RESOLVER_MODULE) is not None, (
        "IT-53R1S1 requires a context-resolution operation that "
        "resolves governed source context against the Logical Schema. "
        f"The production service {RESOLVER_MODULE} is not available."
    )

    module = import_module(RESOLVER_MODULE)
    operation = getattr(
        module,
        "resolve_bound_constraint_context",
        None,
    )
    assert callable(operation), (
        "IT-53R1S1 requires resolve_bound_constraint_context("
        "bound_graph=..., logical_schema_graph=..., "
        "constraint_id=..., output_graph=...)."
    )
    return operation


@pytest.mark.parametrize(
    "parent",
    ("PROPERTY", "BORROWER"),
    ids=("property-address", "borrower-address"),
)
def test_it_53_r1_s1_resolves_one_applicable_context_for_bound_constraint(
    parent: str,
    tmp_path: Path,
) -> None:
    token = uuid4().hex
    source_constraint = URIRef(
        f"{TEST_NAMESPACE}source:{token}"
    )
    source_context = (
        f"/{parent}/ADDRESS/AddressLineText"
    )
    governed_source = {
        "unique_id": f"IT-53R1S1-{token}",
        "data_point_name": "AddressLineText",
        "source_rule_id": f"IT-53R1S1-{token}",
        "requirement_text": (
            "Provide the address line in the governed context."
        ),
        "violation_condition": (
            "The address line is absent in the governed context."
        ),
        "severity": "Fatal",
        "context_fields": [source_context],
        "source_locator": str(source_constraint),
        "source_constraint_uri": str(source_constraint),
    }

    schema_graph = _fixture_schema()
    expected_path_resources = {
        _schema_qname(schema_graph, parent),
        _schema_qname(schema_graph, "ADDRESS"),
        _schema_qname(schema_graph, "AddressLineText"),
    }
    other_parent = (
        "BORROWER" if parent == "PROPERTY" else "PROPERTY"
    )
    excluded_parent = _schema_qname(
        schema_graph,
        other_parent,
    )

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

    bound_graph = Graph()
    bind_normalized_constraint_to_logical_schema(
        normalized_graph=normalized_graph,
        logical_schema_graph=schema_graph,
        constraint_id=str(constraint),
        output_graph=bound_graph,
    )

    bound_resources = set(
        bound_graph.objects(
            constraint,
            CV.boundLogicalSchemaResource,
        )
    )
    assert len(bound_resources) == 1, (
        "The existing IT-52 stage must supply exactly one binding."
    )
    assert (
        constraint,
        PROV.wasDerivedFrom,
        source_constraint,
    ) in bound_graph

    source_context_nodes = set(
        bound_graph.objects(
            constraint,
            CV.hasSourceContext,
        )
    )
    assert source_context_nodes
    assert {
        context_value
        for node in source_context_nodes
        for context_value in bound_graph.objects(
            node,
            CV.contextValue,
        )
    } == {Literal(source_context)}

    bound_before = set(bound_graph)
    schema_before = set(schema_graph)

    resolver = _load_context_resolver()
    output_graph = Graph()
    result = resolver(
        bound_graph=bound_graph,
        logical_schema_graph=schema_graph,
        constraint_id=str(constraint),
        output_graph=output_graph,
    )

    assert set(bound_graph) == bound_before, (
        "Context resolution must preserve its bound input graph."
    )
    assert set(schema_graph) == schema_before, (
        "Context resolution must preserve the Logical Schema Model."
    )
    assert bound_before.issubset(set(output_graph)), (
        "The downstream graph must retain the upstream knowledge."
    )

    # Verify that downstream consumers can use serialized RDF output.
    downstream_graph = Graph().parse(
        data=output_graph.serialize(format="turtle"),
        format="turtle",
    )

    contexts = set(
        downstream_graph.objects(
            constraint,
            CV.applicableContext,
        )
    )
    assert len(contexts) == 1, (
        "IT-53R1S1 requires exactly one applicable context "
        "for the original normalized constraint."
    )
    context = next(iter(contexts))
    assert isinstance(context, URIRef)
    assert (
        context,
        RDF.type,
        CV.ConstraintContext,
    ) in downstream_graph

    path_heads = list(
        downstream_graph.objects(context, CV.schemaPath)
    )
    assert len(path_heads) == 1, (
        "The applicable context must identify its schema path."
    )
    path_resources = list(
        Collection(downstream_graph, path_heads[0])
    )
    assert len(path_resources) == len(expected_path_resources)
    assert set(path_resources) == expected_path_resources, (
        "The resolved path must preserve the exact governed "
        "Logical Schema identities for the selected source context."
    )
    assert excluded_parent not in path_resources, (
        "The same data point name must not select the other context."
    )

    assert set(
        downstream_graph.objects(
            constraint,
            CV.boundLogicalSchemaResource,
        )
    ) == bound_resources

    assert set(
        downstream_graph.objects(
            context,
            CV.hasSourceContext,
        )
    ) == source_context_nodes, (
        "The context must retain links to the governed source context."
    )
    assert (
        context,
        PROV.wasDerivedFrom,
        source_constraint,
    ) in downstream_graph, (
        "The context must be traceable to its governed source constraint."
    )
    assert (
        context,
        PROV.wasDerivedFrom,
        LOGICAL_SCHEMA_MODEL_IRI,
    ) in downstream_graph, (
        "The context must be traceable to the Logical Schema Model."
    )

    stage_result = read_construction_stage_result(
        exchange_graph=downstream_graph,
        result_id=str(result.result_id),
    )
    assert stage_result.constraint_id == str(constraint)
    assert stage_result.construction_stage == "context-resolution"
    assert stage_result.construction_status == "GREEN"
    assert stage_result.available_for_downstream is True
    assert (
        result.result_id,
        UADEX.stageKnowledge,
        context,
    ) in downstream_graph