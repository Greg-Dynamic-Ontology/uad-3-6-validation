# IT-4 RDF Projection Traceability

Feature File: `features/rdf_projection.feature`

| ID       | BDD Rule                                       | BDD Scenario                                                       | Status   |
|----------|------------------------------------------------|--------------------------------------------------------------------|----------|
| IT-4R1S1 | RDF projection uses the loaded appraisal       | Project the loaded UAD XML appraisal into RDF                      | Covered  |
| IT-4R1S2 | RDF projection uses the loaded appraisal       | RDF projection does not require the appraisal to be selected again | Covered  |
| IT-4R2S1 | RDF projection produces the RDF instance graph | Preserve the projected RDF instance graph                          | Covered  |
|          |                                                |                                                                    |          |
|          |                                                |                                                                    |          |
|          |                                                |                                                                    |          |
|          |                                                |                                                                    |          |
|          |                                                |                                                                    |          |
| IT-4R2S2 | RDF projection produces the RDF instance graph | Preserve traceability to the source XML appraisal                  | Covered  |
| IT-4R3S1 | User experience controls technical visibility  | User experience hides RDF implementation details                   | Covered  |
| IT-4R3S2 | User experience controls technical visibility  | Developer experience shows RDF projection status                   | Covered  |
| IT-4R4S1 | RDF projection failures are reported clearly   | RDF projection cannot create an RDF instance graph                 | Covered  |
| IT-4R5S1 | Projection is deterministic                    | Reproject the same loaded appraisal                                | Covered  |
