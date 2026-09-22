from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import quote

from rdflib import Graph, Literal, Namespace, RDF, URIRef

from app.core.schema_source_iri import mint_schema_source_iri
from app.models.schema_model import QName


LOGICAL_SCHEMA = Namespace(
    "https://dynamicontology.com/uad36/logical-schema#"
)
LOGICAL_SCHEMA_MODEL_IRI = URIRef(
    "https://dynamicontology.com/uad36/logical-schema/model"
)
LOGICAL_SCHEMA_QNAME_BASE_IRI = (
    "https://dynamicontology.com/uad36/logical-schema/qname/"
)


def serialize_logical_schema_model(
    logical_schema_model: object,
    output_file: Path,
) -> Path:
    """
    Serialize an in-memory Logical Schema Model as RDF/Turtle.

    This preserves the runtime model structure without applying the
    Milestone 2 XSD-to-ontology projection rules.
    """
    graph = logical_schema_model_to_graph(logical_schema_model)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(
        destination=output_file,
        format="turtle",
        encoding="utf-8",
    )

    return output_file


def logical_schema_model_to_graph(
    logical_schema_model: object,
) -> Graph:
    """
    Convert an in-memory Logical Schema Model into an RDF graph.
    """
    graph = Graph()
    graph.bind("lsm", LOGICAL_SCHEMA)

    visited: dict[int, URIRef] = {}

    _add_value(
        graph=graph,
        subject=LOGICAL_SCHEMA_MODEL_IRI,
        predicate=RDF.type,
        value=logical_schema_model,
        path="model",
        visited=visited,
        root=True,
    )

    return graph


def _add_value(
    *,
    graph: Graph,
    subject: URIRef,
    predicate: URIRef,
    value: Any,
    path: str,
    visited: dict[int, URIRef],
    root: bool = False,
) -> None:
    if value is None:
        return

    if isinstance(value, Path):
        graph.add(
            (subject, predicate, mint_schema_source_iri(value))
        )
        return

    if _is_literal_value(value):
        graph.add((subject, predicate, _to_literal(value)))
        return

    if isinstance(value, dict):
        container = subject if root else _resource_iri(path)
        if not root:
            graph.add((subject, predicate, container))
        graph.add((container, RDF.type, LOGICAL_SCHEMA.Mapping))

        for index, key in enumerate(sorted(value, key=lambda item: str(item))):
            entry_path = f"{path}/entry/{index}"
            entry = _resource_iri(entry_path)
            graph.add((container, LOGICAL_SCHEMA.entry, entry))
            graph.add((entry, RDF.type, LOGICAL_SCHEMA.MappingEntry))

            _add_value(
                graph=graph,
                subject=entry,
                predicate=LOGICAL_SCHEMA.key,
                value=key,
                path=f"{entry_path}/key",
                visited=visited,
            )
            _add_value(
                graph=graph,
                subject=entry,
                predicate=LOGICAL_SCHEMA.value,
                value=value[key],
                path=f"{entry_path}/value",
                visited=visited,
            )
        return

    if isinstance(value, (list, tuple, set, frozenset)):
        container = subject if root else _resource_iri(path)
        if not root:
            graph.add((subject, predicate, container))
        graph.add((container, RDF.type, LOGICAL_SCHEMA.Collection))

        items = list(value)
        if isinstance(value, (set, frozenset)):
            items.sort(key=repr)

        for index, item in enumerate(items):
            _add_value(
                graph=graph,
                subject=container,
                predicate=LOGICAL_SCHEMA.member,
                value=item,
                path=f"{path}/member/{index}",
                visited=visited,
            )
        return

    object_id = id(value)
    resource = subject if root else visited.get(object_id)

    if resource is None:
        if root:
            resource = subject
        else:
            resource = _intrinsic_resource_iri(value) or _resource_iri(path)
        visited[object_id] = resource

    if not root:
        graph.add((subject, predicate, resource))

    graph.add(
        (
            resource,
            RDF.type,
            LOGICAL_SCHEMA[value.__class__.__name__],
        )
    )

    if is_dataclass(value):
        for field in fields(value):
            if not field.metadata.get("logical_schema", True):
                continue

            _add_value(
                graph=graph,
                subject=resource,
                predicate=LOGICAL_SCHEMA[field.name],
                value=getattr(value, field.name),
                path=f"{path}/{field.name}",
                visited=visited,
            )
        return

    attributes = {
        name: attribute
        for name, attribute in vars(value).items()
        if not name.startswith("_")
    }

    for name in sorted(attributes):
        _add_value(
            graph=graph,
            subject=resource,
            predicate=LOGICAL_SCHEMA[name],
            value=attributes[name],
            path=f"{path}/{name}",
            visited=visited,
        )


def _intrinsic_resource_iri(value: Any) -> URIRef | None:
    if isinstance(value, QName):
        return _qname_iri(value)

    return None


def _qname_iri(value: QName) -> URIRef:
    source_identity = value.clark_name
    encoded_identity = quote(source_identity, safe="")
    return URIRef(
        f"{LOGICAL_SCHEMA_QNAME_BASE_IRI}{encoded_identity}"
    )


def _resource_iri(path: str) -> URIRef:
    digest = sha256(path.encode("utf-8")).hexdigest()
    return URIRef(f"{LOGICAL_SCHEMA}resource-{digest}")


def _is_literal_value(value: Any) -> bool:
    return isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
            bytes,
            Enum,
        ),
    )


def _to_literal(value: Any) -> Literal:
    if isinstance(value, Enum):
        return Literal(value.value)

    return Literal(value)
