# ADR-0012: Validation-Derived Analytics and AI Assistance

**Status:** Proposed

## Context

The UAD 3.6 Validation project produces deterministic validation results by deriving semantic knowledge from UAD appraisal documents. The validation pipeline performs XML validation, semantic projection, business-rule validation, SHACL validation, and measurement generation.

Each validation run produces structured metadata describing both the submitted appraisal and the validation process. Over time, these metadata represent an increasingly valuable corpus of derived knowledge.

Recent advances in AI and graph-based retrieval suggest opportunities to improve user experience and identify industry-wide trends. However, the project philosophy remains:

> **Derivation, not divination.**

The project must not replace deterministic validation with probabilistic inference.

## Problem

Determine whether accumulated validation metadata should become the basis for AI-assisted capabilities and subscription services without compromising the deterministic nature of validation.

## Decision

No implementation decision is made by this ADR.

The project will recognize validation-derived metadata as a strategic asset and preserve sufficient provenance to support future analytical and AI capabilities.

Future AI capabilities SHALL consume deterministic validation results rather than replace deterministic validation.

## Principles

The following principles shall guide future work:

* Deterministic validation remains the authoritative source of truth.
* AI shall not determine whether a UAD document conforms.
* Every validation result shall remain traceable to the originating XML, RDF projection, business rule, or SHACL constraint.
* AI-generated recommendations shall be clearly distinguished from deterministic findings.
* Validation metadata should be retained in a form suitable for longitudinal analysis.

## Potential Applications

Examples of future capabilities include:

* Detection of emerging validation trends.
* Identification of systemic implementation issues.
* Statistical prioritization of review activities.
* AI-assisted explanation of validation findings.
* Suggested corrective actions based on previously accepted corrections.
* Detection of anomalous appraisal patterns.
* Cross-version comparison of appraisal software quality.
* Vendor benchmarking using anonymized aggregate metrics.

## Commercial Opportunities

Validation-derived metadata may support future subscription services for appraisal software vendors, lenders, and other ecosystem participants.

Potential services include:

* Early warning of implementation defects.
* Product quality dashboards.
* Release quality monitoring.
* Industry benchmarking.
* Trend analysis.
* Operational metrics.
* Emerging business-rule impact analysis.

These services shall be based on aggregated and appropriately anonymized validation metadata.

## Consequences

### Positive

* Preserves deterministic validation as the authoritative process.
* Creates opportunities for high-value analytical services.
* Establishes provenance suitable for explainable AI.
* Enables future GraphRAG and retrieval-based AI architectures.
* Encourages long-term retention of validation measurements.

### Negative

* Requires careful governance of retained validation metadata.
* Introduces future considerations regarding privacy, anonymization, and customer consent.
* May require additional storage and metadata management.

## Future Work

Potential future ADRs may address:

* Metadata retention policies.
* Customer privacy and anonymization.
* AI architecture.
* GraphRAG integration.
* Subscription analytics products.
* Vendor benchmarking methodologies.

---

I would make one small change from our earlier discussion. I intentionally broadened the 
title from **"AI"** to **"Validation-Derived Analytics and AI Assistance."**

The commercial opportunity you've identified is actually larger than AI. Many of the most 
valuable capabilities—trend reports, benchmarking, release-quality dashboards, and early 
warning—can be implemented with deterministic analytics long before introducing machine 
learning. 
AI then becomes an enhancement to an already valuable analytics platform, rather than the 
product itself.
