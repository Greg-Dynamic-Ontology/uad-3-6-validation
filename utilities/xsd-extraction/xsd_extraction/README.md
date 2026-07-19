# XSD Extraction Utility
The **XSD Extraction Utility** is a command-line development tool used to extract schema-level 
metadata and unique XSD artifacts from one XML Schema file or from every XML Schema file in a 
folder.

It is part of the engineering tooling used to build and maintain the UAD 3.6 validation project. 
It is not part of the production validation service.

## Command-line interface

```commandline
python -m xsd_extraction --input-path <file-or-folder> --output-path <file-or-folder>
```
The utility accepts two parameters:

| Parameter        | Description                                                                                              |
|------------------|----------------------------------------------------------------------------------------------------------|
| `--input-path`   | Path to one XSD file or to a folder containing XSD files.                                                |
| `--output-path`  | Path to the output file for a single input file, or to an output folder when the input path is a folder. |

## Input processing

### File input

When `--input-path` identifies a file, the utility validates and extracts that file.

### Folder input

When `--input-path` identifies a folder, the utility validates and extracts every file in that folder.

Each input file is processed independently. Each input file has a corresponding output file.

## Required file structure

Every input file must satisfy all of the following requirements.

### Line 1: XML declaration

Line 1 must be exactly:

```xml
<?xml version="1.0" encoding="UTF-8"?>
```

Any difference is an error, including:

- missing declaration
- different XML version
- different encoding
- extra characters
- leading whitespace
- trailing whitespace

### Line 2: XSD schema element

Line 2 must begin the schema element using one of these qualified names:

```xml
<xsd:schema
```

or:

```xml
<xs:schema
```

The accepted prefix is determined by the namespace declaration on the schema element:

```xml
xmlns:xsd="http://www.w3.org/2001/XMLSchema"
```

or:

```xml
xmlns:xs="http://www.w3.org/2001/XMLSchema"
```

The prefix used by the schema element and the prefix bound to the XML Schema namespace must agree.

Examples:

```xml
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
```

```xml
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
```

The following conditions are errors:

- line 2 does not begin with `<xsd:schema` or `<xs:schema`
- neither `xmlns:xsd` nor `xmlns:xs` declares the XML Schema namespace
- the schema element prefix and namespace-declaration prefix do not match
- both prefixes are declared in a way that makes the intended schema prefix ambiguous

## Extraction rules

For each valid input file, the utility creates a corresponding output file.

The output contains:

1. Every attribute declared on the opening `schema` element.
2. Every subsequent unique XSD artifact found in the file.

### Schema attributes

Every attribute on the opening schema element is written to the corresponding output file.

This includes, when present, attributes such as:

- namespace declarations
- `targetNamespace`
- `elementFormDefault`
- `attributeFormDefault`
- `version`
- other schema-level attributes

No schema-line attribute is silently discarded.

### Unique XSD artifacts

After processing the schema element, the utility examines the remainder of the file.

Each distinct XSD artifact is written once to the corresponding output file.

Duplicate occurrences of the same artifact within one input file are not written more than once.

Examples of XSD artifacts may include:

- `annotation`
- `appinfo`
- `documentation`
- `import`
- `include`
- `redefine`
- `element`
- `attribute`
- `simpleType`
- `complexType`
- `group`
- `attributeGroup`
- `sequence`
- `choice`
- `all`
- `restriction`
- `extension`
- `enumeration`
- `pattern`
- other XML Schema constructs

Uniqueness is evaluated within each input file. Artifacts from separate input files remain associated with their own corresponding output files.

## Output correspondence

For a single input file, `--output-path` identifies its output file.

For a folder input, `--output-path` identifies the folder in which corresponding output files are created. Each output file must retain an unambiguous relationship to its source XSD file.

The utility must not merge multiple source schemas into one output file unless a future option explicitly requests that behavior.

## Error handling

The utility exits with an error when:

- `--input-path` does not exist
- `--input-path` is neither a file nor a folder
- an input file does not have the required first line
- an input file does not have a valid schema declaration beginning on line 2
- the schema prefix does not agree with its namespace declaration
- an output path cannot be created or written
- an input file cannot be read

For folder input, an error must identify the file that failed validation.

The utility must not silently skip an invalid file.

## Design principles

The utility should:

- behave deterministically
- preserve the relationship between each source file and output file
- report validation failures clearly
- avoid changing source XSD files
- produce repeatable output for identical input
- be independently testable
- preserve enough source information to support later ontology and validation-artifact generation

## Initial scope

The initial version extracts schema metadata and unique XSD artifacts.

It does not:

- validate UAD business rules
- generate SHACL
- generate OWL
- modify schemas
- compare MISMO 3.6 and UAD 3.6 validity
- participate in the production validation pipeline
