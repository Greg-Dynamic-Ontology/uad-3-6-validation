# ADR-0016: Schema Loader Modularization

## Status

Accepted

## Context

The XML Schema loader currently consists of a single implementation module
(schema_loader.py) of approximately 367 lines.

As support for additional XML Schema constructs grows, this module will
continue to increase in size and complexity. The current organization makes
individual responsibilities difficult to locate, review, and evolve.

The project now has over 200 passing automated tests covering the observable
behavior of the loader. This provides sufficient protection to perform
behavior-preserving architectural refactoring.

## Decision

The schema loader shall be decomposed into a package of focused modules,
organized according to XML Schema concepts rather than implementation
mechanics.

The public API shall remain unchanged.

Existing callers shall continue to use:

    SchemaLoader().load(...)

The SchemaLoader class becomes an orchestration façade responsible for
coordinating specialized loading functions.

Each module shall have a single primary responsibility.

Examples include:

- namespace loading
- QName resolution
- simple type loading
- complex type loading

Additional XML Schema concepts shall be added as separate modules rather than
expanding existing ones whenever practical.

## Consequences

Positive

- Smaller implementation units
- Improved readability
- Easier code review
- Better alignment with OTDD
- Easier AI-assisted development
- Lower merge conflict risk
- Clear mapping between XML Schema concepts and implementation

Negative

- Increased number of modules
- Slight increase in import management

Neutral

No externally observable behavior changes are expected.

All existing tests shall continue to pass throughout the refactoring.

## Alternatives Considered

Continue expanding a single schema_loader.py module.

Rejected because the implementation complexity would continue to grow while
mixing unrelated XML Schema concepts into one file.

Decompose by programming constructs (utilities, helpers, parsers).

Rejected because the project architecture is intentionally organized around
domain concepts rather than implementation techniques.