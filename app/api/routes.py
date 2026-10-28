from dataclasses import dataclass
from html import escape
from pathlib import Path, PureWindowsPath
from urllib.parse import urlencode

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.namespace import PROV

from app.adapters.graph_store import graph_store
from app.adapters.llm import llm_client
from app.models.appraisal import LoadedAppraisal
from app.models.enums import Investor
from app.models.ingestion import IngestResponse, MappingIngestRequest, RulesIngestRequest, SchemaIngestRequest
from app.models.schema_validation import SchemaValidationReport
from app.models.validation import (
    ExplanationResponse,
    RevisionHistoryReviewRequest,
    RevisionHistoryReviewResponse,
    ValidationRequest,
    ValidationRun,
)
from app.services.constraint_set_build_workbench import build_registered_constraint_set
from app.services.experience import ExperienceProfile, load_experience_profile
from app.services.ingestion import ingestion_service
from app.services.schema_ingestion_gatekeeper import (
    IncorrectSchemaRootError,
    MalformedSchemaXmlError,
)
from app.services.rdf_projection import RdfProjectionStage, RdfProjector
from app.services.schema_loader import SchemaLoader
from app.services.schema_loader.processing_coverage import (
    report_component_processing_coverage,
)
from app.services.validation import validation_service
from app.services.xml_schema_validator import (
    UAD36_SCHEMA_PATH,
    validate_uad36_xml_bytes,
)


router = APIRouter()


def active_experience(request: Request) -> ExperienceProfile:
    configuration_file = getattr(
        request.app.state,
        "configuration_file",
        None,
    )
    path = (
        Path(configuration_file)
        if configuration_file is not None
        else None
    )
    return load_experience_profile(path)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "uad_version": "3.6"}


@router.get("/configuration/experience")
def get_experience_configuration(request: Request) -> dict[str, bool]:
    """Return only the presentation capabilities needed by the browser."""
    return active_experience(request).as_response()


@router.get("/schema/uad36/component-processing-coverage")
def get_uad36_component_processing_coverage(
    request: Request,
) -> dict[str, list[dict[str, object]]]:
    """Return schema-processing diagnostics in Developer mode."""

    if not active_experience(request).shows_developer_diagnostics:
        raise HTTPException(status_code=404, detail="Not found")

    schema = SchemaLoader().load(UAD36_SCHEMA_PATH)
    return report_component_processing_coverage(schema).as_response()


@router.post("/ingest/schema", response_model=IngestResponse)
def ingest_schema(request: SchemaIngestRequest) -> IngestResponse:
    try:
        return ingestion_service.ingest_schema(request)
    except MalformedSchemaXmlError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except IncorrectSchemaRootError as error:
        raise HTTPException(status_code=400, detail=error.detail) from error


@router.post("/ingest/mappings", response_model=IngestResponse)
def ingest_mappings(request: MappingIngestRequest) -> IngestResponse:
    return ingestion_service.ingest_mappings(request)


@router.post("/ingest/rules", response_model=IngestResponse)
def ingest_rules(request: RulesIngestRequest) -> IngestResponse:
    return ingestion_service.ingest_rules(request)


@router.get("/resources/{resource_id}")
def get_resource(resource_id: str):
    resource = graph_store.get_resource(resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource


@router.post(
    "/validate/uad36/xml-schema",
    response_model=SchemaValidationReport,
)
async def validate_uad36_xml_schema(
    file: UploadFile = File(...),
) -> SchemaValidationReport:
    xml_bytes = await file.read()
    return validate_uad36_xml_bytes(
        package_name=file.filename or "uploaded-uad36-package.xml",
        xml_bytes=xml_bytes,
    )


@router.post("/validate/uad36/rdf-projection")
async def project_uad36_rdf(
    file: UploadFile = File(...),
) -> dict[str, str | int]:
    """Project an uploaded UAD appraisal into RDF."""
    loaded_appraisal = LoadedAppraisal(
        source_name=file.filename or "uploaded-uad36-package.xml",
        xml_bytes=await file.read(),
    )
    graph = RdfProjectionStage(
        projector=RdfProjector(),
    ).run(
        loaded_appraisal=loaded_appraisal,
    )

    return {
        "package_name": loaded_appraisal.source_name,
        "status": "completed",
        "triple_count": len(graph),
    }


@router.post("/validate/uad36/pipeline")
async def run_uad36_pipeline(
    request: Request,
    pipeline: str = Form(...),
    file: UploadFile = File(...),
) -> dict[str, object]:
    """Run the UI-selected validation pipeline for one upload."""
    if pipeline != "rdf-projection":
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported validation pipeline: {pipeline}",
        )

    experience = active_experience(request)
    loaded_appraisal = LoadedAppraisal(
        source_name=file.filename or "uploaded-uad36-package.xml",
        xml_bytes=await file.read(),
    )

    try:
        graph = RdfProjectionStage(
            projector=RdfProjector(),
        ).run(
            loaded_appraisal=loaded_appraisal,
        )
    except Exception as error:
        error_code = "RDF_PROJECTION_FAILED"
        business_message = (
            "The appraisal could not be prepared for validation."
        )
        validation_run = validation_service.record_rdf_projection_failure(
            technical_message=str(error),
            error_code=error_code,
            business_message=business_message,
        )

        if not experience.shows_pipeline_stages:
            return {
                "run_id": validation_run.run_id,
                "package_name": loaded_appraisal.source_name,
                "status": "failed",
                "message": business_message,
            }

        return {
            "run_id": validation_run.run_id,
            "package_name": loaded_appraisal.source_name,
            "pipeline": pipeline,
            "status": "failed",
            "stages": [
                {
                    "name": "rdf-projection",
                    "status": "failed",
                    "error": {
                        "code": error_code,
                        "business_message": business_message,
                    },
                }
            ],
        }

    validation_run = validation_service.record_rdf_projection(
        package_name=loaded_appraisal.source_name,
        xml_bytes=loaded_appraisal.xml_bytes,
        triple_count=len(graph),
    )

    if not experience.shows_pipeline_stages:
        return {
            "run_id": validation_run.run_id,
            "package_name": loaded_appraisal.source_name,
            "status": "completed",
            "message": "The appraisal was processed successfully.",
        }

    return {
        "run_id": validation_run.run_id,
        "package_name": loaded_appraisal.source_name,
        "pipeline": pipeline,
        "status": "completed",
        "stages": [
            {
                "name": "rdf-projection",
                "status": "completed",
                "artifacts": {
                    "rdf_triple_count": len(graph),
                },
            }
        ],
    }

# Implements IT-1: Validate appraisal data against governed rule categories.
# Receives a ValidationRequest with the appraisal data and returns a ValidationRun with the results.
@router.post("/validate/uad36", response_model=ValidationRun)
def validate_uad36(request: ValidationRequest) -> ValidationRun:
    request.investor_scope = Investor.BOTH
    return validation_service.validate(request)


@router.post("/validate/uad36/fannie", response_model=ValidationRun)
def validate_uad36_fannie(request: ValidationRequest) -> ValidationRun:
    request.investor_scope = Investor.FANNIE_MAE
    return validation_service.validate(request)


@router.post("/validate/uad36/freddie", response_model=ValidationRun)
def validate_uad36_freddie(request: ValidationRequest) -> ValidationRun:
    request.investor_scope = Investor.FREDDIE_MAC
    return validation_service.validate(request)


@router.get("/validation-runs/{run_id}", response_model=ValidationRun)
def get_validation_run(run_id: str) -> ValidationRun:
    run = validation_service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Validation run not found")
    return run


@router.post("/explain/finding/{finding_id}", response_model=ExplanationResponse)
def explain_finding(finding_id: str) -> ExplanationResponse:
    finding = validation_service.get_finding(finding_id)
    return ExplanationResponse(
        finding_id=finding_id,
        explanation=llm_client.explain_finding(finding, finding_id),
    )


@router.post("/review/revision-history", response_model=RevisionHistoryReviewResponse)
def review_revision_history(request: RevisionHistoryReviewRequest) -> RevisionHistoryReviewResponse:
    return RevisionHistoryReviewResponse(
        comments=llm_client.review_revision_history(
            request.revision_history_detail,
            request.related_finding_ids,
        )
    )


@router.get("/rules")
def list_rules():
    return {"rules": graph_store.list_rules()}


@router.get("/rules/{rule_id}")
def get_rule(rule_id: str):
    rule = graph_store.get_rule(rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.get("/schema/elements/{element_name}")
def get_schema_element(element_name: str):
    element = graph_store.find_schema_element(element_name)
    if element is None:
        raise HTTPException(status_code=404, detail="Schema element not found")
    return element


_WORKBENCH_CFG = Namespace("https://dynamicontology.com/uad36/configuration#")


@dataclass(frozen=True)
class _WorkbenchConstraintSet:
    identity: str
    label: str
    authority: str
    workbook_location: str
    worksheet: str
    version: str


def _workbench_one(graph: Graph, subject, predicate):
    values = set(graph.objects(subject, predicate))
    if len(values) != 1:
        raise ValueError("A constraint-set registration has missing or conflicting metadata.")
    return next(iter(values))


def _workbench_text(graph: Graph, subject, predicate) -> str:
    value = _workbench_one(graph, subject, predicate)
    if not isinstance(value, Literal) or not str(value).strip():
        raise ValueError("A constraint-set registration requires nonblank text metadata.")
    return str(value)


def _workbench_catalog(configuration_path: Path):
    """Read explicitly registered authorities and sets without opening sources."""
    cfg = _WORKBENCH_CFG
    graph = Graph().parse(configuration_path, format="turtle")
    configurations = set(graph.subjects(RDF.type, cfg.ApplicationConfiguration))
    if len(configurations) != 1:
        raise ValueError("The workbench requires one application configuration.")
    configuration = next(iter(configurations))
    authorities: dict[str, str] = {}
    for authority in graph.subjects(RDF.type, cfg.GoverningAuthority):
        if not isinstance(authority, URIRef):
            raise ValueError("A governing authority must have a registered RDF identity.")
        authorities[str(authority)] = _workbench_text(graph, authority, RDFS.label)
    collections = set(graph.objects(configuration, cfg.hasConstraintSets))
    if not collections:
        return authorities, []
    if len(collections) != 1:
        raise ValueError("The workbench requires one registered constraint-set collection.")
    collection = next(iter(collections))
    if (collection, RDF.type, cfg.GovernedConstraintSetCollection) not in graph:
        raise ValueError("The configured collection must identify governed constraint sets.")
    workbooks = _workbench_one(graph, configuration, cfg.hasSourceWorkbooks)
    if (workbooks, RDF.type, cfg.GovernedSourceWorkbookCollection) not in graph:
        raise ValueError("The source-workbook collection must be explicitly registered.")
    registrations = []
    for set_id in graph.objects(collection, cfg.containsConstraintSet):
        if not isinstance(set_id, URIRef) or (set_id, RDF.type, cfg.GovernedConstraintSet) not in graph:
            raise ValueError("Each constraint set must have an explicit governed registration.")
        authority = _workbench_one(graph, set_id, cfg.governingAuthority)
        if not isinstance(authority, URIRef) or str(authority) not in authorities:
            raise ValueError("Each constraint set must identify a registered governing authority.")
        workbook = _workbench_one(graph, set_id, cfg.sourceWorkbook)
        if not isinstance(workbook, URIRef) or (
            workbooks, cfg.containsWorkbook, workbook
        ) not in graph or (workbook, RDF.type, cfg.GovernedSourceArtifact) not in graph:
            raise ValueError("Each constraint set must identify a registered source workbook.")
        registrations.append(_WorkbenchConstraintSet(
            identity=str(set_id),
            label=_workbench_text(graph, set_id, RDFS.label),
            authority=str(authority),
            workbook_location=_workbench_text(graph, workbook, cfg.sourceFileLocation),
            worksheet=_workbench_text(graph, workbook, cfg.ruleDataSheetName),
            version=_workbench_text(graph, set_id, cfg.governedVersion),
        ))
    return authorities, registrations


@router.get("/constraint-workbench", response_class=HTMLResponse)
def constraint_workbench(
    request: Request,
    authority: str | None = None,
    constraint_set_id: str | None = None,
) -> HTMLResponse:
    """Browse registrations and select one explicit build input."""
    configuration_file = getattr(request.app.state, "configuration_file", None)
    if configuration_file is None:
        raise HTTPException(status_code=503, detail="The source registry is not configured.")
    try:
        authorities, registrations = _workbench_catalog(Path(configuration_file))
    except (OSError, ValueError, SyntaxError) as error:
        raise HTTPException(
            status_code=503,
            detail="The governed constraint-set registry could not be loaded.",
        ) from error
    if authority and authority not in authorities:
        raise HTTPException(status_code=400, detail="Select a registered governing authority.")
    selected = authority or ""
    placeholder_selected = " selected" if not selected else ""
    options = [f'<option value=""{placeholder_selected}>Select a governing authority</option>']
    for identity, label in sorted(authorities.items(), key=lambda item: item[1].casefold()):
        is_selected = " selected" if identity == selected else ""
        options.append(f'<option value="{escape(identity)}"{is_selected}>{escape(label)}</option>')
    applicable = sorted(
        (registration for registration in registrations if registration.authority == selected),
        key=lambda item: (item.label.casefold(), item.version, item.identity),
    )
    if len(request.query_params.getlist("constraint_set_id")) > 1:
        raise HTTPException(status_code=400, detail="Select exactly one constraint set.")
    build_input = None
    if constraint_set_id:
        matches = [registration for registration in applicable if registration.identity == constraint_set_id]
        if len(matches) != 1:
            raise HTTPException(
                status_code=400,
                detail="Select a registered constraint set for the chosen governing authority.",
            )
        build_input = matches[0]
    rows = []
    for index, registration in enumerate(applicable):
        # The full location remains registered knowledge. Display the workbook
        # filename rather than exposing an internal path as the operator label.
        filename = PureWindowsPath(registration.workbook_location).name
        checked = " checked" if build_input is not None and registration.identity == build_input.identity else ""
        row_class = ' class="selected-set"' if checked else ""
        control_id = f"constraint-set-{index}"
        rows.append(
            f'<tr data-constraint-set-id="{escape(registration.identity)}"{row_class}>'
            f'<td><input type="radio" id="{control_id}" name="constraint_set_id" '
            f'value="{escape(registration.identity)}"{checked}>'
            f'<label class="set-choice" for="{control_id}">{escape(registration.label)}</label></td>'
            f'<td title="{escape(registration.workbook_location)}">{escape(filename)}</td>'
            f'<td>{escape(registration.worksheet)}</td>'
            f'<td>{escape(registration.version)}</td></tr>'
        )
    selection_action = '<button type="submit">Select build input</button>' if applicable else ""
    selected_summary = ""
    if build_input is not None:
        workbook_name = PureWindowsPath(build_input.workbook_location).name
        selected_summary = (
            f'<section id="selected-build-input" data-constraint-set-id="{escape(build_input.identity)}" '
            'aria-labelledby="selected-build-heading">'
            '<h2 id="selected-build-heading">Selected build input</h2>'
            '<dl>'
            f'<dt>Constraint set</dt><dd>{escape(build_input.label)}</dd>'
            f'<dt>Governing authority</dt><dd>{escape(authorities[build_input.authority])}</dd>'
            f'<dt>Source workbook</dt><dd>{escape(workbook_name)}</dd>'
            f'<dt>Worksheet</dt><dd>{escape(build_input.worksheet)}</dd>'
            f'<dt>Version</dt><dd>{escape(build_input.version)}</dd>'
            '</dl>'
            '<form method="post" action="/constraint-workbench/build">'
            f'<input type="hidden" name="authority" value="{escape(build_input.authority)}">'
            f'<input type="hidden" name="constraint_set_id" value="{escape(build_input.identity)}">'
            '<button type="submit">Build</button>'
            '</form></section>'
        )
    if not registrations:
        message = "No governed constraint sets have been registered."
    elif not selected:
        message = "Choose a governing authority to see its registered constraint sets."
    elif not applicable:
        message = "No constraint sets are registered for this governing authority."
    else:
        message = f"Registered constraint sets for {authorities[selected]}."
    html = f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Constraint workbench</title>
  <style>
    body {{ margin: 0; background: #f4f6f8; color: #182333; font-family: system-ui, sans-serif; }}
    main {{ max-width: 1080px; margin: 3rem auto; padding: 0 1.25rem; }}
    section {{ background: white; padding: 1.5rem; border: 1px solid #d7dfe8; border-radius: .75rem; }}
    h1 {{ margin-bottom: .5rem; }}
    label {{ display: block; font-weight: 600; margin-bottom: .5rem; }}
    select, button {{ font: inherit; padding: .65rem .8rem; border-radius: .35rem; border: 1px solid #7a8796; }}
    button {{ background: #164e83; color: white; cursor: pointer; }}
    .table-wrap {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; text-align: left; }}
    th, td {{ border-bottom: 1px solid #d7dfe8; padding: .85rem .6rem; vertical-align: top; }}
    caption {{ text-align: left; font-size: 1.15rem; font-weight: 600; margin: 1.25rem 0 .5rem; }}
    .set-choice {{ display: inline; font-weight: 400; margin-left: .5rem; }}
    .selected-set {{ background: #eaf3fb; }}
    #selected-build-input {{ margin-top: 1.25rem; border-color: #164e83; }}
    dl {{ display: grid; grid-template-columns: minmax(8rem, auto) 1fr; gap: .6rem 1rem; }}
    dt {{ font-weight: 600; }}
    dd {{ margin: 0; overflow-wrap: anywhere; }}
  </style>
</head>
<body>
<main>
  <h1>Constraint workbench</h1>
  <p>Find governed constraint sets by their governing authority.</p>
  <section aria-label="Registered constraint sets">
    <form method="get" action="/constraint-workbench">
      <label for="authority">Governing authority</label>
      <select id="authority" name="authority">{''.join(options)}</select>
      <button type="submit">Show constraint sets</button>
    </form>
    <p role="status">{escape(message)}</p>
    <form method="get" action="/constraint-workbench" aria-label="Choose constraint set">
    <input type="hidden" name="authority" value="{escape(selected)}">
    <div class="table-wrap">
      <table>
        <caption>Registered constraint sets</caption>
        <thead><tr><th scope="col">Constraint set</th><th scope="col">Source workbook</th>
          <th scope="col">Worksheet</th><th scope="col">Version</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>
    {selection_action}
    </form>
  </section>
  {selected_summary}
</main>
</body>
</html>'''
    return HTMLResponse(content=html)


@router.post("/constraint-workbench/build", response_class=HTMLResponse)
def request_constraint_build(
    request: Request,
    constraint_set_id: str | None = Form(default=None),
    authority: str | None = Form(default=None),
) -> HTMLResponse:
    """Build exactly the selected registered set through the IT-58 service."""
    back = "/constraint-workbench"
    if authority:
        back += "?" + urlencode({"authority": authority})
    result = None
    status_code = 200
    if constraint_set_id is None or not constraint_set_id.strip():
        message = "Select a constraint set before starting a build."
        status_code = 400
    else:
        configuration_file = getattr(request.app.state, "configuration_file", None)
        if configuration_file is None:
            message = "The source registry is not configured."
            status_code = 503
        else:
            try:
                result = build_registered_constraint_set(
                    configuration_path=Path(configuration_file),
                    constraint_set_id=constraint_set_id,
                    authority=authority,
                )
            except ValueError:
                message = (
                    "The build could not complete. Check the selected constraint set "
                    "and its governed build configuration."
                )
                status_code = 400
            except (OSError, SyntaxError):
                message = (
                    "The build could not complete because its configured inputs "
                    "or saved results could not be accessed."
                )
                status_code = 503

    if result is None:
        heading = "Build not completed" if status_code != 400 else "Build not started"
        body = f'<p role="alert">{escape(message)}</p>'
    else:
        heading = (
            "Build completed with row exceptions"
            if result.exception_row_count else "Build completed"
        )
        body = (
            f'<section data-build-run-id="{escape(result.run_id)}" '
            'aria-label="Build result">'
            '<dl>'
            f'<dt>Constraint set</dt><dd>{escape(result.constraint_set_label)}</dd>'
            f'<dt>Version</dt><dd>{escape(result.source_version)}</dd>'
            f'<dt>Rows completed</dt><dd>{result.completed_row_count}</dd>'
            f'<dt>Rows with exceptions</dt><dd>{result.exception_row_count}</dd>'
            '</dl>'
            '<p role="status">The build results have been saved.</p>'
            '</section>'
        )
    return HTMLResponse(
        status_code=status_code,
        content=f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(heading)}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; color: #182333; background: #f4f6f8; }}
    main {{ max-width: 48rem; margin: 3rem auto; padding: 1.5rem; background: white;
            border: 1px solid #d7dfe8; border-radius: .75rem; }}
    a {{ color: #164e83; }}
    dl {{ display: grid; grid-template-columns: minmax(8rem, auto) 1fr; gap: .6rem 1rem; }}
    dt {{ font-weight: 600; }}
    dd {{ margin: 0; overflow-wrap: anywhere; }}
  </style>
</head>
<body>
  <main>
    <h1>{escape(heading)}</h1>
    {body}
    <p><a href="{escape(back)}">Return to constraint sets</a></p>
  </main>
</body>
</html>''',
    )

# IT-59R3: render saved construction knowledge without executing workers.
_WORKBENCH_CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")
_WORKBENCH_EX = Namespace("https://dynamicontology.com/uad36/construction-exchange#")
_WORKBENCH_STAGES = (
    ("IT-50", "normalized-constraint-representation", "Normalize constraint"),
    ("IT-51", None, "Governed RDF exchange"),
    ("IT-52", "logical-schema-binding", "Bind Logical Schema"),
    ("IT-53", "context-resolution", "Resolve context"),
    ("IT-54", "validation-behavior", "Classify validation behavior"),
    ("IT-55", "instance-rdf-binding", "Bind Instance RDF"),
    ("IT-56", "shacl-representation", "Generate SHACL"),
    ("IT-58", None, "Coordinate constraint production"),
)


def _workbench_run_file(value, directory: Path) -> Path:
    """Resolve only local, existing artifacts contained in this run directory."""
    from urllib.parse import urlsplit
    from urllib.request import url2pathname

    if isinstance(value, URIRef):
        parsed = urlsplit(str(value))
        if parsed.scheme != "file" or parsed.netloc not in ("", "localhost"):
            raise ValueError("Run artifacts must be local files.")
        path = Path(url2pathname(parsed.path))
    elif isinstance(value, Literal):
        path = Path(str(value))
        if not path.is_absolute():
            path = directory / path
    else:
        raise ValueError("A saved artifact location is required.")
    path = path.resolve(strict=True)
    if not path.is_relative_to(directory.resolve()) or not path.is_file():
        raise ValueError("The saved artifact is outside this run.")
    return path


def _workbench_stage_provenance(snapshot, manifest: Graph, run, configuration: Graph, directory: Path) -> str:
    """Describe the selected original result, without guessing missing provenance."""
    from urllib.parse import urlsplit
    from urllib.request import url2pathname

    cv, cfg, exchange = _WORKBENCH_CV, _WORKBENCH_CFG, _WORKBENCH_EX
    graph, result = snapshot[2], URIRef(snapshot[1])

    def sole(data, subject, predicate):
        if subject is None:
            return None
        values = set(data.objects(subject, predicate))
        return next(iter(values)) if len(values) == 1 else None

    # Prefer the run's preserved configuration. Current configuration is used
    # only for older bundles that do not identify a saved configuration artifact.
    source_configuration = configuration
    configuration_artifacts = set(manifest.objects(run, cv.configurationArtifact))
    configuration_note = ''
    if configuration_artifacts:
        source_configuration = Graph()
        if len(configuration_artifacts) == 1:
            try:
                saved_path = _workbench_run_file(next(iter(configuration_artifacts)), directory)
                source_configuration.parse(saved_path, format="turtle")
            except (OSError, ValueError, SyntaxError):
                configuration_note = '<p>The saved source configuration could not be read.</p>'
        else:
            configuration_note = '<p>The saved source configuration reference is ambiguous.</p>'
    workbook = sole(manifest, run, cv.sourceWorkbook)
    label = sole(source_configuration, workbook, RDFS.label)
    workbook_label = str(label) if label is not None else str(workbook) if workbook is not None else 'Workbook identity not recorded.'
    worksheet = sole(manifest, run, cv.sourceWorksheet)
    if worksheet is None:
        worksheet = sole(source_configuration, workbook, cfg.ruleDataSheetName)
    artifact = sole(manifest, run, cv.sourceWorkbookArtifact)
    location = sole(source_configuration, workbook, cfg.sourceFileLocation)
    filename = 'Source filename not recorded.'
    if artifact is not None:
        parsed = urlsplit(str(artifact))
        if parsed.scheme == 'file' and parsed.netloc in ('', 'localhost'):
            filename = PureWindowsPath(url2pathname(parsed.path)).name
    elif location is not None:
        filename = PureWindowsPath(str(location)).name
    constraint = sole(graph, result, exchange.forConstraint)
    row_id = sole(graph, constraint, cv.governedUniqueId)
    # A group manifest contains multiple selections, so it must never substitute
    # its row list for the particular displayed constraint's source identifier.
    if row_id is None and sole(manifest, run, cv.rowScope) == Literal('one'):
        row_id = sole(manifest, run, cv.governedUniqueId)
    activities = sorted(set(graph.objects(result, PROV.wasGeneratedBy)), key=str)
    valid_activities = [activity for activity in activities if (activity, RDF.type, PROV.Activity) in graph]
    activity_attribute = (
        f' data-stage-activity-id="{escape(str(valid_activities[0]))}"'
        if len(activities) == len(valid_activities) == 1 else ''
    )
    attributes = f' data-stage-result-id="{escape(str(result))}"'
    if workbook is not None:
        attributes += f' data-source-workbook-id="{escape(str(workbook))}"'
    if worksheet is not None:
        attributes += f' data-source-worksheet="{escape(str(worksheet))}"'
    if row_id is not None:
        attributes += f' data-source-row-id="{escape(str(row_id))}"'
    activity_text = (
        ''.join(f'<li>{escape(str(activity))}</li>' for activity in valid_activities)
        if valid_activities else '<li>Stage execution activity not recorded.</li>'
    )
    return (
        f'<details id="stage-provenance"{attributes}{activity_attribute}>'
        '<summary>Provenance</summary>'
        f'{configuration_note}<dl>'
        f'<dt>Source workbook</dt><dd>{escape(workbook_label)}</dd>'
        f'<dt>File</dt><dd>{escape(filename)}</dd>'
        f'<dt>Rule-data worksheet</dt><dd>{escape(str(worksheet)) if worksheet is not None else "Worksheet not recorded."}</dd>'
        f'<dt>Source row identifier</dt><dd>{escape(str(row_id)) if row_id is not None else "Source row identifier not recorded."}</dd>'
        f'<dt>Construction stage</dt><dd>{escape(snapshot[3])}</dd>'
        f'<dt>Stage result</dt><dd>{escape(str(result))}</dd>'
        f'<dt>Generating stage activity</dt><dd><ul>{activity_text}</ul></dd>'
        '</dl></details>'
    )

def _workbench_rdf_svg(graph: Graph) -> str:
    """Draw RDF assertions with complete term identities and readable type labels."""
    def term_attribute(term):
        # Keep RDF escapes, datatypes and language tags. Character references
        # preserve whitespace even when the browser parses HTML attributes.
        return escape(term.n3()).replace("\n", "&#10;").replace("\r", "&#13;").replace("\t", "&#9;")
    triples = sorted(graph, key=lambda triple: tuple(term.n3() for term in triple))
    if not triples:
        return '<p role="status">No stage RDF has been saved yet.</p>'
    height = 40 + len(triples) * 90
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" '
        f'viewBox="0 0 1200 {height}" role="img" aria-labelledby="rdf-graph-title">',
        '<title id="rdf-graph-title">Actual RDF assertions from the saved stage result</title>',
        '<defs><marker id="rdf-arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#42678d"/></marker></defs>',
    ]
    for index, (subject, predicate, obj) in enumerate(triples):
        y = 45 + index * 90
        parts.append(
            f'<g data-rdf-subject="{escape(str(subject))}" '
            f'data-rdf-predicate="{escape(str(predicate))}" '
            f'data-rdf-object="{escape(str(obj))}" '
            f'data-rdf-subject-n3="{term_attribute(subject)}" '
            f'data-rdf-predicate-n3="{term_attribute(predicate)}" '
            f'data-rdf-object-n3="{term_attribute(obj)}">'
            f'<path d="M 385 {y} L 805 {y}" stroke="#42678d" '
            'stroke-width="2" marker-end="url(#rdf-arrow)"/>'
        )
        for x, term in ((15, subject), (815, obj)):
            label = term.n3()
            shortened = label if len(label) <= 42 else label[:39] + "..."
            if isinstance(term, URIRef):
                kind, colour = "IRI", "#edf4fb"
            elif isinstance(term, Literal):
                kind, colour = "Literal", "#fff7e6"
                if term.language:
                    kind += f" @{term.language}"
                elif term.datatype:
                    datatype_name = str(term.datatype).rsplit("#", 1)[-1].rsplit("/", 1)[-1]
                    kind += f" ({datatype_name})"
            else:
                kind, colour = "Blank node", "#f3edff"
            parts.append(
                f'<g data-rdf-term-n3="{term_attribute(term)}"><title>{escape(label)}</title>'
                f'<rect x="{x}" y="{y - 22}" width="370" height="44" rx="8" '
                f'fill="{colour}" stroke="#8da9c5"/>'
                f'<text x="{x + 10}" y="{y - 3}" font-size="13">{escape(shortened)}</text>'
                f'<text x="{x + 10}" y="{y + 14}" font-size="10" fill="#526173">{escape(kind)}</text></g>'
            )
        predicate_label = str(predicate)
        short_predicate = predicate_label if len(predicate_label) <= 44 else predicate_label[:41] + "..."
        parts.append(
            f'<text x="595" y="{y - 12}" text-anchor="middle" font-size="12">'
            f'<title>{escape(predicate_label)}</title>{escape(short_predicate)}</text></g>'
        )
    parts.append('</svg>')
    return ''.join(parts)


@router.get("/constraint-workbench/runs/{run_token}", response_class=HTMLResponse)
def view_constraint_build_run(
    request: Request, run_token: str, result_id: str | None = None,
    playback: str | None = None,
) -> HTMLResponse:
    """Read a saved run and refresh its actual RDF visualization while running."""
    from hashlib import sha256

    if playback not in (None, "playing", "paused") or len(request.query_params.getlist("playback")) > 1:
        raise HTTPException(status_code=400, detail="Choose playing or paused playback.")
    cfg, cv, exchange = _WORKBENCH_CFG, _WORKBENCH_CV, _WORKBENCH_EX
    configuration_file = getattr(request.app.state, "configuration_file", None)
    if configuration_file is None:
        raise HTTPException(status_code=503, detail="The source registry is not configured.")
    # Tokens identify a direct child of the configured run root, never a path.
    if not run_token or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for character in run_token):
        raise HTTPException(status_code=404, detail="Build run not found.")
    try:
        configuration_path = Path(configuration_file).resolve(strict=True)
        configuration = Graph().parse(configuration_path, format="turtle")
        roots = set(configuration.subjects(RDF.type, cfg.ApplicationConfiguration))
        if len(roots) != 1:
            raise ValueError("One application configuration is required.")
        root = next(iter(roots))
        profile = _workbench_one(configuration, root, cfg.usesConstraintBuildProfile)
        if (profile, RDF.type, cfg.ConstraintBuildProfile) not in configuration:
            raise ValueError("A governed build profile is required.")
        output_root = Path(_workbench_text(configuration, profile, cfg.buildOutputDirectory))
        if not output_root.is_absolute():
            output_root = configuration_path.parent / output_root
        output_root = output_root.resolve()
        directory = (output_root / run_token).resolve()
        if directory.parent != output_root or not directory.is_dir():
            raise HTTPException(status_code=404, detail="Build run not found.")
        manifest_path = _workbench_run_file(Literal(str(directory / "run.ttl")), directory)
        manifest = Graph().parse(manifest_path, format="turtle")
        runs = set(manifest.subjects(RDF.type, cv.ConstraintSetBuildRun)) | set(manifest.subjects(RDF.type, cv.ConstraintPipelineRun))
        if len(runs) != 1:
            raise ValueError("A manifest must identify exactly one run.")
        run = next(iter(runs))
        if not isinstance(run, URIRef):
            raise ValueError("A run requires a named identity.")
        status = _workbench_text(manifest, run, cv.status)
        running = status == "RUNNING"
        current_values = set(manifest.objects(run, cv.currentStage))
        if len(current_values) > 1:
            raise ValueError("The active stage is ambiguous.")
        current = str(next(iter(current_values))) if current_values else None
        batch_values = set(manifest.objects(run, cv.batchResultsArtifact))
        if len(batch_values) != 1:
            raise ValueError("The run must identify its batch results.")
        # A run can be visible before its first worker has saved any output.
        try:
            batch_path = _workbench_run_file(next(iter(batch_values)), directory)
        except FileNotFoundError:
            if not running:
                raise
            batch = Graph()
        else:
            batch = Graph().parse(batch_path, format="turtle")
        # Count actual saved completion states. During an all-row pipeline call,
        # the manifest may still contain the initial zero completed-row count.
        completed_constraints = {
            constraint
            for state in batch.subjects(RDF.type, cv.ConstraintProductionState)
            if (state, cv.status, Literal("COMPLETE")) in batch
            for constraint in batch.objects(state, cv.governedConstraint)
        }
        completed_row_count = len(completed_constraints)
        totals = set(manifest.objects(run, cv.totalRowCount))
        if totals:
            if len(totals) != 1:
                raise ValueError("The run has conflicting total-row counts.")
            total_row_count = int(str(next(iter(totals))))
            if total_row_count < 0:
                raise ValueError("The total-row count cannot be negative.")
        else:
            selected_ids = set(manifest.objects(run, cv.governedUniqueId))
            total_row_count = len(selected_ids) if selected_ids else len(set(batch.subjects(RDF.type, cv.NormalizedConstraint)))
        # Failed results have contracted knowledge even without a verified RDF
        # snapshot. Read that knowledge directly from this run's saved batch.
        failure_results = set(manifest.objects(run, cv.productionException))
        if not failure_results:
            failure_results = {
                result for result in batch.subjects(RDF.type, exchange.ConstructionStageResult)
                if (result, exchange.constructionStatus, Literal("EXCEPTION")) in batch
            }
        failures = []
        for result in sorted(failure_results, key=str):
            if (result, RDF.type, exchange.ConstructionStageResult) not in batch or (
                result, exchange.constructionStatus, Literal("EXCEPTION")
            ) not in batch:
                raise ValueError("A run exception must identify its contracted batch result.")
            failed_stage = _workbench_text(batch, result, exchange.constructionStage)
            reason = _workbench_text(batch, result, exchange.exceptionReason)
            constraint = _workbench_one(batch, result, exchange.forConstraint)
            source_rows = set(batch.objects(result, cv.governedUniqueId))
            if not source_rows:
                source_rows = set(batch.objects(constraint, cv.governedUniqueId))
            row_id = str(next(iter(source_rows))) if len(source_rows) == 1 else None
            sources = set(batch.objects(result, PROV.wasDerivedFrom))
            if not sources:
                sources = set(batch.objects(constraint, PROV.wasDerivedFrom))
            review = set(batch.objects(result, exchange.requiresReview))
            review_message = (
                "Governed review is required." if review == {Literal(True)} else
                "Governed review is not required." if review == {Literal(False)} else
                "The review requirement was not recorded."
            )
            failures.append((result, failed_stage, constraint, row_id, sources, reason, review_message))
        failed_stages = {failure[1] for failure in failures}
        worker_order = {name: index for index, (_, name, _) in enumerate(_WORKBENCH_STAGES) if name}
        snapshots = []
        completed_stages = set()
        for result in set(batch.subjects(RDF.type, exchange.ConstructionStageResult)):
            stage = _workbench_text(batch, result, exchange.constructionStage)
            if stage not in worker_order:
                continue
            result_status = _workbench_text(batch, result, exchange.constructionStatus)
            if result_status != "GREEN":
                continue
            availability = set(batch.objects(result, exchange.availableForDownstream))
            # A GREEN label alone must not override an explicit withheld or
            # conflicting verification decision. Exclude this result before
            # building timeline links, playback navigation or direct selection.
            if availability and availability != {Literal(True)}:
                continue
            location = _workbench_one(batch, result, exchange.rdfSnapshotPath)
            snapshot_path = _workbench_run_file(location, directory)
            snapshot_bytes = snapshot_path.read_bytes()
            checksums = set(batch.objects(result, exchange.snapshotSha256))
            if len(checksums) != 1:
                raise ValueError("A saved stage must have exactly one recorded digest.")
            recorded_digest = str(next(iter(checksums)))
            manifest_digests = set(manifest.objects(result, exchange.snapshotSha256))
            if manifest_digests and manifest_digests != checksums:
                raise ValueError("The manifest and batch disagree on the saved digest.")
            computed_digest = sha256(snapshot_bytes).hexdigest()
            matches_digest = recorded_digest == computed_digest
            # Preserve the failed comparison as inspectable evidence. Do not
            # parse or render changed bytes as the original governed result.
            graph = Graph()
            saved_text = ''
            if matches_digest:
                graph.parse(data=snapshot_bytes, format="turtle")
                if (result, RDF.type, exchange.ConstructionStageResult) not in graph or (
                    result, exchange.constructionStage, Literal(stage)
                ) not in graph:
                    raise ValueError("The snapshot does not identify the saved stage result.")
                saved_text = snapshot_bytes.decode("utf-8")
                completed_stages.add(stage)
            snapshots.append((
                worker_order[stage], str(result), graph, stage, saved_text,
                recorded_digest, computed_digest,
            ))
        latest = max(snapshots, key=lambda item: (item[0], item[1])) if snapshots else None
        if len(request.query_params.getlist("result_id")) > 1:
            raise HTTPException(status_code=400, detail="Select exactly one saved stage result.")
        ordered_snapshots = sorted(snapshots, key=lambda saved: (saved[0], saved[1]))
        selected_snapshot = (
            ordered_snapshots[0] if playback == "playing" and ordered_snapshots else latest
        )
        if result_id is not None:
            matches = [item for item in snapshots if item[1] == result_id]
            if len(matches) != 1:
                raise HTTPException(
                    status_code=404,
                    detail="The selected stage result is not available in this build run.",
                )
            selected_snapshot = matches[0]
    except HTTPException:
        raise
    except (OSError, ValueError, SyntaxError) as error:
        raise HTTPException(status_code=503, detail="Saved build progress could not be read. Refresh to retry.") from error

    steps = []
    for iteration, stage, label in _WORKBENCH_STAGES:
        is_current = running and stage is not None and stage == current and stage not in failed_stages
        stage_status = (
            "EXCEPTION" if stage in failed_stages else
            "RUNNING" if is_current else "GREEN" if stage in completed_stages else "PENDING"
        )
        if iteration == "IT-51":
            stage_status = "CONTRACT"
        if iteration == "IT-58":
            stage_status = status
        active = ' aria-current="step"' if is_current else ''
        steps.append(
            f'<li data-pipeline-stage="{iteration}" data-status="{escape(stage_status)}"{active}>'
            f'<strong>{iteration}: {escape(label)}</strong> <span>{escape(stage_status)}</span></li>'
        )
    # With no playback query, preserve the live view of the latest saved output.
    # Explicit playback walks the saved results; pausing freezes the chosen one.
    integrity_mismatch = bool(selected_snapshot and selected_snapshot[5] != selected_snapshot[6])
    playback_state = playback or ("playing" if running and result_id is None else "paused")
    if integrity_mismatch:
        playback_state = "paused"
    selected_index = next(
        (index for index, item in enumerate(ordered_snapshots)
         if selected_snapshot and item[1] == selected_snapshot[1]),
        None,
    )
    previous_snapshot = (
        ordered_snapshots[selected_index - 1]
        if selected_index is not None and selected_index > 0 else None
    )
    next_snapshot = (
        ordered_snapshots[selected_index + 1]
        if selected_index is not None and selected_index + 1 < len(ordered_snapshots) else None
    )

    def playback_url(snapshot, state):
        query = {"playback": state}
        if snapshot is not None:
            query["result_id"] = snapshot[1]
        return f"/constraint-workbench/runs/{run_token}?" + urlencode(query)

    def playback_control(action, label, snapshot, state):
        return (
            f'<a data-visualization-action="{action}" '
            f'href="{escape(playback_url(snapshot, state))}">{label}</a>'
        )

    controls = []
    if playback_state == "playing":
        controls.append(playback_control("pause", "Pause", selected_snapshot, "paused"))
    else:
        controls.append(playback_control("resume", "Resume", selected_snapshot, "playing"))
    if previous_snapshot is not None:
        controls.append(playback_control("previous", "Previous stage", previous_snapshot, playback_state))
    if next_snapshot is not None:
        controls.append(playback_control("next", "Next stage", next_snapshot, playback_state))
    refresh = ''
    if playback_state == "playing":
        if playback is None:
            if running:
                refresh = '<meta http-equiv="refresh" content="2">'
        elif next_snapshot is not None or running:
            destination = playback_url(next_snapshot or selected_snapshot, "playing")
            refresh = f'<meta http-equiv="refresh" content="2;url={escape(destination)}">'
    graph = selected_snapshot[2] if selected_snapshot else Graph()
    graph_title = (
        f"Selected stage: {selected_snapshot[3]}" if result_id is not None and selected_snapshot
        else f"Latest saved stage: {selected_snapshot[3]}" if selected_snapshot
        else "Waiting for the first stage result"
    )
    result_links = []
    labels = {stage: (iteration, label) for iteration, stage, label in _WORKBENCH_STAGES if stage}
    for item in sorted(snapshots, key=lambda saved: (saved[0], saved[1])):
        _, saved_id, saved_graph, saved_stage, _, _, _ = item
        saved_constraint = _workbench_one(batch, URIRef(saved_id), exchange.forConstraint)
        row_ids = set(batch.objects(saved_constraint, cv.governedUniqueId))
        row_label = str(next(iter(row_ids))) if len(row_ids) == 1 else str(saved_constraint)
        iteration, label = labels[saved_stage]
        # Clicking a stage in the default live view pauses on that result.
        selection_state = playback_state if playback is not None else "paused"
        href = playback_url(item, selection_state)
        selected_attribute = ' aria-current="true"' if selected_snapshot and saved_id == selected_snapshot[1] else ''
        result_links.append(
            f'<li><a data-visualization-action="select" href="{escape(href)}"{selected_attribute}>'
            f'{iteration}: {escape(label)} — row {escape(row_label)}</a></li>'
        )
    selection_attribute = (
        f' data-selected-stage-result-id="{escape(selected_snapshot[1])}"'
        if selected_snapshot else ''
    )
    serialized_rdf = (
        '<details open><summary>Exact saved Turtle</summary>'
        f'<pre id="stage-rdf">{escape(selected_snapshot[4])}</pre></details>'
        if selected_snapshot and not integrity_mismatch else ''
    )
    provenance_details = (
        _workbench_stage_provenance(selected_snapshot, manifest, run, configuration, directory)
        if selected_snapshot and not integrity_mismatch else ''
    )
    integrity_report = ''
    if selected_snapshot:
        integrity_status = "MISMATCH" if integrity_mismatch else "MATCH"
        integrity_message = (
            "Integrity check failed: this snapshot does not match the saved run record. "
            "Playback is paused and the changed RDF is not displayed."
            if integrity_mismatch else
            "Integrity verified: this snapshot matches the saved run record."
        )
        integrity_report = (
            f'<section aria-label="Stage integrity" data-integrity-status="{integrity_status}" '
            f'data-recorded-digest="{escape(selected_snapshot[5])}" '
            f'data-computed-digest="{escape(selected_snapshot[6])}">'
            '<h3>Saved result integrity</h3>'
            f'<p role="status">{escape(integrity_message)}</p>'
            '<details><summary>SHA-256 comparison</summary><dl>'
            f'<dt>Recorded digest</dt><dd>{escape(selected_snapshot[5])}</dd>'
            f'<dt>Computed digest</dt><dd>{escape(selected_snapshot[6])}</dd>'
            '</dl></details></section>'
        )
    rendered_graph = '' if integrity_mismatch else _workbench_rdf_svg(graph)
    constraints = sorted({str(node) for node in graph.subjects(RDF.type, cv.NormalizedConstraint)})
    constraint_labels = ''.join(f'<li>{escape(identity)}</li>' for identity in constraints)
    active_label = next((label for _, stage, label in _WORKBENCH_STAGES if stage and stage == current), None)
    progress = f"Currently processing: {active_label}" if running and active_label else (
        "Waiting for saved stage progress" if running else f"Run status: {status}"
    )
    failure_sections = []
    stage_labels = {stage: f"{iteration}: {label}" for iteration, stage, label in _WORKBENCH_STAGES if stage}
    for result, failed_stage, constraint, row_id, sources, reason, review_message in failures:
        source_attribute = (
            f' data-source-constraint-id="{escape(str(next(iter(sources))))}"'
            if len(sources) == 1 else ''
        )
        row_attribute = f' data-source-row-id="{escape(row_id)}"' if row_id else ''
        source_text = (
            ''.join(f'<li>{escape(str(source))}</li>' for source in sorted(sources, key=str))
            if sources else '<li>Governed source reference not recorded.</li>'
        )
        row_text = escape(row_id) if row_id else 'Source row ID unavailable: not recorded.'
        failure_sections.append(
            f'<section class="construction-failure" role="alert" '
            f'data-construction-exception-id="{escape(str(result))}" '
            f'data-failed-stage="{escape(failed_stage)}"{source_attribute}{row_attribute}>'
            f'<h2>Construction exception — {escape(stage_labels.get(failed_stage, failed_stage))}</h2>'
            f'<p><strong>Source row:</strong> {row_text}</p>'
            f'<p><strong>Constraint:</strong> {escape(str(constraint))}</p>'
            f'<p><strong>Contracted reason:</strong> {escape(reason)}</p>'
            f'<p>{escape(review_message)}</p>'
            '<h3>Governed source</h3>'
            f'<ul>{source_text}</ul></section>'
        )
    view_heading = (
        "Build completed with construction exceptions" if status == "COMPLETE_WITH_EXCEPTIONS" else
        "Build has construction exceptions" if failures or status == "EXCEPTION" else
        "Constraint build progress"
    )
    return HTMLResponse(status_code=409 if integrity_mismatch else 200, content=f'''<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
{refresh}<title>{escape(view_heading)}</title>
<style>
body {{ background: #f4f6f8; color: #182333; font-family: system-ui, sans-serif; margin: 0; }}
main {{ max-width: 1280px; margin: 2rem auto; padding: 0 1rem; }}
section {{ background: white; border: 1px solid #d7dfe8; border-radius: .75rem; padding: 1.25rem; margin: 1rem 0; }}
ol {{ display: flex; flex-wrap: wrap; gap: .75rem; list-style-position: inside; padding: 0; }}
ol li {{ border: 1px solid #c6d3df; padding: .75rem; border-radius: .4rem; }}
ol li span {{ display: block; margin-top: .3rem; }}
[aria-current="step"] {{ background: #e8f3ff; border-color: #164e83; }}
.graph {{ overflow: auto; max-height: 70vh; }}
pre {{ overflow: auto; max-height: 30rem; background: #f4f6f8; padding: 1rem; }}
summary {{ cursor: pointer; margin: 1rem 0; font-weight: 600; }}
[aria-current="true"] {{ font-weight: 700; }}
li {{ overflow-wrap: anywhere; }} a {{ color: #164e83; }}
.construction-failure {{ border-left: 5px solid #a52921; background: #fff4f2; }}
.playback-controls {{ display: flex; flex-wrap: wrap; gap: 1rem; align-items: center; }}
.playback-controls a {{ padding: .6rem .85rem; border: 1px solid #164e83; border-radius: .35rem; }}
</style></head><body><main data-build-run-id="{escape(str(run))}" data-run-status="{escape(status)}"
 data-completed-row-count="{completed_row_count}" data-total-row-count="{total_row_count}">
<h1>{escape(view_heading)}</h1><p role="status">{escape(progress)}</p>
<p role="status">Rows completed: {completed_row_count} of {total_row_count}.</p>
{''.join(failure_sections)}
<section aria-label="Construction stages"><ol>{''.join(steps)}</ol></section>
<section aria-label="Playback controls" data-playback-state="{playback_state}">
<h2>Playback</h2><p>{"Playing" if playback_state == "playing" else "Paused"}</p>
<nav class="playback-controls" aria-label="Navigate stage results">{''.join(controls)}</nav>
</section>
<section aria-label="Select saved stage result"><h2>Available stage results</h2>
<ul>{''.join(result_links)}</ul></section>
<section aria-label="Saved stage RDF"{selection_attribute}><h2>{escape(graph_title)}</h2>
{integrity_report}
<ul>{constraint_labels}</ul><div class="graph">{rendered_graph}</div>
{serialized_rdf}
{provenance_details}</section>
<p><a href="/constraint-workbench">Return to constraint sets</a></p>
</main></body></html>''')


@dataclass(frozen=True)
class _PipelineSourceWorkbook:
    identity: str
    label: str
    location: str
    worksheet: str


def _pipeline_source_workbooks(configuration_path: Path) -> list[_PipelineSourceWorkbook]:
    """Read registered workbook metadata without opening or changing sources."""
    cfg = _WORKBENCH_CFG
    configuration = Graph().parse(configuration_path, format="turtle")
    roots = set(configuration.subjects(RDF.type, cfg.ApplicationConfiguration))
    if len(roots) != 1:
        raise ValueError("The pipeline requires one application configuration.")
    root = next(iter(roots))
    collection = _workbench_one(configuration, root, cfg.hasSourceWorkbooks)
    if (collection, RDF.type, cfg.GovernedSourceWorkbookCollection) not in configuration:
        raise ValueError("The source-workbook collection must be explicitly registered.")
    workbooks = []
    for identity in set(configuration.objects(collection, cfg.containsWorkbook)):
        if not isinstance(identity, URIRef) or (
            identity, RDF.type, cfg.GovernedSourceArtifact
        ) not in configuration:
            raise ValueError("Each source workbook requires an explicit governed registration.")
        workbooks.append(_PipelineSourceWorkbook(
            identity=str(identity),
            label=_workbench_text(configuration, identity, RDFS.label),
            location=_workbench_text(configuration, identity, cfg.sourceFileLocation),
            worksheet=_workbench_text(configuration, identity, cfg.ruleDataSheetName),
        ))
    return sorted(workbooks, key=lambda item: (item.label.casefold(), item.identity))


@router.get("/constraint-pipeline", response_class=HTMLResponse)
def constraint_pipeline(
    request: Request, source_workbook_id: str | None = None,
) -> HTMLResponse:
    """Select workbook input for this run without changing active configuration."""
    configuration_file = getattr(request.app.state, "configuration_file", None)
    if configuration_file is None:
        raise HTTPException(status_code=503, detail="The source-workbook collection is not configured.")
    if len(request.query_params.getlist("source_workbook_id")) > 1:
        raise HTTPException(status_code=400, detail="Select exactly one source workbook.")
    try:
        workbooks = _pipeline_source_workbooks(Path(configuration_file))
    except (OSError, ValueError, SyntaxError) as error:
        raise HTTPException(
            status_code=503, detail="The configured source-workbook collection could not be loaded.",
        ) from error
    selected = None
    if source_workbook_id is not None:
        matches = [item for item in workbooks if item.identity == source_workbook_id]
        if len(matches) != 1:
            raise HTTPException(status_code=400, detail="Select a workbook from the configured source collection.")
        selected = matches[0]
    placeholder_selected = ' selected' if selected is None else ''
    options = [f'<option value="" disabled{placeholder_selected}>Select a governed workbook</option>']
    for workbook in workbooks:
        checked = ' selected' if selected is not None and workbook.identity == selected.identity else ''
        options.append(
            f'<option value="{escape(workbook.identity)}"{checked}>{escape(workbook.label)}</option>'
        )
    selected_summary = ''
    if selected is not None:
        from app.services.constraint_pipeline_workbench import list_workbook_row_identifiers

        try:
            row_ids = list_workbook_row_identifiers(
                configuration_path=Path(configuration_file), source_workbook_id=selected.identity,
            )
        except (OSError, ValueError, SyntaxError) as error:
            raise HTTPException(status_code=503, detail="The configured worksheet's row identifiers could not be loaded.") from error
        row_options = ''.join(f'<option value="{escape(value)}">{escape(value)}</option>' for value in row_ids)
        selected_summary = (
            '<section id="selected-source-workbook" '
            f'data-source-workbook-id="{escape(selected.identity)}" '
            'aria-labelledby="selected-source-heading">'
            '<h2 id="selected-source-heading">Selected source workbook</h2><dl>'
            f'<dt>Workbook</dt><dd>{escape(selected.label)}</dd>'
            f'<dt>File</dt><dd>{escape(PureWindowsPath(selected.location).name)}</dd>'
            f'<dt>Rule-data worksheet</dt><dd>{escape(selected.worksheet)}</dd>'
            '</dl><p>This workbook is selected for this construction run.</p>'
            '<form id="construction-run-form" method="post" action="/constraint-pipeline/runs" aria-label="Construction run input">'
            f'<input type="hidden" name="source_workbook_id" value="{escape(selected.identity)}">'
            '<fieldset><legend>Rows to process</legend>'
            '<label><input type="radio" name="row_scope" value="one" checked> One row</label>'
            '<label><input type="radio" name="row_scope" value="group"> Selected group of rows</label>'
            '<label><input type="radio" name="row_scope" value="all"> All rows in this worksheet</label>'
            '<div id="single-row-choice"><label for="unique-id">Exact governed row identifier</label>'
            '<input id="unique-id" name="unique_id" type="text" required autocomplete="off" '
            'aria-describedby="unique-id-help">'
            '<p id="unique-id-help">Enter the identifier exactly as published, including leading zeroes.</p></div>'
            '<div id="group-row-choice" hidden><label for="unique-ids">Select governed row identifiers</label>'
            f'<select id="unique-ids" name="unique_ids" multiple size="8" disabled>{row_options}</select>'
            '<p>Use Ctrl or Shift to select multiple rows.</p></div>'
            '</fieldset><button type="submit">Start construction</button>'
            '</form></section>'
        )
    collection_message = (
        'Choose the governed workbook to use for this construction run.'
        if workbooks else 'No source workbooks have been registered.'
    )
    disabled = '' if workbooks else ' disabled'
    return HTMLResponse(content=f'''<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Constraint pipeline</title>
<style>
body {{ margin: 0; background: #f4f6f8; color: #182333; font-family: system-ui, sans-serif; }}
main {{ max-width: 60rem; margin: 3rem auto; padding: 0 1.25rem; }}
section {{ background: white; padding: 1.5rem; margin: 1.25rem 0;
           border: 1px solid #d7dfe8; border-radius: .75rem; }}
label {{ display: block; font-weight: 600; margin-bottom: .5rem; }}
select, button {{ max-width: 100%; font: inherit; padding: .65rem .8rem;
                  border-radius: .35rem; border: 1px solid #7a8796; }}
button {{ background: #164e83; color: white; cursor: pointer; }}
button:disabled {{ background: #687583; cursor: default; }}
dl {{ display: grid; grid-template-columns: minmax(8rem, auto) 1fr; gap: .6rem 1rem; }}
dt {{ font-weight: 600; }} dd {{ margin: 0; overflow-wrap: anywhere; }}
a {{ color: #164e83; }}
</style></head><body><main>
<h1>Constraint pipeline</h1>
<section aria-label="Choose governed source">
<h2>Source workbook</h2><p>{escape(collection_message)}</p>
<form method="get" action="/constraint-pipeline">
<label for="source-workbook">Governed source workbook</label>
<select id="source-workbook" name="source_workbook_id" required{disabled}>{''.join(options)}</select>
<button type="submit"{disabled}>Select workbook</button>
</form></section>
{selected_summary}
<p><a href="/constraint-workbench">Open the constraint-set workbench</a></p>
<script>
(() => {{
  const form = document.getElementById('construction-run-form');
  if (!form) return;
  const single = document.getElementById('unique-id');
  const group = document.getElementById('unique-ids');
  const updateScope = () => {{
    const scope = form.querySelector('input[name="row_scope"]:checked').value;
    const grouped = scope === 'group';
    const one = scope === 'one';
    document.getElementById('single-row-choice').hidden = !one;
    document.getElementById('group-row-choice').hidden = !grouped;
    single.disabled = !one;
    single.required = one;
    group.disabled = !grouped;
    group.required = grouped;
  }};
  form.querySelectorAll('input[name="row_scope"]').forEach(control => control.addEventListener('change', updateScope));
  updateScope();
}})();
</script>
</main></body></html>''')


@router.post("/constraint-pipeline/runs", response_class=HTMLResponse)
def start_constraint_pipeline_run(
    request: Request,
    source_workbook_id: str | None = Form(default=None),
    row_scope: str | None = Form(default=None),
    unique_id: str | None = Form(default=None),
    unique_ids: list[str] | None = Form(default=None),
) -> HTMLResponse:
    """Construct the selected exact textual IDs inside one saved workbook run."""
    from app.services.constraint_pipeline_workbench import (
        process_one_workbook_row, process_selected_workbook_rows, process_all_workbook_rows,
    )

    if not source_workbook_id or not source_workbook_id.strip():
        raise HTTPException(status_code=400, detail="Select a configured source workbook.")
    if row_scope not in {"one", "group", "all"}:
        raise HTTPException(status_code=400, detail="Select a supported row scope.")
    if row_scope == "one" and (unique_id is None or not unique_id.strip()):
        raise HTTPException(status_code=400, detail="Enter the exact governed row identifier.")
    if row_scope == "group" and not unique_ids:
        raise HTTPException(status_code=400, detail="Select at least one governed row identifier.")
    configuration_file = getattr(request.app.state, "configuration_file", None)
    if configuration_file is None:
        raise HTTPException(status_code=503, detail="The source-workbook collection is not configured.")
    try:
        if row_scope == "one":
            result = process_one_workbook_row(
                configuration_path=Path(configuration_file),
                source_workbook_id=source_workbook_id, unique_id=unique_id,
            )
        elif row_scope == "group":
            result = process_selected_workbook_rows(
                configuration_path=Path(configuration_file),
                source_workbook_id=source_workbook_id, unique_ids=unique_ids,
            )
        else:
            result = process_all_workbook_rows(
                configuration_path=Path(configuration_file), source_workbook_id=source_workbook_id,
            )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="Construction could not complete the selected rows. Check the exact identifiers and governed input knowledge.",
        ) from error
    except (OSError, SyntaxError) as error:
        raise HTTPException(status_code=503, detail="The configured construction inputs or saved results could not be accessed.") from error
    if result.status == "EXCEPTION" or result.exception_row_count:
        # A contracted worker failure is a saved construction outcome. Show its
        # original diagnostic and the retained verified-stage links immediately.
        return view_constraint_build_run(request, result.run_directory.name, playback="paused")
    view_url = f"/constraint-workbench/runs/{result.run_directory.name}"
    selected_rows = ''.join(f'<li>{escape(value)}</li>' for value in result.unique_ids)
    heading = "Constraint construction completed with exceptions" if result.exception_row_count else "Constraint construction completed"
    return HTMLResponse(content=f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(heading)}</title>
<style>
body {{ background: #f4f6f8; color: #182333; font-family: system-ui, sans-serif; }}
main {{ max-width: 55rem; margin: 3rem auto; padding: 1.5rem; background: white;
        border: 1px solid #d7dfe8; border-radius: .75rem; }}
dl {{ display: grid; grid-template-columns: minmax(8rem, auto) 1fr; gap: .7rem 1rem; }}
dt {{ font-weight: 600; }} dd {{ margin: 0; overflow-wrap: anywhere; }} a {{ color: #164e83; }}
</style></head><body><main data-build-run-id="{escape(result.run_id)}" data-run-status="{result.status}"
 data-completed-row-count="{result.completed_row_count}" data-total-row-count="{len(result.unique_ids)}">
<h1>{escape(heading)}</h1>
<p role="status">Rows completed: {result.completed_row_count} of {len(result.unique_ids)}.</p>
<dl><dt>Source workbook</dt><dd>{escape(result.workbook_label)}</dd>
<dt>Worksheet</dt><dd>{escape(result.worksheet)}</dd>
<dt>Row identifiers</dt><dd><ul>{selected_rows}</ul></dd>
<dt>Rows completed</dt><dd>{result.completed_row_count}</dd>
<dt>Rows with exceptions</dt><dd>{result.exception_row_count}</dd></dl>
<p role="status">The selected rows' reusable RDF and SHACL artifacts have been saved.</p>
<p><a href="{escape(view_url)}">Inspect the run's stage RDF</a></p>
<p><a href="/constraint-pipeline">Return to the constraint pipeline</a></p>
</main></body></html>''')
