# ChatGPT Sources

This directory is the bounded collaboration workspace between the
UAD 3.6 Validation project and ChatGPT.

It is intentionally located inside the PyCharm/Git project while remaining
separate from the authoritative project artifacts.

## Purpose

The `chatgpt-sources` directory provides a controlled place where:

- project context can be made available to ChatGPT;
- selected project files can be supplied as inputs;
- files produced or modified with ChatGPT assistance can be returned;
- those files can be reviewed in PyCharm before being promoted into the
  authoritative project structure.

Access to this directory does not imply access to the rest of the
`uad-3-6-validation` repository.

## Directory Structure
[GSE_UAD_3.6.0_v1.3](sources/schemas/UAD/GSE_UAD_3.6.0_v1.3)
    chatgpt-sources/
        README.md
        context/
        input/
        work/

### context/

Contains durable information ChatGPT should use when working on this project.

Examples include:

- project conventions;
- architecture summaries;
- OTDD working conventions;
- terminology and modeling decisions;
- instructions governing collaboration.

Files in `context/` describe the project but are not substitutes for
authoritative project artifacts.

### input/

Contains copies of authoritative project artifacts deliberately supplied to
ChatGPT for a particular task.

Examples include:

- feature files;
- Python source files;
- pytest tests;
- XML examples;
- constraint data;
- ontology fragments;
- documentation under review.

Files in `input` are working copies. The authoritative versions remain in
their normal project locations.

### work/

Contains files created or modified with ChatGPT assistance.

Files in `work/` are proposals until reviewed and accepted.

The normal workflow is:

1. ChatGPT places a complete proposed file in `work/`.
2. The file is reviewed in PyCharm.
3. The user promotes the accepted file to its authoritative project location.
4. Tests are run against the authoritative project.
5. Normal OTDD and Git practices continue from there.

## Authority

The authoritative UAD 3.6 Validation artifacts remain outside
`chatgpt-sources`.

For example:

    app/          production code
    features/     behavioral specifications
    tests/        executable pytest tests
    ontologies/   governed ontology artifacts
    docs/         project documentation
    site/         published site artifacts

Nothing becomes an authoritative project artifact merely because it exists
under `chatgpt-sources`.

## Git

The directory structure and durable context may be committed to Git.

Transient files placed in `input` and `work/` should normally not be
committed. Empty directories may be preserved with `.gitkeep` files.

Suggested `.gitignore` entries:

    chatgpt-sources/input/*
    chatgpt-sources/work/*
    !chatgpt-sources/input/.gitkeep
    !chatgpt-sources/work/.gitkeep

## Principle

`chatgpt-sources` is a controlled collaboration boundary.

The project determines what evidence ChatGPT receives.
ChatGPT prepares work within that boundary.
The user decides what becomes part of the authoritative project.

Derivation, not divination.