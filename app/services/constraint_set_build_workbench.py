"""Build an explicitly selected registered constraint set using IT-58."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.namespace import PROV

from app.services import constraint_production_pipeline
from app.services.construction_exchange import UADEX


CFG = Namespace("https://dynamicontology.com/uad36/configuration#")
CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")


@dataclass(frozen=True)
class ConstraintSetBuildResult:
    """Saved run identity and operator-facing construction summary."""

    run_id: str
    constraint_set_id: str
    constraint_set_label: str
    source_version: str
    status: str
    completed_row_count: int
    exception_row_count: int
    manifest_path: Path
    batch_results_path: Path
    run_directory: Path


def _one(graph: Graph, subject, predicate):
    values = set(graph.objects(subject, predicate))
    if len(values) != 1:
        raise ValueError(f"Build configuration must identify exactly one {predicate}.")
    return next(iter(values))


def _text(graph: Graph, subject, predicate) -> str:
    value = _one(graph, subject, predicate)
    if not isinstance(value, Literal) or not str(value).strip():
        raise ValueError(f"Build configuration requires nonblank text for {predicate}.")
    return str(value)


def _location(graph: Graph, subject, predicate, base: Path, *, existing: bool) -> Path:
    path = Path(_text(graph, subject, predicate))
    if not path.is_absolute():
        path = base / path
    path = path.resolve(strict=existing)
    if existing and not path.is_file():
        raise ValueError("A configured build input must identify an existing file.")
    return path


def _index_preserved_stages(manifest: Graph, run: URIRef, batch_path: Path, directory: Path) -> None:
    """Index original verified worker results; never regenerate stage RDF."""
    if not batch_path.exists():
        return
    batch = Graph().parse(batch_path, format="turtle")
    root = directory.resolve()
    indexed = Graph()
    indexed.bind("uadex", UADEX)
    for result in set(batch.subjects(RDF.type, UADEX.ConstructionStageResult)):
        if (result, UADEX.constructionStatus, Literal("GREEN")) not in batch:
            continue
        stage = _text(batch, result, UADEX.constructionStage)
        if stage not in constraint_production_pipeline.STAGES:
            raise ValueError("A saved worker result has an unknown production stage.")
        constraint = _one(batch, result, UADEX.forConstraint)
        location = _one(batch, result, UADEX.rdfSnapshotPath)
        if not isinstance(location, Literal):
            raise ValueError("A saved stage must identify its original snapshot path.")
        path = Path(str(location)).resolve(strict=True)
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("A saved stage snapshot must be inside its build run.")
        saved_bytes = path.read_bytes()
        digest = _one(batch, result, UADEX.snapshotSha256)
        if str(digest) != sha256(saved_bytes).hexdigest():
            raise ValueError("A saved stage snapshot no longer matches its recorded digest.")
        snapshot = Graph().parse(data=saved_bytes, format="turtle")
        for triple in (
            (result, RDF.type, UADEX.ConstructionStageResult),
            (result, UADEX.forConstraint, constraint),
            (result, UADEX.constructionStage, Literal(stage)),
            (result, UADEX.constructionStatus, Literal("GREEN")),
        ):
            if triple not in snapshot:
                raise ValueError("A saved snapshot does not preserve its original stage identity.")
            indexed.add(triple)
        activities = set(batch.objects(result, PROV.wasGeneratedBy))
        if not activities or set(snapshot.objects(result, PROV.wasGeneratedBy)) != activities:
            raise ValueError("A saved stage must preserve its actual execution provenance.")
        for activity in activities:
            if (activity, RDF.type, PROV.Activity) not in snapshot:
                raise ValueError("A saved stage is missing its execution activity.")
            indexed.add((result, PROV.wasGeneratedBy, activity))
            for triple in snapshot.triples((activity, None, None)):
                indexed.add(triple)
        for triple in (
            (run, CV.preservedStageResult, result),
            (result, CV.stageOrder, Literal(constraint_production_pipeline.STAGES.index(stage) + 1)),
            (result, UADEX.rdfSnapshotPath, location),
            (result, UADEX.snapshotSha256, digest),
        ):
            indexed.add(triple)
    # Publish the complete index only after every original snapshot was checked.
    for triple in indexed:
        manifest.add(triple)

def build_registered_constraint_set(
    *,
    configuration_path: str | Path,
    constraint_set_id: str,
    authority: str | None = None,
) -> ConstraintSetBuildResult:
    """Persist one distinct set-build run without modifying its source registry.

    Registry metadata selects the workbook, worksheet and governed version.
    A configured build profile supplies the four governed model graphs and
    output directory. IT-58 owns row selection, worker execution, stage gates,
    row exceptions and completion. No appraisal evaluation is performed here.
    """
    if not isinstance(constraint_set_id, str) or not constraint_set_id.strip():
        raise ValueError("Select a constraint set before starting a build.")
    configuration_path = Path(configuration_path).resolve(strict=True)
    base = configuration_path.parent
    registry = Graph().parse(configuration_path, format="turtle")
    roots = set(registry.subjects(RDF.type, CFG.ApplicationConfiguration))
    if len(roots) != 1:
        raise ValueError("Build requires one application configuration.")
    configuration = next(iter(roots))
    collection = _one(registry, configuration, CFG.hasConstraintSets)
    selected = URIRef(constraint_set_id.strip())
    if (collection, RDF.type, CFG.GovernedConstraintSetCollection) not in registry or (
        collection, CFG.containsConstraintSet, selected
    ) not in registry or (selected, RDF.type, CFG.GovernedConstraintSet) not in registry:
        raise ValueError("Select a registered governed constraint set.")
    governing_authority = _one(registry, selected, CFG.governingAuthority)
    if not isinstance(governing_authority, URIRef) or (
        governing_authority, RDF.type, CFG.GoverningAuthority
    ) not in registry:
        raise ValueError("The selected set must identify its registered governing authority.")
    if authority and authority != str(governing_authority):
        raise ValueError("The selected set does not belong to the chosen governing authority.")
    workbook = _one(registry, selected, CFG.sourceWorkbook)
    workbooks = _one(registry, configuration, CFG.hasSourceWorkbooks)
    if not isinstance(workbook, URIRef) or (
        workbooks, RDF.type, CFG.GovernedSourceWorkbookCollection
    ) not in registry or (workbooks, CFG.containsWorkbook, workbook) not in registry or (
        workbook, RDF.type, CFG.GovernedSourceArtifact
    ) not in registry:
        raise ValueError("The selected set must identify its registered source workbook.")
    label = _text(registry, selected, RDFS.label)
    version = _text(registry, selected, CFG.governedVersion)
    source_path = _location(registry, workbook, CFG.sourceFileLocation, base, existing=True)
    source_format = _text(registry, workbook, CFG.sourceFormat).strip().lower()
    if source_format not in {"csv", "xlsx", "xlsm"}:
        raise ValueError("The selected source has an unsupported governed format.")
    worksheet = None
    if source_format != "csv":
        worksheet = _text(registry, workbook, CFG.ruleDataSheetName)
    profile = _one(registry, configuration, CFG.usesConstraintBuildProfile)
    if (profile, RDF.type, CFG.ConstraintBuildProfile) not in registry:
        raise ValueError("The workbench requires a governed ConstraintBuildProfile.")
    models = {}
    model_paths = []
    for argument, predicate in (
        ("logical_schema_graph", CFG.logicalSchemaFileLocation),
        ("projection_model_graph", CFG.projectionModelFileLocation),
        ("established_behaviors_graph", CFG.establishedBehaviorsFileLocation),
        ("implementation_patterns_graph", CFG.shaclPatternsFileLocation),
    ):
        path = _location(registry, profile, predicate, base, existing=True)
        models[argument] = Graph().parse(path, format="turtle")
        model_paths.append(path)
    output_root = _location(registry, profile, CFG.buildOutputDirectory, base, existing=False)
    token = uuid4().hex
    run_directory = output_root / token
    run_directory.mkdir(parents=True, exist_ok=False)
    run = URIRef(f"https://dynamicontology.com/uad36/construction/run/{token}")
    manifest_path = run_directory / "run.ttl"
    batch_path = run_directory / "batch-results.ttl"
    selected_configuration = run_directory / "source-configuration.ttl"

    # Only the run-local copy changes. Resolve the selected source location
    # against the original configuration before moving the snapshot elsewhere.
    registry.set((configuration, CFG.activeComplianceSource, workbook))
    registry.set((workbook, CFG.sourceFileLocation, Literal(str(source_path))))
    registry.set((workbook, CFG.sourceFormat, Literal(source_format)))
    registry.serialize(destination=selected_configuration, format="turtle", encoding="utf-8")

    manifest = Graph()
    manifest.bind("cv", CV)
    manifest.bind("prov", PROV)
    for triple in (
        (run, RDF.type, CV.ConstraintSetBuildRun),
        (run, RDF.type, PROV.Activity),
        (run, CV.selectedConstraintSet, selected),
        (run, CV.sourceVersion, Literal(version)),
        (run, CV.sourceWorkbook, workbook),
        (run, CV.governingAuthority, governing_authority),
        (run, CV.sourceWorkbookArtifact, URIRef(source_path.as_uri())),
        (run, CV.configurationArtifact, URIRef(selected_configuration.resolve().as_uri())),
        (run, CV.batchResultsArtifact, URIRef(batch_path.resolve().as_uri())),
        (run, CV.status, Literal("RUNNING")),
        (run, PROV.used, selected),
        (run, PROV.used, workbook),
        (run, PROV.used, URIRef(source_path.as_uri())),
        (run, PROV.startedAtTime, Literal(datetime.now(timezone.utc))),
    ):
        manifest.add(triple)
    if worksheet is not None:
        manifest.add((run, CV.sourceWorksheet, Literal(worksheet)))
    for path in model_paths:
        manifest.add((run, PROV.used, URIRef(path.as_uri())))
    manifest.serialize(destination=manifest_path, format="turtle", encoding="utf-8")

    try:
        produced = constraint_production_pipeline.process_all_governed_source_rows(
            configuration_path=selected_configuration,
            output_directory=run_directory / "constraints",
            batch_results_path=batch_path,
            **models,
        )
        _index_preserved_stages(manifest, run, batch_path, run_directory)
    except Exception as error:
        # Keep run-level evidence if construction cannot return row results.
        # Never report a failed request as a completed build.
        manifest.set((run, CV.status, Literal("EXCEPTION")))
        manifest.add((run, CV.exceptionReason, Literal(str(error) or type(error).__name__)))
        manifest.add((run, PROV.endedAtTime, Literal(datetime.now(timezone.utc))))
        manifest.serialize(destination=manifest_path, format="turtle", encoding="utf-8")
        raise
    completed = tuple(produced.completed)
    exceptions = tuple(produced.exceptions)
    status = "COMPLETE_WITH_EXCEPTIONS" if exceptions else "COMPLETE"
    if not batch_path.exists():
        # A valid but empty source has no per-row persistence calls in IT-58.
        Graph().serialize(destination=batch_path, format="turtle", encoding="utf-8")
    manifest.set((run, CV.status, Literal(status)))
    manifest.add((run, CV.completedRowCount, Literal(len(completed))))
    manifest.add((run, CV.exceptionRowCount, Literal(len(exceptions))))
    manifest.add((run, PROV.endedAtTime, Literal(datetime.now(timezone.utc))))
    for item in completed:
        manifest.add((run, CV.producedConstraint, URIRef(item.constraint_id)))
    for item in exceptions:
        manifest.add((run, CV.productionException, item.result_id))
    manifest.serialize(destination=manifest_path, format="turtle", encoding="utf-8")
    return ConstraintSetBuildResult(
        run_id=str(run),
        constraint_set_id=str(selected),
        constraint_set_label=label,
        source_version=version,
        status=status,
        completed_row_count=len(completed),
        exception_row_count=len(exceptions),
        manifest_path=manifest_path,
        batch_results_path=batch_path,
        run_directory=run_directory,
    )


__all__ = ["ConstraintSetBuildResult", "build_registered_constraint_set"]
