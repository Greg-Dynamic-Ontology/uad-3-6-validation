"use strict";

const form = document.getElementById("validation-form");
const fileInput = document.getElementById("appraisal-file");
const validateButton = document.getElementById("validate-button");
const technicalPipelineSelection = document.getElementById(
    "technical-pipeline-selection"
);
const technicalPipelineSpacing = document.getElementById(
    "technical-pipeline-spacing"
);
const technicalArtifactsSection = document.getElementById(
    "technical-artifacts-section"
);
const schemaComponentProcessingCoverage = document.getElementById(
    "schema-component-processing-coverage"
);
const schemaComponentProcessingCoverageRows = document.getElementById(
    "schema-component-processing-coverage-rows"
);
const validationIntroduction = document.getElementById(
    "validation-introduction"
);
const validationTaskHeading = document.getElementById(
    "validation-task-heading"
);
const statusCard = document.getElementById("validation-status-card");
const statusHeading = document.getElementById("validation-status-heading");
const statusMessage = document.getElementById("validation-status-message");
const resultsCard = document.getElementById("validation-results-card");
const resultsContent = document.getElementById("validation-results-content");

const artifactStatuses = {
    rdf: document.getElementById("artifact-rdf-status"),
    shacl: document.getElementById("artifact-shacl-status"),
    measurement: document.getElementById("artifact-measurement-status"),
    log: document.getElementById("artifact-log-status"),
};

let experienceProfile = {
    shows_overall_progress: true,
    shows_pipeline_stages: true,
    shows_technical_artifacts: true,
    shows_developer_diagnostics: true,
};

function setStatus(kind, heading, message) {
    statusCard.className = `card validation-status validation-status--${kind}`;
    statusHeading.textContent = heading;
    statusMessage.textContent = message;
}

function setArtifactStatus(artifact, status, kind) {
    const element = artifactStatuses[artifact];
    element.textContent = status;
    element.className = `artifact-status artifact-status--${kind}`;
}

function resetArtifacts() {
    setArtifactStatus("rdf", "Not Generated", "inactive");
    setArtifactStatus("shacl", "Not Generated", "inactive");
    setArtifactStatus("measurement", "Not Generated", "inactive");
    setArtifactStatus("log", "Pending", "pending");
}

function applyExperience(profile) {
    experienceProfile = profile;
    technicalPipelineSelection.hidden = !profile.shows_pipeline_stages;
    technicalPipelineSpacing.hidden = !profile.shows_pipeline_stages;
    technicalArtifactsSection.hidden = !profile.shows_technical_artifacts;
    schemaComponentProcessingCoverage.hidden = true;

    if (profile.shows_pipeline_stages) {
        validationTaskHeading.textContent = "Validation Pipeline";
        validationIntroduction.textContent =
            "Upload a UAD 3.6 appraisal XML instance document and select " +
            "the desired validation pipeline.";
        validateButton.textContent = "Validate";
        statusMessage.textContent =
            "Select an appraisal file and the validation to run.";
        return;
    }

    validationTaskHeading.textContent = "Validate Appraisal";
    validationIntroduction.textContent =
        "Upload a UAD 3.6 appraisal and validate it.";
    validateButton.textContent = "Validate Appraisal";
    statusMessage.textContent =
        "Select a UAD 3.6 appraisal and validate it.";
}

function appendCoverageCell(row, column, value) {
    const cell = document.createElement("td");
    cell.dataset.column = column;
    cell.textContent = String(value);
    row.appendChild(cell);
}

function showSchemaComponentProcessingCoverage(report) {
    schemaComponentProcessingCoverageRows.replaceChildren();

    for (const coverage of report.component_kinds) {
        const row = document.createElement("tr");
        row.dataset.componentKind = coverage.component_kind;
        appendCoverageCell(row, "component-kind", coverage.component_kind);
        appendCoverageCell(row, "found", coverage.found);
        appendCoverageCell(row, "processed", coverage.processed);
        appendCoverageCell(row, "status", coverage.status);
        schemaComponentProcessingCoverageRows.appendChild(row);
    }

    schemaComponentProcessingCoverage.hidden = false;
}

async function loadSchemaComponentProcessingCoverage() {
    const response = await fetch(
        "/schema/uad36/component-processing-coverage"
    );
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    showSchemaComponentProcessingCoverage(await response.json());
}

async function configureExperience() {
    // IT-64R1S2: the anonymous Demo page keeps its own presentation policy,
    // even when the server's configuration selects a Developer experience.
    // This controls presentation only; account authorization remains server-side.
    if (document.body.dataset.operatingMode === "demo") {
        applyExperience({
            shows_overall_progress: true,
            shows_pipeline_stages: false,
            shows_technical_artifacts: false,
            shows_developer_diagnostics: false,
        });
        return;
    }

    try {
        const response = await fetch("/configuration/experience");
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const profile = await response.json();
        applyExperience(profile);
        if (profile.shows_developer_diagnostics) {
            await loadSchemaComponentProcessingCoverage();
        }
    } catch (_error) {
        applyExperience(experienceProfile);
    }
}

const experienceReady = configureExperience();

function escapeHtml(value) {
    const element = document.createElement("div");
    element.textContent = String(value ?? "");
    return element.innerHTML;
}

function showResults(report) {
    const passed = report.status === "passed";
    const malformed = report.well_formed === false;
    const title = malformed
        ? "XML Parsing"
        : "UAD 3.6 XML Schema Validation";
    const summary = passed
        ? "The uploaded document conforms to the UAD 3.6 XML Schema."
        : malformed
            ? "The uploaded document is not well-formed XML."
            : "The document is well-formed XML but does not conform to the UAD 3.6 XML Schema.";

    const findings = report.findings.length === 0
        ? ""
        : `<ol class="finding-list">${report.findings.map((finding) => {
            const location = finding.line === null
                ? ""
                : ` <span class="finding-location">Line ${finding.line}${finding.column === null ? "" : `, column ${finding.column}`}</span>`;
            return `<li><span>${escapeHtml(finding.message)}</span>${location}</li>`;
        }).join("")}</ol>`;

    resultsContent.innerHTML = `
        <p class="result-stage">${title}</p>
        <p class="result-outcome result-outcome--${passed ? "passed" : "failed"}">
            ${passed ? "PASSED" : "FAILED"}
        </p>
        <p>${summary}</p>
        <dl class="result-summary">
            <div><dt>File</dt><dd>${escapeHtml(report.package_name)}</dd></div>
            <div><dt>Schema</dt><dd>${escapeHtml(report.schema_name)}</dd></div>
            <div><dt>Errors</dt><dd>${report.summary.error_count}</dd></div>
            <div><dt>Warnings</dt><dd>${report.summary.warning_count}</dd></div>
        </dl>
        ${findings}
    `;
    resultsCard.hidden = false;
    setArtifactStatus("log", "Generated", "generated");

    if (passed) {
        setArtifactStatus("rdf", "Ready for Next Stage", "ready");
        setArtifactStatus("shacl", "Not Generated", "inactive");
        setArtifactStatus("measurement", "Not Generated", "inactive");
    }
}

let reportDownloadUrl = null;
// IT-46R3S1: a correction continues the kind of validation being reviewed.
let reviewedIntegratedRunId = null;

// IT-46R2S1: display and export the same saved run without re-evaluation.
function showRequiredDataResults(report, filename) {
    reviewedIntegratedRunId = report.run_id;
    const resultUrl = new URL(window.location.href);
    resultUrl.searchParams.set("run_id", report.run_id);
    window.history.replaceState(null, "", resultUrl);
    if (!experienceProfile.shows_pipeline_stages) {
        validateButton.textContent = "Validate corrected file";
    }
    const coverage = report.coverage;
    const findings = report.findings || [];
    const schema = report.schema;
    const incomplete = report.processing_status !== "completed" ||
        !coverage || !coverage.complete;
    const state = incomplete ? "INCOMPLETE" : report.passed ? "PASSED" : "FINDINGS DETECTED";
    const hasSchemaFindings = Boolean(schema && schema.findings && schema.findings.length);
    const summary = findings.length || hasSchemaFindings
        ? "Findings detected. Review the schema assessment and business-rule findings below."
        : "No issues were found within the evaluated coverage.";
    const failure = report.failure ? `
        <p role="alert"><strong>Validation incomplete.</strong> ${escapeHtml(report.failure.message)}</p>
        <p>${escapeHtml(report.failure.suggested_action)}</p>
    ` : incomplete ? '<p role="alert">Validation incomplete. Some required checks did not finish. Retry validation or contact support.</p>' : "";
    const findingList = findings.length ? `<ol class="finding-list">${findings.map(finding => `
        <li data-finding-id="${escapeHtml(finding.finding_id)}">
            <p><strong>${escapeHtml(String(finding.severity).toUpperCase())}</strong>
                ${escapeHtml(finding.rule_id || "Schema assessment")}
                ${finding.row_id ? ` â€” Row ${escapeHtml(finding.row_id)}` : ""}</p>
            <p>${escapeHtml(finding.finding)}</p>
            <p><strong>Expected:</strong> ${escapeHtml(finding.expected_condition || "See the governed assessment.")}</p>
            ${finding.primary_data_element ? `<p>Element: ${escapeHtml(finding.primary_data_element)}</p>` : ""}
            ${finding.data_location ? `<details><summary>XML context</summary><code>${escapeHtml(finding.data_location)}</code></details>` : ""}
            ${finding.source ? `<details><summary>Source provenance</summary>
                <p>${escapeHtml(finding.source.source_document)} ${escapeHtml(finding.source.source_version || "")}</p>
                <p>${escapeHtml(finding.source.source_section || "")}</p></details>` : ""}
        </li>`).join("")}</ol>` : "<p>No business-rule findings were detected within the evaluated coverage.</p>";
    const coverageHtml = coverage ? `
        <section data-validation-coverage aria-label="Validation coverage">
            <h4>Selected constraint coverage</h4>
            <dl class="result-summary">
                <div><dt>Selected checks</dt><dd data-coverage-count="selected">${coverage.selected_rule_ids.length}</dd></div>
                <div><dt>Evaluated checks</dt><dd data-coverage-count="evaluated">${coverage.evaluated_rule_ids.length}</dd></div>
                <div><dt>Not evaluated</dt><dd data-coverage-count="not-evaluated">${coverage.not_evaluated.length}</dd></div>
                <div><dt>Workbook rules outside selected coverage</dt><dd>${coverage.unselected_rule_ids.length}</dd></div>
            </dl>
            <p>This result does not establish complete UAD compliance. Rules outside the selected coverage have not been evaluated by this run.</p>
            ${coverage.not_evaluated.length ? `<h5>Deferred or failed checks</h5><ul>${coverage.not_evaluated.map(item =>
                `<li><strong>${escapeHtml(item.rule_id)}</strong>: ${escapeHtml(item.reason)}</li>`
            ).join("")}</ul>` : "<p>Every selected business-rule check completed its applicability and validation assessment.</p>"}
            <details><summary>Evaluated rule IDs</summary><p>${escapeHtml(coverage.evaluated_rule_ids.join(", "))}</p></details>
            <details><summary>Rules outside selected coverage</summary><p>${escapeHtml(coverage.unselected_rule_ids.join(", "))}</p></details>
            <details><summary>Constraint-set provenance</summary>
                <p>Version: ${escapeHtml(coverage.constraint_set.version)}</p>
                <p>Source: ${escapeHtml(coverage.constraint_set.source_document)}</p>
                <p>Worksheet: ${escapeHtml(coverage.constraint_set.source_sheet)}</p>
                <p>SHA-256: ${escapeHtml(coverage.constraint_set.sha256)}</p>
            </details>
        </section>` : '<section data-validation-coverage><h4>Coverage unavailable</h4><p>Validation is incomplete. No unevaluated check is reported as passing.</p></section>';
    const schemaHtml = schema ? `
        <section aria-label="XML Schema assessment"><h4>XML Schema assessment</h4>
            <p>${schema.well_formed ? schema.schema_valid ? "The upload conforms to the governed XML Schema." : "The upload does not conform to the governed XML Schema." : "The upload is not well-formed XML."}</p>
            <p>${escapeHtml(schema.schema_version)}</p>
            <ul>${schema.findings.map(item => `<li>${escapeHtml(item.message)}${item.line != null ? ` â€” Line ${escapeHtml(item.line)}` : ""}</li>`).join("")}</ul>
        </section>` : '<section aria-label="XML Schema assessment"><h4>XML Schema assessment unavailable</h4><p>No schema-validity conclusion was produced.</p></section>';

    resultsContent.dataset.validationRunId = report.run_id;
    resultsContent.innerHTML = `
        <p class="result-stage">Validation results</p>
        <p class="result-outcome result-outcome--${incomplete || !report.passed ? "failed" : "passed"}">${state}</p>
        <p>Processing: ${escapeHtml(report.processing_status || "incomplete")}</p>
        <p>${summary}</p>${failure}
        <dl class="result-summary">
            <div><dt>Run</dt><dd>${escapeHtml(report.run_id)}</dd></div>
            <div><dt>File</dt><dd>${escapeHtml(report.package_name || filename)}</dd></div>
            <div><dt>Upload SHA-256</dt><dd>${escapeHtml(report.source_sha256)}</dd></div>
        </dl>
        ${schemaHtml}${coverageHtml}
        <h4>Business-rule findings</h4>${findingList}
        <p><a data-download-report>Download report (JSON)</a></p>
    `;
    // Export the exact recorded response, preserving finding order and identity.
    if (reportDownloadUrl) URL.revokeObjectURL(reportDownloadUrl);
    reportDownloadUrl = URL.createObjectURL(new Blob(
        [JSON.stringify(report, null, 2)], {type: "application/json;charset=utf-8"}
    ));
    const download = resultsContent.querySelector("[data-download-report]");
    download.href = reportDownloadUrl;
    download.download = `validation-report-${String(report.run_id).replace(/[^a-zA-Z0-9_-]/g, "_")}.json`;
    resultsCard.hidden = false;
    setArtifactStatus("log", "Generated", "generated");
    setStatus(incomplete || !report.passed ? "failed" : "passed",
        incomplete ? "Validation incomplete" : "Validation completed", summary);
}

async function openSavedValidationResult() {
    const runId = new URLSearchParams(window.location.search).get("run_id");
    if (!runId) return;
    await experienceReady;
    setStatus("running", "Loading validation results", "Opening the recorded validation run.");
    try {
        const response = await fetch(`/validation-runs/${encodeURIComponent(runId)}`, {cache: "no-store"});
        if (!response.ok) {
            throw new Error(response.status === 404
                ? "This validation run is unavailable. Submit the file again or contact support with its run ID."
                : "The saved result could not be loaded. Please retry or contact support.");
        }
        const report = await response.json();
        if (report.run_id !== runId) throw new Error("The service returned a different validation run. Please retry.");
        showRequiredDataResults(report, report.package_name);
    } catch (error) {
        showRequestError(error instanceof Error ? error.message : "The saved result could not be opened. Please retry.");
    }
}

void openSavedValidationResult();

function showUserPipelineResults(report) {
    const completed = report.status === "completed";
    const message = completed
        ? "The appraisal was processed successfully."
        : report.message;

    resultsContent.innerHTML = `
        <p class="result-outcome result-outcome--${completed ? "passed" : "failed"}">
            ${completed ? "COMPLETED" : "FAILED"}
        </p>
        <p>${escapeHtml(message)}</p>
        <dl class="result-summary">
            <div><dt>File</dt><dd>${escapeHtml(report.package_name)}</dd></div>
        </dl>
    `;
    resultsCard.hidden = false;
}

function showDeveloperPipelineResults(report) {
    const stage = report.stages[0];
    const completed = report.status === "completed";
    const tripleCount = completed ? stage.artifacts.rdf_triple_count : null;
    const description = completed
        ? "The uploaded appraisal was projected into an RDF instance graph."
        : stage.error.business_message;

    resultsContent.innerHTML = `
        <p class="result-stage">RDF Projection</p>
        <p class="result-outcome result-outcome--${completed ? "passed" : "failed"}">
            ${completed ? "COMPLETED" : "FAILED"}
        </p>
        <p>${escapeHtml(description)}</p>
        <dl class="result-summary">
            <div><dt>File</dt><dd>${escapeHtml(report.package_name)}</dd></div>
            ${completed ? `<div><dt>Triples</dt><dd>${tripleCount}</dd></div>` : ""}
        </dl>
    `;
    resultsCard.hidden = false;

    if (completed) {
        setArtifactStatus("rdf", "Generated", "generated");
    }
    setArtifactStatus("log", "Generated", "generated");
}

function showPipelineResults(report) {
    if (experienceProfile.shows_pipeline_stages) {
        showDeveloperPipelineResults(report);
    } else {
        showUserPipelineResults(report);
    }
}

function showRequestError(message) {
    delete resultsContent.dataset.validationRunId;
    setStatus("failed", "Validation request failed", message);
    resultsContent.innerHTML = `<p>${escapeHtml(message)}</p>`;
    resultsCard.hidden = false;
    setArtifactStatus("log", "Not Generated", "inactive");
}

async function readRequiredDataXml(file) {
    const bytes = new Uint8Array(await file.arrayBuffer());
    let text;
    try {
        text = new TextDecoder("utf-8", {fatal: true}).decode(bytes);
    } catch (_error) {
        throw new Error(
            "Required Data Validation currently accepts UTF-8 XML. " +
            "Please export the appraisal as UTF-8 XML."
        );
    }
    if (text.includes("\u0000")) {
        throw new Error(
            "Required Data Validation currently accepts UTF-8 XML."
        );
    }
    const declaration = text.match(
        /^\s*<\?xml\b[^?]*\bencoding\s*=\s*["']([^"']+)["']/i
    );
    if (declaration && !/^(utf-8|utf8|us-ascii|ascii)$/i.test(declaration[1])) {
        throw new Error(
            "Required Data Validation currently accepts UTF-8 XML. " +
            "Please export the appraisal as UTF-8 XML."
        );
    }
    return text;
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await experienceReady;

    const file = fileInput.files[0];
    const selectedPipeline = experienceProfile.shows_pipeline_stages
        ? form.querySelector('input[name="pipeline"]:checked').value
        : (document.body.dataset.validationUpload === "integrated" || reviewedIntegratedRunId)
            ? "required-data" : "rdf-projection";
    const isRdfProjection = selectedPipeline === "rdf-projection";
    const isRequiredData = selectedPipeline === "required-data";

    if (!file) {
        setStatus(
            "failed",
            "No file selected",
            "Select a UAD 3.6 appraisal before validating."
        );
        return;
    }

    resetArtifacts();
    delete resultsContent.dataset.validationRunId;
    resultsCard.hidden = true;
    validateButton.disabled = true;
    setStatus(
        "running",
        "Validation in progress",
        experienceProfile.shows_pipeline_stages
            ? "Running the selected validation stage."
            : "Checking the appraisal."
    );

    try {
        let endpoint;
        let options;

        if (isRequiredData) {
            const xmlText = await readRequiredDataXml(file);
            endpoint = "/validate/uad36";
            options = {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    package_name: file.name,
                    xml_text: xmlText,
                    investor_scope: "both",
                }),
            };
        } else {
            const formData = new FormData();
            formData.append("file", file);
            if (isRdfProjection) {
                formData.append("pipeline", selectedPipeline);
            }
            endpoint = isRdfProjection
                ? "/validate/uad36/pipeline"
                : "/validate/uad36/xml-schema";
            options = {method: "POST", body: formData};
        }

        const response = await fetch(endpoint, options);
        if (!response.ok) {
            throw new Error(
                `The validation service returned HTTP ${response.status}.`
            );
        }

        const report = await response.json();

        if (isRequiredData) {
            showRequiredDataResults(report, file.name);
            return;
        }

        if (isRdfProjection) {
            showPipelineResults(report);
            if (report.status === "completed") {
                setStatus(
                    "passed",
                    experienceProfile.shows_pipeline_stages
                        ? "RDF Projection completed"
                        : "Validation completed",
                    experienceProfile.shows_pipeline_stages
                        ? "The loaded appraisal was projected without selecting the file again."
                        : "The appraisal was processed successfully."
                );
            } else {
                const message = experienceProfile.shows_pipeline_stages
                    ? report.stages[0].error.business_message
                    : report.message;
                setStatus("failed", "Validation failed", message);
            }
            return;
        }

        showResults(report);

        if (report.status === "passed") {
            setStatus(
                "passed",
                "XML Schema validation passed",
                "The document is a valid UAD 3.6 XML instance and is ready for the next processing stage."
            );
        } else if (report.well_formed === false) {
            setStatus(
                "failed",
                "XML parsing failed",
                "The uploaded file is not well-formed XML. Processing stopped."
            );
        } else {
            setStatus(
                "failed",
                "XML Schema validation failed",
                "The document does not conform to the UAD 3.6 XML Schema. Processing stopped."
            );
        }
    } catch (error) {
        showRequestError(
            error instanceof Error
                ? error.message
                : "An unexpected validation error occurred."
        );
    } finally {
        validateButton.disabled = false;
    }
});
