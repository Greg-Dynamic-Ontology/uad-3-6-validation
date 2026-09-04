# OTDD Steps

## Purpose

This document defines the repeatable Ontology Test-Driven Development (OTDD) process for
taking a governed validation constraint from its source representation through an executable
SHACL validation.

The process separates source requirements, semantic interpretation, behavioral specification,
and executable validation. SHACL is an implementation representation near the end of the process,
not the starting point.

The first UAD 3.6 constraint used to exercise this process is `0100.0007 / UAD1001`, concerning
`AddressLineText` for the Subject Property physical address.

## 1. Capture the governed source row exactly

Preserve the constraint as supplied by its governing source before interpreting it.
The source we are using in this example is the Fannie Mae issued
appendix-h-1-uad-compliance-rules-urar.xlsx.

Other constraint documents will require analysis to find equivalent data as to
that documented here.

Capture all available source information, including:

- constraint identifier;
- rule identifier;
- data point;
- requirement wording;
- failure or trigger condition;
- severity;
- business context;
- XPath or other source location information; and
- source provenance.

For UAD1001, the governed source includes `0100.0007`, `UAD1001`,
`AddressLineText`, Fatal severity, and the Subject Property physical-address
context.

The source representation remains authoritative evidence of what was received.

## 2. Normalize the row as a governed constraint requirement

Transform the source row into a machine-readable Constraint Requirement Model
without discarding its governed identity or provenance.

The normalized requirement should represent concepts such as:

- source constraint identity;
- governed rule identity;
- subject or data point;
- requirement statement;
- applicability context;
- violation condition;
- severity; and
- source provenance.

Normalization is not semantic reinvention.
It makes the source requirement explicit and processable while retaining
a trace back to the original row.

A spreadsheet row does **not** automatically become a separate
Gherkin scenario. 
Gherkin represents behavioral patterns; the normalized constraint requirement
represents the individual governed requirement.

## 3. Create or extend the governing OTDD Feature and Rule

Identify the behavior class represented by the normalized constraint and place
it under the appropriate OTDD Feature and Rule.

Mint and preserve the OTDD Rule and Scenario identifiers according to project
conventions.

The Feature and Rule describe what the system must know and do.
They should not merely duplicate spreadsheet rows and should not prematurely
prescribe SHACL syntax.

A constraint with genuinely unique behavior may justify a dedicated Scenario.
Constraints sharing the same behavioral pattern should normally be exercised
as governed test data under that pattern.

## 4. Ingest the governed constraint as knowledge

> Governed Constraint Representation — The project representation of a
> normalized constraint requirement that preserves the requirement's governed
> identity, meaning, applicability, severity, and provenance independently
> of any executable validation representation such as SHACL.

Clearly the governed constraint representation may be different for project to
project.

What we are trying to constrct is knowledge about the knowledge we have and
need in order have a succesful implementation. 
Load or construct the normalized constraint requirement in the project's
governed constraint representation.

Tests should establish that ingestion preserves the source identity,
requirement, severity, context, and provenance and does not silently discard
source meaning.

At this point the project should possess the requirement as governed knowledge
independently of any particular SHACL implementation.

## 5. Resolve the constraint vocabulary against the Logical Schema Model

Bind the terms in the requirement to the established UAD Logical Schema RDF.

For example, begin with `AddressLineText`, resolve its governed QName identity,
find the schema resources that reference it, and determine the structural
contexts in which it occurs.

The constraint conforms to the RDF design; it does not redesign it.

GraphDB and SPARQL are useful engineering tools for this discovery,
but GraphDB is not required as part of the validation runtime.

## 6. Prove the intended context with SPARQL

Use SPARQL to express and test the graph pattern to which the constraint
applies.

For UAD1001, the graph investigation must distinguish the `ADDRESS` used as
the Subject Property physical address from other valid uses of `ADDRESS`, such
as additional-address contexts.

This step serves two purposes:

1. it verifies our understanding of the Logical Schema graph; and
2. it establishes the semantic targeting knowledge needed by the executable
constraint.

SPARQL is therefore a discovery and proof tool in the OTDD process, not an
accidental dependency of production validation.

## 7. State the validation behavior independently of SHACL

Describe the required validation behavior without referring to SHACL
implementation constructs.

For example:

> For the ADDRESS serving as the Subject Property physical address,
> AddressLineText must be present. 
> Its absence produces the governed UAD1001 validation result with Fatal
> severity.

At this point the target context, required condition, violation condition,
governed result identity, and severity should all be understandable without
mentioning `sh:minCount`, SHACL paths, or SHACL-SPARQL.

## 8. Create positive and negative RDF fixtures

Create minimal RDF instance graphs that demonstrate the intended behavior.

At minimum, include:

- a conforming instance in which the governed requirement is satisfied;
- a violating instance in which only the governed requirement is violated; and
- where context matters, an instance demonstrating that the same data
structure in an unrelated context does not trigger the constraint.

For UAD1001, an ADDRESS outside the Subject Property physical-address context
should not be rejected merely because it lacks `AddressLineText` unless
another governed constraint requires it there.

## 9. Write the SHACL acceptance tests first

Write tests for the Rule before implementing the SHACL shape and establish the
expected RED state.

Tests should prove, as applicable, that:

- the conforming fixture passes;
- the violating fixture fails;
- the correct governed constraint is reported;
- the reported severity matches the governed severity;
- unrelated contexts do not produce false violations; and
- the validation result remains traceable to the governed source requirement.

The tests describe the required behavior. 
They should not pass merely because a particular SHACL implementation happens
to exist.

## 10. Implement the smallest SHACL representation that makes the Rule green

Implement the executable SHACL constraint only after the behavior, context,
fixtures, and tests are established.

Prefer SHACL Core when it faithfully represents the requirement. 
Use SHACL-SPARQL when the governed context or condition genuinely requires
additional expressive power.

Implementation may include constructs such as targets, paths, cardinality
constraints, severity mappings, and provenance annotations, but those
constructs implement knowledge established in the preceding steps.

Run the focused Rule tests until they are green, then run the complete
regression suite.

Feature-complete is not implementation-complete: the Rule is complete only
when its required behavior is implemented and proven without breaking existing
behavior.

## 11. Commit at the Rule break

When all Scenarios belonging to the OTDD Rule are green and the full
regression suite passes, commit at the Rule boundary.

The commit message should identify the OTDD Rule and the semantic
accomplishment rather than merely listing implementation mechanics.

Push the commit so that the Rule break becomes a durable project checkpoint.

The completed increment should provide an auditable chain:

 - **governed source row →**
 - **normalized constraint requirement →**
 - **Logical Schema binding →**
 - **SPARQL understanding →**
 - **behavioral specification →**
 - **RDF fixtures →**
 - **RED tests →**
 - **SHACL implementation →**
 - **GREEN tests →**
 - **regression →**
 - **Rule-break commit**

## OTDD Principle

The governing principle of this process is that the executable SHACL shape
is not the requirement itself. 
It is one representation of knowledge whose identity, meaning, applicability,
and expected behavior have already been established and tested.

**Software is only one representation of knowledge.**
