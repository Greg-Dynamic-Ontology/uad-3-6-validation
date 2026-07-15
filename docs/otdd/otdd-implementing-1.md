# Implementing OTDD - Lesson 1

## Context

During the development of the UAD 3.6 Validation project, the OTDD
methodology was itself under development. As the first reference
implementation of OTDD, UAD serves both as a production semantic project
and as the environment in which the methodology is evaluated and
refined.

Early implementation revealed that practical experience often exposed
questions not anticipated during the initial design of the methodology.

## Observation

The methodology itself evolved as it was applied.

Rather than indicating weakness in OTDD, this demonstrated that
developing an engineering methodology and constructing its first
reference implementation naturally proceed together.

As implementation continued, lessons were discovered that improved both
the methodology and the reference implementation.

## Analysis

Engineering methodologies are not created in isolation.

They mature through repeated application to real engineering problems.

OTDD is no different.

The purpose of the UAD reference implementation is not merely to produce
a working ontology and validation environment, but also to evaluate and
improve the engineering practices used to create them.

This experience established an important distinction between three
related but independent artifacts:

- **OTDD**, the engineering methodology.
- **UAD**, the reference implementation exercising the methodology.
- **Implementing OTDD**, the engineering notebook documenting lessons
  learned while applying the methodology.

Maintaining this separation allows the methodology to evolve based on
observed engineering experience rather than speculation.

## Resulting Guidance

Treat OTDD as an engineering methodology that evolves through disciplined
application.

Record implementation lessons as they are discovered.

Do not immediately modify the methodology whenever a new idea appears.
Instead:

1. Observe the implementation experience.
2. Record the lesson.
3. Determine whether the lesson is repeatable.
4. Incorporate stable lessons into the OTDD methodology.

This ensures that OTDD evolves through derivation rather than
assumption.

## Impact

### Methodology

Establishes that OTDD should mature through experience gained while
building real semantic systems.

### UAD

Confirms the role of UAD as the reference implementation used to
exercise and evaluate OTDD.

### OTK

Provides future guidance that OTK should support engineering practices
proven useful through reference implementations rather than introducing
process based solely on theoretical design.

### Documentation

Introduces the **Implementing OTDD** document series as an engineering
notebook for capturing methodological lessons prior to their adoption
into the formal OTDD methodology.