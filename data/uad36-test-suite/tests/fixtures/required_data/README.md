# UAD 3.6 required-data negative tests

53 negative XML fixtures, each independently derived from the same unmodified repository baseline. No rows were unsafe to generate.

## Sources
- Repository: https://github.com/Greg-Dynamic-Ontology/uad-3-6-validation
- Commit: 8cae70b4f19f8790d3b8b78d7891ca022d04e660
- Baseline: `examples/xml/SF1_Appraisal_v1.4.xml` (included under `baseline/`).
- Baseline SHA-256: `47509c23bcf28c3abb9c57e00a3f93cf52ed38fec3862d7cda24bffd6bca5be9`
- Rules: the uploaded `data-constraints.xlsx`, Sheet1. Exactly 53 rows match Severity = Fatal and Rule Logic = `If <Primary Data Element> is not provided`. Their source columns are preserved in `selected-workbook-rows.json`.
- Schema: `specs/UAD/GSE_UAD_3.6.0_v1.3/Combined/GSE_UAD_3.6.0_v1.3.xsd` from the same repository commit.

## Manifest and context
`manifest.csv` maps every fixture to its row ID, Primary Data Element, Rule ID and namespace-aware XPath. Bind prefix `m` to `http://www.mismo.org/residential/2009/schemas`. Paths follow the workbook's parent paths. Subject rows are restricted to `PROPERTY[@ValuationUseType='SubjectProperty']`, as identified in the baseline. Every selected path resolves to exactly one populated leaf element before removal. Comparable data is preserved.

## Verification
The original baseline passes the repository GSE UAD 3.6 v1.3 XSD. All 53 baseline required-data presence checks pass. Each test deletes precisely one complete target element by its original byte span. Every byte outside that span remains unchanged, including namespace declarations, whitespace, embedded content and other properties. XML parsing, reinsertion/tree equality and the 53 presence checks were verified independently for every output. Each output fails exactly its targeted check within this 53-rule subset and passes the other 52.

All 53 outputs are well-formed XML; 53 of 53 also pass the XSD after removal. Detailed results and hashes are in `verification.json`.

These are missing-data fixtures with verified target absence. Full production business-rule validation was not run. Passing XSD and these 53 baseline checks does not certify compliance with every UAD business rule. Related rules outside this subset may also report consequences of the intentional omission.
