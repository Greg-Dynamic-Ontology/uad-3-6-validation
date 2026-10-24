"""IT-58R2S1: stop at an unverified stage and persist its actual RDF state."""

from __future__ import annotations

import csv
from importlib import import_module
from pathlib import Path
from uuid import uuid4

import pytest
from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import PROV, SH

from app.services.construction_exchange import (
    UADEX,
    read_construction_stage_result,
    record_construction_stage_result,
)
from app.services.governed_constraint_source_reader import EXPECTED_COLUMNS


CFG = Namespace("https://dynamicontology.com/uad36/configuration#")
CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")
NORMALIZATION = "normalized-constraint-representation"
WORKERS = (
    ("logical_schema_binding_agent", "bind_normalized_constraint_to_logical_schema",
     "logical-schema-binding", "normalized_graph"),
    ("context_resolution_agent", "resolve_bound_constraint_context",
     "context-resolution", "bound_graph"),
    ("constraint_behavior_classification", "classify_governed_constraint_behavior",
     "validation-behavior", "context_graph"),
    ("instance_rdf_binding_agent", "bind_governed_constraint_to_instance_rdf",
     "instance-rdf-binding", "classified_graph"),
    ("shacl_generation_agent", "generate_governed_constraint_shacl",
     "shacl-representation", "bound_graph"),
)


@pytest.mark.parametrize("stopped_index", range(4), ids=[
    "logical-schema-binding", "context-resolution", "validation-behavior",
    "instance-rdf-binding",
])
@pytest.mark.parametrize("status,available", [
    ("RED", True),
    ("PENDING", False),
    ("GREEN", False),
], ids=["red-even-if-marked-available", "pending", "green-not-available"])
def test_it_58_r2_s1_blocks_downstream_and_persists_unverified_stage_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stopped_index: int,
    status: str,
    available: bool,
) -> None:
    pipeline = import_module("app.services.constraint_production_pipeline")
    ns = Namespace(f"urn:uad36:test:it58r2s1:{uuid4().hex}:")
    unique_id = "0" + uuid4().hex
    row = dict.fromkeys(EXPECTED_COLUMNS, "")
    row.update({
        "Unique ID": unique_id,
        "Primary Data Element": "AddressLineText",
        "Message ID": "test-rule-" + uuid4().hex,
        "Message Text": "Provide the property address line.",
        "Rule Logic": "The property address line is absent.",
        "Severity": "Fatal",
        "Property Affected": "/PROPERTY/ADDRESS/AddressLineText",
        "Data Point Name / Value": "AddressLineText",
        " xPath": "/PROPERTY/ADDRESS/AddressLineText",
    })
    source_path = tmp_path / "constraints.csv"
    with source_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=EXPECTED_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    source_iri = URIRef(f"urn:uad36:governed-source:{source_path.name}#row=2")
    configuration = Graph()
    for triple in (
        (ns.configuration, RDF.type, CFG.ApplicationConfiguration),
        (ns.configuration, CFG.hasSourceWorkbooks, ns.collection),
        (ns.configuration, CFG.activeComplianceSource, ns.source),
        (ns.collection, RDF.type, CFG.GovernedSourceWorkbookCollection),
        (ns.collection, CFG.containsWorkbook, ns.source),
        (ns.source, RDF.type, CFG.GovernedSourceArtifact),
        (ns.source, CFG.sourceFileLocation, Literal(str(source_path))),
        (ns.source, CFG.sourceFormat, Literal("csv")),
    ):
        configuration.add(triple)
    configuration_path = tmp_path / "configuration.ttl"
    configuration.serialize(destination=configuration_path, format="turtle")
    originals = (source_path.read_bytes(), configuration_path.read_bytes())
    calls = []
    stopped_output = Graph()
    stopped_result_ids = []
    stopped_stage = WORKERS[stopped_index][2]

    def controlled_worker(index, stage, input_name):
        def execute(**kwargs):
            assert index <= stopped_index, (
                "Unverified upstream output reached a downstream production worker."
            )
            assert index == len(calls), "Workers ran out of order or a stage was retried."
            incoming = kwargs[input_name]
            preceding = NORMALIZATION if index == 0 else WORKERS[index - 1][2]
            prior_ids = set(incoming.subjects(UADEX.constructionStage, Literal(preceding)))
            assert len(prior_ids) == 1
            prior = read_construction_stage_result(
                exchange_graph=incoming, result_id=str(next(iter(prior_ids))),
            )
            assert prior.construction_status == "GREEN"
            assert prior.available_for_downstream is True
            output = kwargs["output_graph"]
            for triple in incoming:
                output.add(triple)
            record = record_construction_stage_result(
                output_graph=output,
                constraint_id=kwargs["constraint_id"],
                construction_stage=stage,
                construction_status=status if index == stopped_index else "GREEN",
            )
            output.add((record.result_id, UADEX.availableForDownstream,
                        Literal(available if index == stopped_index else True)))
            # Preserve identifiable worker output as well as its exchange status.
            knowledge = URIRef(f"{record.result_id}/knowledge")
            output.add((record.result_id, UADEX.stageKnowledge, knowledge))
            output.add((knowledge, PROV.wasDerivedFrom, source_iri))
            output.add((knowledge, CV.governedUniqueId, Literal(unique_id)))
            calls.append(stage)
            if index == stopped_index:
                stopped_result_ids.append(record.result_id)
                for triple in output:
                    stopped_output.add(triple)
            return record
        return execute

    # These controlled workers isolate orchestration from stage-specific
    # interpretation. Normalization remains real. No production code changes.
    for index, (module_name, operation_name, stage, input_name) in enumerate(WORKERS):
        module = import_module(f"app.services.{module_name}")
        real = getattr(module, operation_name)
        controlled = controlled_worker(index, stage, input_name)
        monkeypatch.setattr(module, operation_name, controlled)
        if getattr(pipeline, operation_name, None) is real:
            monkeypatch.setattr(pipeline, operation_name, controlled)

    output_directory = tmp_path / "production-artifacts"
    batch_path = tmp_path / "batch-state" / "results.ttl"
    returned = None
    try:
        returned = pipeline.process_governed_source_row(
            configuration_path=configuration_path,
            unique_id=unique_id,
            logical_schema_graph=Graph(),
            projection_model_graph=Graph(),
            established_behaviors_graph=Graph(),
            implementation_patterns_graph=Graph(),
            output_directory=output_directory,
            batch_results_path=batch_path,
        )
    except ValueError:
        # This scenario permits the existing stopped-row exception contract.
        # Raising alone is insufficient: the current state must also be saved.
        pass

    assert calls == [worker[2] for worker in WORKERS[:stopped_index + 1]]
    assert returned is None or not returned.is_complete
    assert len(stopped_result_ids) == 1
    assert batch_path.is_file(), "The stopped row has no persistent Batch Results Graph."
    batch = Graph().parse(batch_path, format="turtle")
    result_id = stopped_result_ids[0]
    assert (result_id, RDF.type, UADEX.ConstructionStageResult) in batch, (
        "IT-58R2S1 requires the Batch Results Graph to preserve the current "
        f"unverified {stopped_stage} result with its original RDF identity and status; "
        "recording only the preceding GREEN stage is insufficient."
    )
    assert set(stopped_output).issubset(set(batch)), (
        "The persisted stage state discarded unverified worker knowledge."
    )
    saved = read_construction_stage_result(exchange_graph=batch, result_id=str(result_id))
    assert saved.construction_stage == stopped_stage
    assert saved.construction_status == status
    assert saved.available_for_downstream is available
    constraint = URIRef(saved.constraint_id)
    saved_stages = {
        str(stage)
        for result in batch.subjects(UADEX.forConstraint, constraint)
        for stage in batch.objects(result, UADEX.constructionStage)
    }
    assert saved_stages == {NORMALIZATION, *calls}
    assert not list(batch.subjects(RDF.type, SH.NodeShape))
    assert not list(batch.subjects(RDF.type, SH.ValidationResult))
    assert not list(output_directory.rglob("constraint.ttl"))
    assert not list(output_directory.rglob("shapes.ttl"))
    assert (source_path.read_bytes(), configuration_path.read_bytes()) == originals
