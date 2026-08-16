# IT-5 XSD Component Processing Traceability

Feature File: `features/xsd_component_processing.feature`
Acceptance Baseline: `specs/samples/xsd_extraction/it-5-master-list.txt`

| ID       | BDD Rule                                                     | BDD Scenario                                                  | Status      |
|----------|--------------------------------------------------------------|---------------------------------------------------------------|-------------|
| IT-5R1S1 | The complete UAD schema closure is discovered                | Follow imports through the UAD schema closure                 | Covered     |
| IT-5R1S2 |                                                              | Inventory every XSD component occurrence                      | Covered     |
| IT-5R2S1 | Schema declarations and documentation preserve their meaning | Process schema declarations used by UAD                       | Covered     |
| IT-5R2S2 |                                                              | Preserve schema documentation                                 | Covered     |
| IT-5R3S1 | Content models and type derivations preserve their meaning   | Process model groups used by UAD                              | Covered     |
| IT-5R3S2 |                                                              | Process type derivations used by UAD                          | Not Covered |
| IT-5R4S1 | Datatype constraints preserve their meaning                  | Process datatype facets used by UAD                           | Not Covered |
| IT-5R5S1 | Schema packaging and wildcards are handled deliberately      | Process schema imports                                        | Not Covered |
| IT-5R5S2 |                                                              | Apply the documented wildcard policy                          | Not Covered |
| IT-5R6S1 | Developer experience reports component-processing coverage   | Developer sees processing coverage for the UAD schema closure | Not Covered |
| IT-5R6S2 |                                                              | An unrecognized XSD component remains visible                 | Not Covered |
| IT-5R6S3 |                                                              | User experience hides schema implementation details           | Not Covered |
| IT-5R7S1 | Complete processing is reconcilable and deterministic        | Every discovered occurrence has a processing disposition      | Not Covered |
| IT-5R7S2 |                                                              | Combined and individual UAD schemas produce equivalent models | Not Covered |
| IT-5R7S3 |                                                              | Reprocess the same UAD schema closure                         | Not Covered |
