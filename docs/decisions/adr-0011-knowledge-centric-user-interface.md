# ADR-011: Knowledge-Centric User Interface

## Status

Accepted

## Context

The UAD 3.6 Validation project is knowledge-centric.

The project represents appraisal meaning, validation rules, measurements, and relationships 
explicitly rather than burying them entirely in procedural code.

ADR-010 establishes role-based user experiences. The initial roles are:

- Business User
- Technical User

These roles use the same validation and repair capabilities but require different terminology 
and levels of technical detail.

For example, the same capability may be presented as:

| Business User               | Technical User              |
|-----------------------------|-----------------------------|
| Check File                  | Validate XML Structure      |
| Repair Common File Problems | Normalize XML               |
| Check Appraisal             | Run UAD Validation          |
| View Results                | View Validation Diagnostics |

A conventional implementation would place these labels and descriptions directly in HTML, 
JavaScript, Python dictionaries, or templates.

That approach would work, but it would make the user interface language another collection of 
hard-coded values distributed throughout the application.

A knowledge-centric alternative is to represent application capabilities, user roles, and 
role-appropriate presentation text in a graph.

The application could then derive portions of its user interface from explicit knowledge about:

- what the application can do
- which roles may use a capability
- how a capability should be described to each role
- what explanatory text should accompany it?
- which service or workflow implements it?

This would make the user interface another projection of the application's knowledge model.

However, the project also has an immediate delivery goal: the sample-repair capability 
should be available through the application this week.

The knowledge-centric user interface must not delay that delivery.

## Decision

The application SHALL adopt a knowledge-centric model for role-dependent user interface 
presentation.

The model SHALL represent application capabilities independently of their presentation.

A capability represents something the application can do.

Examples include:

- checking an appraisal file
- repairing common file problems
- validating an appraisal
- generating a report
- projecting appraisal data into the canonical internal representation
- running business-rule validation

Role-specific presentation resources may provide:

- menu labels
- button labels
- page headings
- short descriptions
- help text
- status messages
- technical explanations

The same capability may have different presentation resources for different roles.

The application SHALL continue to use one implementation of each capability regardless of how 
that capability is presented.

The graph SHALL describe and present capabilities. 
It SHALL NOT replace the application service layer or contain executable application logic.

## Capability and Presentation Separation

The knowledge model SHALL distinguish between:

1. **Capability**

   What the application does.

2. **Role**

   The perspective from which the user interacts with the application.

3. **Presentation**

   How a capability is described to a particular role.

4. **Implementation Binding**

   The application service, route, or workflow that performs the capability.

For example:

```text
Repair Appraisal File
        |
        +-- Business User presentation:
        |      Repair Common File Problems
        |
        +-- Technical User presentation:
        |      Normalize XML
        |
        +-- Implementation:
               XML whitespace cleanup service
```
The capability remains stable even when labels, descriptions, or interface layouts change.

## Initial Roles
The initial user interface roles are defined in ADR-010:
- Business User
- Technical User
Additional roles may be introduced later without requiring duplicate validation or repair 
implementations.
## Initial Graph Scope
The first graph-backed user interface model SHOULD remain deliberately small.

It may initially represent:
- role identifiers
- capability identifiers
- role-specific labels
- role-specific descriptions
- display order
- capability availability
- implementation identifiers

The initial model SHOULD NOT attempt to represent:
- complete page layouts
- arbitrary HTML
- CSS styling
- browser behavior
- executable JavaScript
- application control flow
- validation algorithms
- repair algorithms

These remain the responsibilities of the application code.

## Illustrative Model
The following is illustrative rather than final vocabulary:
```turtle
@prefix ui: <https://dynamicontology.com/uad36/ui#> .
@prefix role: <https://dynamicontology.com/uad36/role#> .
@prefix capability: <https://dynamicontology.com/uad36/capability#> .

role:BusinessUser
    a ui:UserRole ;
    ui:label "Business User" .

role:TechnicalUser
    a ui:UserRole ;
    ui:label "Technical User" .

capability:RepairAppraisalFile
    a ui:Capability ;
    ui:implementationId "repair-appraisal-file" ;
    ui:hasPresentation [
        a ui:RolePresentation ;
        ui:forRole role:BusinessUser ;
        ui:label "Repair Common File Problems" ;
        ui:description
            "Create a corrected copy of an appraisal file with common formatting problems repaired."
    ] ;
    ui:hasPresentation [
        a ui:RolePresentation ;
        ui:forRole role:TechnicalUser ;
        ui:label "Normalize XML" ;
        ui:description
            "Create a normalized XML copy by repairing supported simple-content whitespace defects."
    ] .
```
The exact vocabulary and namespace SHALL be settled through tests and implementation work.

## Incremental Delivery
This decision SHALL be implemented incrementally.

The knowledge-centric user interface is not a prerequisite for delivering the first 
sample-repair feature.

The first sample-repair release MAY use role-specific text stored directly in application 
code or static user interface files.

Such text SHALL be treated as an interim projection of the intended knowledge model rather 
than as the final source of truth.

The implementation sequence shall be:
1. Deliver the sample-repair capability through the application.
2. Establish Business User and Technical User presentations for that capability.
3. Define the minimum graph vocabulary needed to represent the capability and its presentations.
4. Add tests for graph-based presentation selection.
5. Replace interim hard-coded presentation text with graph-derived text.
6. Extend the graph only as additional capabilities require it.

No graph infrastructure work SHALL delay the initial sample-repair delivery unless that work 
is directly required by the repair feature.

## Sample-Repair Priority
The immediate project priority is to make sample repair available through the application this
week.

The first delivered workflow should allow a user to:
1. Select or upload an appraisal file.
2. Check the file.
3. See that repairable formatting problems were detected.
4. Create a repaired copy.
5. Preserve the original file unchanged.
6. Recheck the repaired copy.
7. Download or otherwise save the repaired artifact.

The Business User experience should use a language such as:
- Check File
- Repair Common File Problems
- Create Repaired Copy
- Check Repaired File

The Technical User experience may additionally expose:
- XML Schema validation
- normalization counts
- affected element details
- validation diagnostics
- generated artifact information

The underlying repair operation SHALL be identical for both roles.

## Source of Truth

During the incremental implementation period, presentation information may exist temporarily 
in both application code and the graph.

Once graph-backed presentation is operational and tested, the graph SHALL become the 
authoritative source for role-dependent presentation text covered by the model.

Application code may provide fallback text so that failure to load presentation knowledge does 
not prevent essential validation or repair operations.

Fallback behavior SHALL be explicit and tested.

## Testing

The knowledge-centric user interface SHALL be developed using tests.

Tests should establish that:

- every modeled capability has a stable identifier
- every supported role has an appropriate presentation for required capabilities
- a Business User receives business-oriented terminology
- a Technical User receives technical terminology
- both presentations invoke the same underlying capability
- missing presentation text produces a defined fallback
- graph changes do not alter validation or repair outcomes
- the sample-repair capability remains usable if graph presentation data cannot be loaded

The graph itself SHALL be syntactically valid RDF and subject to ontology and vocabulary tests 
consistent with existing project practices.

## Rationale

Representing role-specific interface knowledge in a graph is consistent with the project's knowledge-centric architecture.

It makes explicit the relationship among:

- users
- roles
- capabilities
- terminology
- help content
- implementation services

It also separates what the application does from how that work is explained.

This provides a foundation for the future:

- additional user roles
- localization
- accessibility descriptions
- contextual help
- guided workflows
- documentation generation
- account-specific experiences
- product editions or licensed capability sets

The incremental-delivery rule prevents the architectural direction from becoming speculative 
infrastructure that delays a useful feature.

## Consequences
## Positive Consequences
- Role-dependent terminology becomes explicit knowledge.
- Capabilities are modeled independently of the menu structure.
- Business and Technical users can share one implementation.
- User interface text can be tested for completeness.
- New roles can be introduced without duplicating application services.
- Help text and documentation may eventually be derived from the same model.
- The design remains consistent with the project's knowledge-centric principles.
### Negative Consequences
- The application must load and query presentation knowledge.
- A small user-interface vocabulary must be designed and maintained.
- Developers must distinguish capability identifiers from visible labels.
- Fallback behavior is required if presentation knowledge is unavailable.
- Some temporary duplication may exist during incremental migration.
## Risks

An overly ambitious model could attempt to encode the entire user interface in RDF.

That would increase complexity and could delay delivery.

This risk is controlled by initially modeling only stable knowledge:

- roles
- capabilities
- labels
- descriptions
- availability
- ordering
- implementation bindings

Layout and interactive behavior remain in conventional application code.

## Alternatives Considered
### Hard-Code All Role-Specific Text

This is simple initially but distributes presentation knowledge throughout the codebase and 
weakens the knowledge-centric architecture.

Rejected as the long-term design.

Permitted temporarily to support incremental delivery.

### Maintain Role Text in JSON or YAML

This would centralize presentation text and may be easier to implement than RDF.

However, it would not naturally connect roles, capabilities, implementation identifiers, help 
resources, and other project knowledge.

Rejected as the authoritative long-term model, though serialized configuration may be used as a 
generated or cached projection.

### Generate the Entire User Interface from RDF

This would maximize graph-driven behavior but would introduce unnecessary complexity, 
especially for layout and browser interaction.

Rejected.

The graph describes capabilities and their presentation. Conventional code renders and operates 
the interface.

## Related ADRs
- ADR-004: Meaning-First Ontology Development
- ADR-005: Single Logical Ontology
- ADR-006: Ontology Test-Driven Development
- ADR-008: Canonical Internal Representation
- ADR-009: UAD Sample Artifact Policy
- ADR-010: Role-Based User Experience

The key sentence for this week is:

> **No graph infrastructure work SHALL delay the initial sample-repair delivery unless that work is directly required by the repair feature.**

So the architecture points toward graph-derived language, while the current work stays focused 
on getting **Check File → Repair Common File Problems → Check Repaired File** working end to end.

