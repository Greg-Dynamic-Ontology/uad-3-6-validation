"""IT-53R2S1: preserve ordered governed schema paths."""

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
TEST_NAMESPACE = "urn:uad36:test:it53r2s1:"


def _schema_fixture() -> Graph:
    """Build two parent contexts sharing the same address data point."""

    def qname(name: str) -> QName:
        return QName(TEST_NAMESPACE, name)

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

    definitions = [
        ComplexTypeDefinition(
            name=qname("ADDRESS_TYPE"),
            content=ModelGroup(
                kind=ModelGroupKind.SEQUENCE,
                elements=(target,),
            ),
        ),
        *[
            ComplexTypeDefinition(
                name=qname(f"{parent}_TYPE"),
                content=ModelGroup(
                    kind=ModelGroupKind.SEQUENCE,
                    elements=(address,),
                ),
            )
            for parent in ("PROPERTY", "BORROWER")
        ],
    ]

    model = SchemaModel(
        target_namespace=TEST_NAMESPACE,
        elements={
            declaration.name: declaration
            for declaration in roots
        },
        complex_types={
            definition.name: definition
            for definition in definitions
        },
    )
    return logical_schema_model_to_graph(model)


def _schema_qname(graph: Graph, local_name: str) -> URIRef:
    matches = {
        resource
        for resource in graph.subjects(
            LSM.local_name,
            Literal(local_name),
        )
        if (resource, RDF.type, LSM.QName) in graph
    }
    assert len(matches) == 1, (
        f"The test model must identify one QName for {local_name!r}."
    )
    resource = next(iter(matches))
    assert isinstance(resource, URIRef)
    return resource


def _resolve_fixture_constraint(
    *,
    parent: str,
    schema_graph: Graph,
    output_graph: Graph,
    tmp_path: Path,
) -> tuple[URIRef, URIRef]:
    token = uuid4().hex
    source_constraint = f"{TEST_NAMESPACE}source:{token}"

    governed_source = {
        "unique_id": f"IT-53R2S1-{token}",
        "data_point_name": "AddressLineText",
        "source_rule_id": f"IT-53R2S1-{token}",
        "requirement_text": (
            "Provide the address line in the governed context."
        ),
        "violation_condition": (
            "The address line is absent in the governed context."
        ),
        "severity": "Fatal",
        "context_fields": [
            f"/{parent}/ADDRESS/AddressLineText"
        ],
        "source_locator": source_constraint,
        "source_constraint_uri": source_constraint,
    }

    normalized_path = tmp_path / f"{parent}-normalized.ttl"
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

    bindings = set(
        bound_graph.objects(
            constraint,
            CV.boundLogicalSchemaResource,
        )
    )
    assert len(bindings) == 1
    bound_resource = next(iter(bindings))

    resolve_bound_constraint_context(
        bound_graph=bound_graph,
        logical_schema_graph=schema_graph,
        constraint_id=str(constraint),
        output_graph=output_graph,
    )
    return constraint, bound_resource


@pytest.mark.parametrize(
    "serialization_format",
    ("turtle", "xml"),
    ids=("turtle", "rdf-xml"),
)
def test_it_53_r2_s1_records_an_ordered_governed_schema_path(
    serialization_format: str,
    tmp_path: Path,
) -> None:
    schema_graph = _schema_fixture()
    output_graph = Graph()

    constraints = {
        parent: _resolve_fixture_constraint(
            parent=parent,
            schema_graph=schema_graph,
            output_graph=output_graph,
            tmp_path=tmp_path,
        )
        for parent in ("PROPERTY", "BORROWER")
    }

    # A downstream consumer receives RDF, not the resolver's Python objects.
    downstream_graph = Graph().parse(
        data=output_graph.serialize(
            format=serialization_format,
        ),
        format=serialization_format,
    )

    contexts = {}
    paths = {}

    for parent, (constraint, bound_resource) in constraints.items():
        candidates = set(
            downstream_graph.objects(
                constraint,
                CV.applicableContext,
            )
        )
        assert len(candidates) == 1
        context = next(iter(candidates))
        contexts[parent] = context

        assert (
            context,
            RDF.type,
            CV.ConstraintContext,
        ) in downstream_graph

        heads = list(
            downstream_graph.objects(
                context,
                CV.schemaPath,
            )
        )
        assert len(heads) == 1

        actual_path = list(
            Collection(downstream_graph, heads[0])
        )
        expected_path = [
            _schema_qname(schema_graph, parent),
            _schema_qname(schema_graph, "ADDRESS"),
            _schema_qname(schema_graph, "AddressLineText"),
        ]

        assert actual_path == expected_path, (
            "The downstream RDF must preserve the governed path "
            "in parent-to-child order, using the exact schema IRIs."
        )
        paths[parent] = actual_path

        terminal_names = set(
            schema_graph.objects(bound_resource, LSM.name)
        )
        assert terminal_names == {actual_path[-1]}, (
            "The constrained data point must remain the terminal "
            "governed resource of the applicable path."
        )

        for resource in actual_path:
            assert isinstance(resource, URIRef)
            assert (
                resource,
                RDF.type,
                LSM.QName,
            ) in schema_graph

    assert contexts["PROPERTY"] != contexts["BORROWER"], (
        "Different applicable paths must have distinct context identities."
    )
    assert paths["PROPERTY"] != paths["BORROWER"], (
        "Downstream agents must distinguish the two applicable paths."
    )
    assert paths["PROPERTY"][-1] == paths["BORROWER"][-1], (
        "The distinction must survive even when both contexts "
        "share the exact same terminal data point."
    )