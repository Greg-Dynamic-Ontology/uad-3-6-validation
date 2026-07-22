"use strict";

const form = document.getElementById("validation-form");
const fileInput = document.getElementById("appraisal-file");
const validateButton = document.getElementById("validate-button");
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

function showResults(report) {
    const passed = report.status === "passed";
    const malformed = report.well_formed === false;
    const title = malformed
        ? "XML Parsing"
        : "UAD 3.6 XML Schema Validation";
    const outcome = passed ? "PASSED" : "FAILED";
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
        <p class="result-outcome result-outcome--${passed ? "passed" : "failed"}">${outcome}</p>
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

function showRequestError(message) {
    setStatus("failed", "Validation request failed", message);
    resultsContent.innerHTML = `<p>${escapeHtml(message)}</p>`;
    resultsCard.hidden = false;
    setArtifactStatus("log", "Not Generated", "inactive");
}

function escapeHtml(value) {
    const element = document.createElement("div");
    element.textContent = String(value);
    return element.innerHTML;
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const file = fileInput.files[0];
    if (!file) {
        setStatus("failed", "No file selected", "Select a UAD 3.6 appraisal XML instance document before validating.");
        return;
    }

    resetArtifacts();
    resultsCard.hidden = true;
    validateButton.disabled = true;
    setStatus("running", "Validation in progress", "Parsing the XML document and validating it against the UAD 3.6 XML Schema.");

    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch("/validate/uad36/xml-schema", {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            throw new Error(`The validation service returned HTTP ${response.status}.`);
        }

        const report = await response.json();
        showResults(report);

        if (report.status === "passed") {
            setStatus("passed", "XML Schema validation passed", "The document is a valid UAD 3.6 XML instance and is ready for the next processing stage.");
        } else if (report.well_formed === false) {
            setStatus("failed", "XML parsing failed", "The uploaded file is not well-formed XML. Processing stopped.");
        } else {
            setStatus("failed", "XML Schema validation failed", "The document does not conform to the UAD 3.6 XML Schema. Processing stopped.");
        }
    } catch (error) {
        showRequestError(error instanceof Error ? error.message : "An unexpected validation error occurred.");
    } finally {
        validateButton.disabled = false;
    }
});
