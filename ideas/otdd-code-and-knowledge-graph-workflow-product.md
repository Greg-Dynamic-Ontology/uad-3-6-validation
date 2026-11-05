# Product idea: OTDD execution for code and knowledge graphs

Recorded: October 30, 2026

Status: Parked idea. UAD revenue work remains the priority.

## Concept

An Ontology CI/CD or BDD package that executes the OTDD design across both
application code and knowledge graphs (KGs).

Carry governed requirements through a traceable workflow:

**Feature → Rule → Scenario → executable test → code or knowledge change →
verified evidence**

The operator selects a feature and works through its rules and scenarios.
The application remembers progress, runs the appropriate checks, coordinates
implementation, and preserves evidence.
Python's `iter()` could traverse scenarios; durable workflow state would control
advancement and resumption.

## What it could govern

- Application behavior and API/browser integration.
- Ontology classes, properties, identities, and relationships.
- RDF ingestion, transformations, and provenance.
- SHACL shapes and validation behavior.
- Configuration knowledge and vocabulary synchronization.
- Integration between executable code and governed knowledge.

## Essential workflow rules

- Check prerequisites before starting a scenario.
- Distinguish behavioral RED from blocked setup, unavailable infrastructure,
or missing credentials.
- Preserve the two-pass process: establish the test result, then implement an
authorized change that makes it GREEN.
- Record already-GREEN scenarios without manufacturing failures.
- Keep completed iteration requirements unchanged; document subsequent repairs and
their reasons.
- Associate test results with the exact requirement, code revision, and knowledge
artifact versions evaluated.
- Preserve human review decisions and resume interrupted work from saved state.
- Generate a matching Live QA Script after a UI scenario is GREEN, when requested.
- Run focused checks during scenario development, iteration regression at feature
completion, and full regression before the iteration commit.
- Keep implementation verification distinct from authorization to publish or deploy.

## Product distinction

The opportunity is a unified OTDD method and execution system for code and
knowledge—not merely another test runner.
It would make requirements, transformations, verification results, and acceptance
decisions inspectable together.

This is a product hypothesis; market demand and differentiation remain to be
investigated.

## Existing foundations to investigate later

- [GitHub Spec Kit](https://github.com/github/spec-kit): structured specification-driven development with coding agents.
- [pytest-bdd](https://github.com/pytest-dev/pytest-bdd): executable Gherkin scenarios through pytest.
- [LangGraph](https://reference.langchain.com/python/langgraph/types/interrupt): agent workflow state, persistence, and human decision points.
- [Temporal Python SDK](https://docs.temporal.io/develop/python): durable workflow orchestration.

These may provide components. Their fit to the complete OTDD process has not been
established.

## Smallest useful starting point

Select a feature, identify its next unfinished scenario, check prerequisites, run
its associated test, and save the result with traceability to the feature and
repository revision.
Add controlled code/KG changes and CI/CD integration after this foundation proves
useful.

No implementation is authorized by this idea note.
