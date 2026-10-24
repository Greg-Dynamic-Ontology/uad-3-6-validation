"""IT-57R1S1: project one real SHACL violation into one governed finding."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from pyshacl import validate
from rdflib import Graph, Literal, Namespace, RDF
from rdflib.collection import Collection
from rdflib.namespace import PROV, SH

from app.services.shacl_generation_agent import generate_governed_constraint_shacl
from app.services.validation_finding_projection import project_governed_findings


CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")


def test_it_57_r1_s1_projects_one_shacl_result_to_one_governed_finding(
    tmp_path: Path,
) -> None:
    ns = Namespace(f"urn:uad36:test:it57r1s1:{uuid4().hex}:")
    constraint = ns.constraint
    source = ns.source_constraint
    source_rule = ns.source_rule
    focus = ns.appraisal_property
    violation_kind = ns.MissingRequiredValue
    severity = "Fatal"
    requirement = Literal("Provide the governed value for each applicable property.")
    bound = Graph()
    for triple in (
        (constraint, RDF.type, CV.NormalizedConstraint),
        (constraint, CV.requirementText, requirement),
        (constraint, CV.violationCondition, Literal("The governed value is absent.")),
        (constraint, CV.sourceConstraint, source),
        (constraint, CV.umdpRule, source_rule),
        (constraint, CV.severity, Literal(severity)),
        (constraint, CV.violationKind, violation_kind),
        (constraint, PROV.wasDerivedFrom, source),
        (constraint, CV.boundLogicalSchemaResource, ns.value_qname),
        (constraint, CV.applicableContext, ns.context),
        (constraint, CV.behaviorClassification, ns.classification),
        (constraint, CV.instanceRdfBinding, ns.binding),
        (ns.context, RDF.type, CV.ConstraintContext),
        (ns.context, CV.schemaPath, ns.schema_path),
        (ns.classification, RDF.type, CV.ValidationBehaviorClassification),
        (ns.classification, CV.applicableContext, ns.context),
        (ns.classification, CV.validationBehavior, ns.behavior),
        (ns.behavior, RDF.type, CV.ValidationBehavior),
        (ns.binding, RDF.type, CV.InstanceRdfBinding),
        (ns.binding, CV.boundLogicalSchemaResource, ns.value_qname),
        (ns.binding, CV.applicableContext, ns.context),
        (ns.binding, CV.behaviorClassification, ns.classification),
        (ns.binding, CV.validationBehavior, ns.behavior),
        (ns.binding, CV.focusClass, ns.Property),
        (ns.binding, CV.valuePredicate, ns.required_value),
        (ns.binding, CV.predicatePath, ns.predicate_path),
    ):
        bound.add(triple)
    Collection(bound, ns.schema_path, [ns.property_qname, ns.value_qname])
    Collection(bound, ns.predicate_path, [ns.required_value])
    patterns = Graph()
    patterns.add((ns.behavior, CV.shaclImplementationPattern, ns.pattern))
    patterns.add((ns.pattern, RDF.type, CV.ShaclImplementationPattern))
    patterns.add((ns.pattern, CV.propertyShapeTemplate, ns.template))
    patterns.add((ns.template, RDF.type, SH.PropertyShape))
    patterns.add((ns.template, SH.minCount, Literal(1)))

    # Production generation supplies the executable shape and constraint
    # linkage. The test does not add a synthetic source-shape shortcut.
    governed = Graph()
    artifact = tmp_path / "governed-shapes" / "constraint.ttl"
    generate_governed_constraint_shacl(
        bound_graph=bound,
        implementation_patterns_graph=patterns,
        constraint_id=str(constraint),
        output_path=artifact,
        output_graph=governed,
    )
    assert artifact.is_file()
    shapes = Graph().parse(artifact, format="turtle")
    representations = set(governed.objects(constraint, CV.shaclRepresentation))
    assert len(representations) == 1
    shape = next(iter(representations))
    assert (shape, CV.implementsConstraint, constraint) in governed
    property_shapes = set(shapes.objects(shape, SH.property))
    assert len(property_shapes) == 1
    property_shape = next(iter(property_shapes))

    # The runtime data intentionally lacks the value required by the shape.
    instance = Graph()
    instance.add((focus, RDF.type, ns.Property))
    conforms, runtime_report, _ = validate(data_graph=instance, shacl_graph=shapes)
    assert not conforms
    report = Graph().parse(data=runtime_report.serialize(format="turtle"), format="turtle")
    results = set(report.subjects(RDF.type, SH.ValidationResult))
    assert len(results) == 1, "Test setup must produce exactly one real SHACL violation."
    validation_result = next(iter(results))
    assert (validation_result, SH.sourceShape, property_shape) in report
    assert (validation_result, SH.focusNode, focus) in report
    assert (validation_result, SH.resultSeverity, SH.Violation) in report
    report_before = set(report)
    governed_before = set(governed)

    projected = project_governed_findings(
        shacl_result_graph=report,
        governed_constraint_graph=governed,
    )
    assert set(report) == report_before
    assert set(governed) == governed_before
    assert len(projected.findings) == 1, (
        "IT-57R1S1 requires one governed finding for the actual pySHACL result, "
        "including its RDF result identity and the property shape's link "
        "through the generated NodeShape to the governed constraint. "
        f"The projector returned {len(projected.findings)} findings."
    )
    finding = projected.findings[0]
    assert finding.governed_constraint == constraint
    assert finding.source_constraint == source
    assert finding.umdp_rule == source_rule
    assert finding.severity == severity, "Use governed Fatal severity, not SHACL Violation."
    assert finding.violation_kind == violation_kind
    assert finding.focus_node == focus
    assert finding.shacl_validation_result == validation_result
    assert (finding.governed_constraint, PROV.wasDerivedFrom, finding.source_constraint) in governed
    assert (finding.governed_constraint, CV.umdpRule, finding.umdp_rule) in governed
    assert (finding.shacl_validation_result, RDF.type, SH.ValidationResult) in report
