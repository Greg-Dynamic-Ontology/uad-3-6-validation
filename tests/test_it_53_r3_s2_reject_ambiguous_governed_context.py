"""IT-53R3S2: reject incompatible candidate contexts and request review."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.collection import Collection

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
LSM = Namespace(
    "https://dynamicontology.com/uad36/logical-schema#"
)

TEST_NAMESPACE = "urn:uad36:test:it53r3s2:"
CONTEXT_NAMESPACES = (
    f"{TEST_NAMESPACE}context-a:",
    f"{TEST_NAMESPACE}context-b:",
)


def _qname_resource(
    graph: Graph,
    namespace: str,
    local_name: str,
) -> URIRef:
    matches = {
        resource
        for resource in graph.subjects(
            LSM.local_name,
            Literal(local_name),
        )
        if (
            resource,
            LSM.namespace,
            Literal(namespace),
        ) in graph
        and (
            resource,
            RDF.type,
            LSM.QName,
        ) in graph
    }
    assert len(matches) == 1
    resource = next(iter(matches))
    assert isinstance(resource, URIRef)
    return resource


def _ambiguous_schema_fixture() -> tuple[Graph, set]:
    """Create two matching paths that share one terminal declaration."""
    target = ElementDeclaration(
        name=QName(TEST_NAMESPACE, "AddressLineText"),
    )
    roots = {}
    definitions = {}

    for namespace in CONTEXT_NAMESPACES:
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
            (TEST_NAMESPACE, *CONTEXT_NAMESPACES)
        ),
        elements=roots,
        complex_types=definitions,
    )
    serialized = logical_schema_model_to_graph(model).serialize(
        format="turtle"
    )
    graph = Graph().parse(
        data=serialized,
        format="turtle",
    )

    terminal = _qname_resource(
        graph,
        TEST_NAMESPACE,
        "AddressLineText",
    )
    expected_paths = {
        (
            _qname_resource(graph, namespace, "PROPERTY"),
            _qname_resource(graph, namespace, "ADDRESS"),
            terminal,
        )
        for namespace in CONTEXT_NAMESPACES
    }
    assert len(expected_paths) == 2
    return graph, expected_paths


def test_it_53_r3_s2_rejects_incompatible_contexts_and_routes_for_review(
    tmp_path: Path,
) -> None:
    token = uuid4().hex
    source_identity = f"{TEST_NAMESPACE}source:{token}"
    source_path = "/PROPERTY/ADDRESS/AddressLineText"

    governed_source = {
        "unique_id": f"IT-53R3S2-{token}",
        "data_point_name": "AddressLineText",
        "source_rule_id": f"IT-53R3S2-{token}",
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

    schema_graph, expected_paths = _ambiguous_schema_fixture()
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
        "The terminal data point must already have one valid binding."
    )

    source_context_nodes = set(
        bound_graph.objects(
            constraint,
            CV.hasSourceContext,
        )
    )
    assert source_context_nodes

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
            "IT-53R3S2 requires a governed EXCEPTION recording "
            "both candidate contexts and routing the constraint "
            "for review. The resolver instead raised an "
            f"uncontracted ValueError: {error}",
            pytrace=False,
        )

    assert set(bound_graph) == bound_before
    assert set(schema_graph) == schema_before
    assert bound_before.issubset(set(output_graph))

    downstream_graph = Graph().parse(
        data=output_graph.serialize(format="turtle"),
        format="turtle",
    )
    recorded = read_construction_stage_result(
        exchange_graph=downstream_graph,
        result_id=str(result.result_id),
    )

    assert recorded.constraint_id == str(constraint)
    assert recorded.construction_stage == "context-resolution"
    assert recorded.construction_status == "EXCEPTION"
    assert recorded.requires_review is True, (
        "Ambiguous context must route the constraint for review."
    )
    assert recorded.available_for_downstream is False
    assert recorded.exception_reason

    assert not list(
        downstream_graph.objects(
            constraint,
            CV.applicableContext,
        )
    ), "Neither candidate may be selected as the applicable context."

    assert not list(
        downstream_graph.objects(
            result.result_id,
            UADEX.stageKnowledge,
        )
    ), "The exception must not advertise successful downstream knowledge."

    candidates = set(
        downstream_graph.objects(
            result.result_id,
            CV.candidateContext,
        )
    )
    assert len(candidates) == 2, (
        "The exception must retain both incompatible candidate contexts."
    )

    actual_paths = set()
    for candidate in candidates:
        assert isinstance(candidate, URIRef)
        heads = list(
            downstream_graph.objects(
                candidate,
                CV.schemaPath,
            )
        )
        assert len(heads) == 1
        path = tuple(
            Collection(downstream_graph, heads[0])
        )
        actual_paths.add(path)

        assert path in expected_paths, (
            "Each candidate must preserve its exact governed schema "
            "identities and path order."
        )

    assert actual_paths == expected_paths, (
        "The exception must record every candidate without "
        "dropping or substituting a path."
    )

    assert set(
        downstream_graph.objects(
            constraint,
            CV.hasSourceContext,
        )
    ) == source_context_nodes