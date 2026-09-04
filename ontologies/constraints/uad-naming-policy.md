# UAD 3.6 Naming Policy

## Principle

> A governed identity should be derived from the identity supplied by its
> governing source whenever one exists.
> Generated identity is the fallback, not the default.

## UAD Constraint Identity Classes

| Thing                   | Governing identity                    | Candidate IRI                                                                   |
| ----------------------- | ------------------------------------- | ------------------------------------------------------------------------------- |
| Source document         | Publisher + document identity/version | `https://dynamicontology.com/uad36/source/umdp/fannie-mae/appendix-h-1/...`     |
| Source constraint       | Source's constraint ID                | `https://dynamicontology.com/uad36/source/umdp/fannie-mae/constraint/0100.0007` |
| Governed rule           | Source's rule ID                      | `https://dynamicontology.com/uad36/source/umdp/fannie-mae/rule/UAD1001`         |
| Normalized constraint   | Derived from governed source identity | `https://dynamicontology.com/uad36/constraint/0100.0007`                        |
| Normalization activity  | Project-created                       | `https://dynamicontology.com/uad36/activity/normalize/0100.0007`                |
| SHACL shape             | Project-created implementation        | TBD pending rule/constraint cardinality                                         |
| Logical Schema resource | Source QName                          | already governed by IT-31                                                       |
