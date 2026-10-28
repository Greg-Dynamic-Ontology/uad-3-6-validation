# UAD
## Managing constraints

### Running Constraint Builder
```text
".venv\Scripts\python.exe" -B -m uvicorn app.main:app --host 127.0.0.1 --port 4000
```
### Constraint Data

## Run SPARQL queries against local RDF

This development utility loads a local RDF document, executes a SPARQL query
from a `.rq` file, and prints the results. It does not modify either input file.
It runs locally; the UAD API server does not need to be running.

### Requirements

Use the project's virtual environment with its existing `rdflib` dependency
installed. The utility requires no additional dependency.

The runner is:

```text
C:\Users\grego\projects\uad-3-6-validation\utilities\sparql\run_query.py
```

### Where the data and queries live

The constraint-testing knowledge is stored in:

```text
C:\Users\grego\projects\uad-3-6-validation\tests\fixtures\constraint-testing\constraint-test-knowledge.ttl
```

Keep its reusable SPARQL expressions in:

```text
C:\Users\grego\projects\uad-3-6-validation\tests\fixtures\constraint-testing\queries
```

Each `.rq` file contains a SPARQL expression, including its required prefix
declarations. Queries can be reviewed and versioned independently of the runner.

### Example: count constraints

Save this query in:

```text
C:\Users\grego\projects\uad-3-6-validation\tests\fixtures\constraint-testing\queries\count-constraints.rq
```

```sparql
PREFIX tk: <https://dynamicontology.com/uad36/test-knowledge#>

SELECT (COUNT(DISTINCT ?constraint) AS ?constraintCount)
WHERE {
    ?constraint a tk:GovernedSourceConstraint .
}
```

The expression counts distinct resources explicitly typed as
`tk:GovernedSourceConstraint`. A constraint is counted once even if many files
link to it. Constraints with no candidate file links are also counted.

Open Windows Command Prompt and run:

```bat
cd /d "C:\Users\grego\projects\uad-3-6-validation"
"C:\Users\grego\projects\uad-3-6-validation\.venv\Scripts\python.exe" -B "C:\Users\grego\projects\uad-3-6-validation\utilities\sparql\run_query.py" --data "C:\Users\grego\projects\uad-3-6-validation\tests\fixtures\constraint-testing\constraint-test-knowledge.ttl" --query "C:\Users\grego\projects\uad-3-6-validation\tests\fixtures\constraint-testing\queries\count-constraints.rq"
```

For the initial 728-constraint inventory, the expected result is:

```csv
constraintCount
728
```

The first line is the result column heading. The second line is its value.
This counts the source constraints in the inventory; it does not count passing
tests, verified triggers, or file-to-constraint links.

### Run another query

Create another `.rq` file and supply its complete filename to `--query`. Keep
`--data` pointed at the RDF document you want to inspect.

| Option         | Purpose                                                                                                          |
|----------------|------------------------------------------------------------------------------------------------------------------|
| `--data`       | Required path to the local RDF document.                                                                         |
| `--query`      | Required path to the SPARQL query file.                                                                          |
| `--rdf-format` | Optional RDFLib format name, such as `turtle` or `xml`. Otherwise the format is inferred from the data filename. |

Relative paths are resolved from the terminal's current directory. Quoting full
paths avoids ambiguity and handles spaces in filenames.

To display command help:

```bat
"C:\Users\grego\projects\uad-3-6-validation\.venv\Scripts\python.exe" -B "C:\Users\grego\projects\uad-3-6-validation\utilities\sparql\run_query.py" --help
```

### Result formats

| Query type  | Printed result                                         |
|-------------|--------------------------------------------------------|
| `SELECT`    | UTF-8 CSV with column headings and one row per result. |
| `ASK`       | `true` or `false`.                                     |
| `CONSTRUCT` | RDF serialized as Turtle.                              |
| `DESCRIBE`  | RDF serialized as Turtle.                              |

For predictable ordering of multiple result rows, include `ORDER BY` in the
query. No automatic ontology reasoning is enabled; queries operate on the
triples loaded from the supplied file. SPARQL property paths can explicitly
follow relationships when needed.

### Save query results

Windows Command Prompt can redirect the printed output into a file. For example:

```bat
"C:\Users\grego\projects\uad-3-6-validation\.venv\Scripts\python.exe" -B "C:\Users\grego\projects\uad-3-6-validation\utilities\sparql\run_query.py" --data "C:\Users\grego\projects\uad-3-6-validation\tests\fixtures\constraint-testing\constraint-test-knowledge.ttl" --query "C:\Users\grego\projects\uad-3-6-validation\tests\fixtures\constraint-testing\queries\count-constraints.rq" > "C:\Users\grego\projects\uad-3-6-validation\constraint-count.csv"
```

The redirection creates or replaces the result CSV. Keep its filename different
from the RDF and query input filenames. The runner itself does not write files.

### Understand failures

- A missing RDF or query file produces an argument error naming the missing file.
- Invalid RDF, invalid SPARQL, and query-execution failures produce a diagnostic
  on standard error and a nonzero exit code.
- An `ASK` result of `false` is a successful query result, not an execution error.
- A `SELECT` with no matching rows normally prints only its column headings.
- The count example still returns one row when nothing matches, with a value of `0`.

The runner reads UTF-8 query files, including files saved with a UTF-8 byte-order
mark. Its printed output uses UTF-8.

### Interpret the testing knowledge

`tk:hasCandidateDataForConstraint` identifies a file with a primary node matched
at the source constraint's recorded path. It does not establish that the whole
trigger is true, that a non-trigger case has been covered, or that validation
passed. Trigger assessments, expected findings, and actual execution results
must be recorded separately as that testing knowledge is developed.
