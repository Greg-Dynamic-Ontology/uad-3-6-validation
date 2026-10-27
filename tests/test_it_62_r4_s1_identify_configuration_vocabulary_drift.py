"""IT-62R4S1: detect new undefined terms on successive synchronization checks."""

from uuid import uuid4

import pytest
from rdflib import Graph, Literal, Namespace, RDF, RDFS
from rdflib.compare import isomorphic

from app.services.configuration_knowledge import validate_configuration_vocabulary


CFG = Namespace("https://dynamicontology.com/uad36/configuration#")


def _copy(graph: Graph) -> Graph:
    snapshot = Graph()
    for triple in graph:
        snapshot.add(triple)
    return snapshot


@pytest.mark.parametrize(
    "add_class, add_property",
    [(True, False), (False, True), (True, True)],
    ids=["new-class", "new-property", "new-class-and-property"],
)
def test_it_62_r4_s1_identifies_new_undefined_configuration_terms(
    add_class: bool, add_property: bool,
) -> None:
    token = uuid4().hex
    application = CFG[f"application-{token}"]
    new_class = CFG[f"NewConfigurationClass-{token}"]
    new_property = CFG[f"newConfigurationProperty-{token}"]
    configuration = Graph()
    configuration.add((application, RDF.type, CFG.ApplicationConfiguration))
    vocabulary = Graph()
    vocabulary.add((CFG.ApplicationConfiguration, RDF.type, RDFS.Class))

    initial = validate_configuration_vocabulary(
        configuration_graph=configuration, vocabulary_graph=vocabulary,
    )
    assert initial.conforms is True
    assert tuple(initial.diagnostics) == ()

    if add_class:
        configuration.add((application, RDF.type, new_class))
    if add_property:
        configuration.add((application, new_property, Literal("New setting")))

    changed_configuration = _copy(configuration)
    unchanged_vocabulary = _copy(vocabulary)
    drift = validate_configuration_vocabulary(
        configuration_graph=configuration, vocabulary_graph=vocabulary,
    )

    assert drift.conforms is False, (
        "IT-62R4S1 requires a fresh synchronization check to detect newly "
        "used terms, even when the same graphs previously passed validation."
    )
    expected_classes = {new_class} if add_class else set()
    expected_properties = {new_property} if add_property else set()
    assert set(drift.undefined_classes) == expected_classes
    assert set(drift.undefined_properties) == expected_properties
    messages = tuple(drift.diagnostics)
    assert messages and all(isinstance(message, str) and message.strip() for message in messages)
    for term in expected_classes | expected_properties:
        assert any(str(term) in message for message in messages), (
            f"Vocabulary drift diagnostics must identify {term}."
        )
    assert isomorphic(configuration, changed_configuration)
    assert isomorphic(vocabulary, unchanged_vocabulary), (
        "The check must report missing definitions without inventing them."
    )

    # Synchronization is restored by explicit vocabulary definitions.
    if add_class:
        vocabulary.add((new_class, RDF.type, RDFS.Class))
    if add_property:
        vocabulary.add((new_property, RDF.type, RDF.Property))
    updated_vocabulary = _copy(vocabulary)
    synchronized = validate_configuration_vocabulary(
        configuration_graph=configuration, vocabulary_graph=vocabulary,
    )
    assert synchronized.conforms is True
    assert tuple(synchronized.undefined_classes) == ()
    assert tuple(synchronized.undefined_properties) == ()
    assert tuple(synchronized.diagnostics) == ()
    assert isomorphic(configuration, changed_configuration)
    assert isomorphic(vocabulary, updated_vocabulary)
