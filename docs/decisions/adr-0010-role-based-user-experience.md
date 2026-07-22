# ADR-010: Role-Based User Experience

## Status

Accepted

## Context

The UAD 3.6 Validation project is intended to serve multiple communities that share the same validation engine but have different objectives and technical backgrounds.

Examples include:

- Residential appraisers
- Appraisal reviewers
- Lenders
- Appraisal Management Companies (AMCs)
- Quality assurance personnel
- Vendor support organizations
- Software developers
- Standards engineers

While these users perform different tasks, they all interact with the same underlying UAD appraisal data.

Early prototypes exposed technical implementation details such as XML, XML Schema, RDF, SHACL, ontology projections, and pipeline artifacts. These concepts are valuable to software developers but are unnecessary—and potentially confusing—for many appraisal professionals.

The project therefore requires a user experience that presents information appropriate to the user's role while maintaining a single authoritative validation pipeline.

This decision establishes roles independently of user authentication.

## Decision

The application SHALL support role-based user experiences.

Roles determine:

- terminology presented to the user
- available menus
- available reports
- level of diagnostic detail
- visibility of implementation artifacts

Roles SHALL NOT affect:

- validation logic
- business rules
- measurement algorithms
- ontology projections
- validation outcomes

All users execute the same validation pipeline.

Only the presentation of information differs.

Initially, role selection SHALL be independent of user authentication.

A user may select an operating role without creating an account.

Future authenticated user accounts SHALL be assigned one or more roles.

## Initial Roles

### Business User

The Business User experience is intended for appraisal professionals and others whose primary objective is to produce a valid UAD appraisal package.

The interface SHALL use task-oriented language rather than implementation terminology.

Examples include:

- Open Appraisal
- Check File
- Repair File Problems
- Validate Appraisal
- View Results
- Save Report

Implementation details such as XML Schema, RDF, SHACL, namespaces, ontology projections, and pipeline artifacts SHALL remain hidden unless explicitly requested.

### Technical User

The Technical User experience is intended for software developers, vendor support personnel, standards engineers, and technical consultants.

Additional information SHALL be available, including:

- XML Schema validation details
- normalization reports
- ontology projections
- SHACL validation
- measurement diagnostics
- pipeline artifacts
- implementation logs

Technical terminology SHALL be used where appropriate.

## User Interface Principles

The application SHALL communicate in the language of the user's task rather than the language of its implementation.

For example:

Instead of:

- Validate XML Schema

the Business User interface may present:

- Check File

Instead of:

- XML Normalization

the Business User interface may present:

- Repair Common File Problems

Technical terminology remains available within the Technical User experience.

## Future Authentication

This ADR establishes roles, not accounts.

Future releases may introduce authenticated user accounts.

Accounts SHALL be assigned one or more roles.

The role model defined by this ADR SHALL remain independent of the authentication mechanism.

Possible future account types include:

- Individual Appraiser
- Appraisal Reviewer
- AMC Staff
- Lender Staff
- Vendor Support
- Technical Consultant
- Administrator

These account types inherit one or more user experience roles.

## Rationale

Separating roles from authentication provides several benefits.

It allows development of multiple user experiences before implementing identity management.

It preserves a single authoritative validation engine.

It enables gradual expansion from local desktop use to hosted services.

It allows the application to present simple workflows for appraisal professionals while simultaneously providing comprehensive diagnostics for technical users.

## Consequences

The application architecture shall distinguish between:

- Validation Engine
- User Experience Layer
- Authentication Layer (future)

The Validation Engine remains independent of user interface concerns.

All validation results are identical regardless of user role.

Role selection influences only presentation, terminology, and available features.

## Related ADRs

- ADR-008: Canonical Internal Representation
- ADR-009: UAD Sample Artifact Policy