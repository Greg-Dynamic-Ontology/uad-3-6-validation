"""IT-62R1S1: reject and diagnose every undefined configuration class/property."""

from importlib import import_module, util
from uuid import uuid4

import pytest
from rdflib import Graph, Literal, Namespace, RDF, RDFS
from rdflib.compare import isomorphic


CFG = Namespace("https://dynamicontology.com/uad36/configuration#")
MODULE = "app.services.configuration_knowledge"


def _copy(graph):
    saved = Graph()
    for triple in graph:
        saved.add(triple)
    return saved


def _validator():
    assert util.find_spec(MODULE) is not None, (
        "IT-62R1S1 requires app.services.configuration_knowledge to reject "
        "and identify undefined configuration classes and properties."
    )

    operation = getattr(
        import_module(MODULE),
        "validate_configuration_vocabulary",
        None,
    )
    assert callable(operation), (
        "IT-62R1S1 requires validate_configuration_vocabulary()."
    )
    return operation


@pytest.mark.parametrize(
    "class_count, property_count, apparent_definition",
    [
        (1, 0, "none"),
        (0, 1, "none"),
        (2, 3, "none"),
        (2, 2, "labels-only"),
        (1, 1, "wrong-kind"),
    ],
    ids=[
        "undefined-class",
        "undefined-property",
        "all-undefined-terms",
        "labels-are-not-definitions",
        "wrong-definition-kind",
    ],
)
def test_it_62_r1_s1_rejects_and_identifies_every_undefined_configuration_term(
    class_count: int,
    property_count: int,
    apparent_definition: str,
) -> None:
    token = uuid4().hex
    application = CFG[f"application-{token}"]
    workbook = CFG[f"workbook-{token}"]
    other_instance = CFG[f"instance-{token}"]

    unknown_classes = tuple(
        CFG[f"MissingClass-{token}-{index}"]
        for index in range(class_count)
    )
    unknown_properties = tuple(
        CFG[f"missingProperty-{token}-{index}"]
        for index in range(property_count)
    )

    vocabulary = Graph()
    for triple in (
        (CFG.ApplicationConfiguration, RDF.type, RDFS.Class),
        (CFG.GovernedSourceArtifact, RDF.type, RDFS.Class),
        (CFG.activeComplianceSource, RDF.type, RDF.Property),
    ):
        vocabulary.add(triple)

    configuration = Graph()
    for triple in (
        (application, RDF.type, CFG.ApplicationConfiguration),
        (
            application,
            RDFS.label,
            Literal("Configuration using undefined terms"),
        ),
        (application, CFG.activeComplianceSource, workbook),
        (workbook, RDF.type, CFG.GovernedSourceArtifact),
    ):
        configuration.add(triple)

    # Repeat each use to verify that diagnostics report terms once.
    for term in unknown_classes:
        configuration.add((application, RDF.type, term))
        configuration.add((other_instance, RDF.type, term))

    for term in unknown_properties:
        configuration.add((application, term, workbook))
        configuration.add(
            (other_instance, term, Literal("Repeated property use"))
        )

    if apparent_definition == "labels-only":
        for term in (*unknown_classes, *unknown_properties):
            vocabulary.add(
                (
                    term,
                    RDFS.label,
                    Literal("A label is not a class/property definition"),
                )
            )
            vocabulary.add(
                (
                    term,
                    RDFS.comment,
                    Literal("Neither is a descriptive comment"),
                )
            )

    elif apparent_definition == "wrong-kind":
        for term in unknown_classes:
            vocabulary.add((term, RDF.type, RDF.Property))

        for term in unknown_properties:
            vocabulary.add((term, RDF.type, RDFS.Class))

    original_configuration = _copy(configuration)
    original_vocabulary = _copy(vocabulary)

    result = _validator()(
        configuration_graph=configuration,
        vocabulary_graph=vocabulary,
    )

    assert getattr(result, "conforms", None) is False, (
        "IT-62R1S1 requires vocabulary validation to reject configuration "
        "RDF when a used configuration class or property lacks an "
        "appropriate definition."
    )

    assert set(result.undefined_classes) == set(unknown_classes)
    assert set(result.undefined_properties) == set(unknown_properties)

    assert len(result.undefined_classes) == len(unknown_classes), (
        "Repeated uses must not duplicate class diagnostics."
    )
    assert len(result.undefined_properties) == len(unknown_properties), (
        "Repeated uses must not duplicate property diagnostics."
    )

    diagnostics = tuple(result.diagnostics)
    assert all(
        isinstance(message, str) and message.strip()
        for message in diagnostics
    )

    for term in unknown_classes:
        assert any(
            str(term) in message and "class" in message.casefold()
            for message in diagnostics
        ), f"The diagnostic must identify undefined configuration class {term}."

    for term in unknown_properties:
        assert any(
            str(term) in message and "property" in message.casefold()
            for message in diagnostics
        ), (
            "The diagnostic must identify undefined configuration "
            f"property {term}."
        )

    # Instance identities are not class/property vocabulary uses.
    for instance in (application, workbook, other_instance):
        assert instance not in result.undefined_classes
        assert instance not in result.undefined_properties

    assert isomorphic(configuration, original_configuration)
    assert isomorphic(vocabulary, original_vocabulary)