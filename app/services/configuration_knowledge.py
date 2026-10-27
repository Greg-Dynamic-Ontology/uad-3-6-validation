"""Validate application configuration knowledge against its supplied vocabulary."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.namespace import OWL


CFG = Namespace("https://dynamicontology.com/uad36/configuration#")
_CLASS_DEFINITION_TYPES = (RDFS.Class, OWL.Class)
_PROPERTY_DEFINITION_TYPES = (
    RDF.Property, OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty,
)


@dataclass(frozen=True)
class ConfigurationVocabularyValidationResult:
    """Vocabulary coverage, with every undefined term retained by RDF identity."""

    undefined_classes: tuple[URIRef, ...] = ()
    undefined_properties: tuple[URIRef, ...] = ()

    @property
    def conforms(self) -> bool:
        return not self.undefined_classes and not self.undefined_properties

    @property
    def diagnostics(self) -> tuple[str, ...]:
        return (
            *(f"Undefined configuration class: {term}" for term in self.undefined_classes),
            *(f"Undefined configuration property: {term}" for term in self.undefined_properties),
        )


def _is_configuration_term(term) -> bool:
    return isinstance(term, URIRef) and str(term).startswith(str(CFG))


def validate_configuration_vocabulary(
    *, configuration_graph: Graph, vocabulary_graph: Graph,
) -> ConfigurationVocabularyValidationResult:
    """Check explicit class/property definitions without altering either graph.

    Configuration classes are used as rdf:type objects; configuration
    properties are used as predicates. Merely naming a configuration individual
    in the cfg namespace does not make it a class or property use. RDF/RDFS/OWL
    built-ins and terms from other namespaces are outside this vocabulary check.

    A definition must be present in the supplied vocabulary graph with an
    appropriate RDFS/RDF or OWL type. Labels, instance descriptions and usage
    alone do not define a term. No definitions are invented or inferred, and no
    files, source workbooks or network resources are opened by this operation.
    """
    used_classes = {
        term for term in configuration_graph.objects(None, RDF.type)
        if _is_configuration_term(term)
    }
    used_properties = {
        term for term in configuration_graph.predicates()
        if _is_configuration_term(term)
    }
    defined_classes = {
        term for definition_type in _CLASS_DEFINITION_TYPES
        for term in vocabulary_graph.subjects(RDF.type, definition_type)
        if _is_configuration_term(term)
    }
    defined_properties = {
        term for definition_type in _PROPERTY_DEFINITION_TYPES
        for term in vocabulary_graph.subjects(RDF.type, definition_type)
        if _is_configuration_term(term)
    }
    return ConfigurationVocabularyValidationResult(
        undefined_classes=tuple(sorted(used_classes - defined_classes, key=str)),
        undefined_properties=tuple(sorted(used_properties - defined_properties, key=str)),
    )


@dataclass(frozen=True)
class ActiveComplianceSourceValidationResult:
    """An accepted governed workbook identity or source-selection diagnostics."""

    active_source: URIRef | None = None
    diagnostics: tuple[str, ...] = ()

    @property
    def conforms(self) -> bool:
        return self.active_source is not None and not self.diagnostics


def validate_active_compliance_source(
    *, configuration_graph: Graph, configuration_id: URIRef,
) -> ActiveComplianceSourceValidationResult:
    """Validate selection within this configuration's explicit collection.

    Other registered workbooks remain available. Validation neither selects a
    default nor changes configuration triples, and does not open source files.
    Vocabulary validation remains a separate check.
    """
    active_sources = set(configuration_graph.objects(
        configuration_id, CFG.activeComplianceSource,
    ))
    collections = set(configuration_graph.objects(
        configuration_id, CFG.hasSourceWorkbooks,
    ))
    diagnostics = []
    if len(active_sources) != 1:
        diagnostics.append(
            f"{configuration_id}: cfg:activeComplianceSource must identify "
            f"exactly one workbook; found {len(active_sources)}."
        )
    if len(collections) != 1:
        diagnostics.append(
            f"{configuration_id}: cfg:hasSourceWorkbooks must identify "
            f"exactly one source-workbook collection; found {len(collections)}."
        )
    if diagnostics:
        return ActiveComplianceSourceValidationResult(
            diagnostics=tuple(diagnostics),
        )

    selected = next(iter(active_sources))
    collection = next(iter(collections))
    if not isinstance(selected, URIRef):
        return ActiveComplianceSourceValidationResult(diagnostics=(
            f"{configuration_id}: active compliance source must be a governed "
            f"workbook IRI; found {selected!r}.",
        ))
    if (collection, CFG.containsWorkbook, selected) not in configuration_graph:
        return ActiveComplianceSourceValidationResult(diagnostics=(
            f"{configuration_id}: active compliance source {selected} is not "
            f"listed by cfg:containsWorkbook in source collection {collection}.",
        ))
    return ActiveComplianceSourceValidationResult(active_source=selected)


@dataclass(frozen=True)
class WorkbookSourceDefinitionValidationResult:
    """A workbook's accepted source details or configuration diagnostics."""

    workbook_id: URIRef
    source_file_location: str | None = None
    rule_data_sheet_name: str | None = None
    diagnostics: tuple[str, ...] = ()

    @property
    def conforms(self) -> bool:
        return (
            self.source_file_location is not None
            and self.rule_data_sheet_name is not None
            and not self.diagnostics
        )


def validate_workbook_source_definition(
    *, configuration_graph: Graph, workbook_id: URIRef,
) -> WorkbookSourceDefinitionValidationResult:
    """Validate explicit location and rule-data worksheet values in RDF.

    This checks configuration knowledge, without opening the file or checking
    worksheet existence. Values are preserved exactly. Descriptive source tabs
    and properties of other workbooks do not participate in this selection.
    """
    values = {}
    diagnostics = []
    for predicate in (CFG.sourceFileLocation, CFG.ruleDataSheetName):
        configured = set(configuration_graph.objects(workbook_id, predicate))
        if len(configured) != 1:
            diagnostics.append(
                f"{workbook_id}: {predicate} must have exactly one value; "
                f"found {len(configured)}."
            )
            continue
        value = next(iter(configured))
        if not isinstance(value, Literal) or not str(value).strip():
            diagnostics.append(
                f"{workbook_id}: {predicate} must be a nonblank literal."
            )
            continue
        values[predicate] = str(value)

    if diagnostics:
        return WorkbookSourceDefinitionValidationResult(
            workbook_id=workbook_id, diagnostics=tuple(diagnostics),
        )
    return WorkbookSourceDefinitionValidationResult(
        workbook_id=workbook_id,
        source_file_location=values[CFG.sourceFileLocation],
        rule_data_sheet_name=values[CFG.ruleDataSheetName],
    )


__all__ = [
    "ConfigurationVocabularyValidationResult", "validate_configuration_vocabulary",
    "ActiveComplianceSourceValidationResult", "validate_active_compliance_source",
    "WorkbookSourceDefinitionValidationResult", "validate_workbook_source_definition",
]
