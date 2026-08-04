# IT-4 RDF Projection Traceability

Feature File: `features/rdf_projection.feature`

Test Suites:

- `tests/test_rdf_projection.py`
- `tests/test_rdf_projection_loaded_appraisal.py`
- `tests/test_rdf_projection_api.py`
- `tests/test_validation_pipeline_api.py`
- `tests/test_rdf_projection_browser.py`
- `tests/test_rdf_projection_traceability.py`


| ID       | BDD Rule                                       | BDD Scenario                                                       | Supporting Tests                                                                                                                                                                    | Status   |
|----------|------------------------------------------------|--------------------------------------------------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| IT-4R1S1 | RDF projection uses the loaded appraisal       | Project the loaded UAD XML appraisal into RDF                      | `test_rdf_projector_projects_loaded_xml_into_instance_graph`                                                                                                                        | Covered  |
| IT-4R1S2 | RDF projection uses the loaded appraisal       | RDF projection does not require the appraisal to be selected again | `test_rdf_projection_uses_previously_loaded_appraisal`<br>`test_pipeline_runs_selected_stage_from_one_uploaded_appraisal`<br>`test_rdf_projection_does_not_request_appraisal_again` | Covered  |
| IT-4R2S1 | RDF projection produces the RDF instance graph | Preserve the projected RDF instance graph                          | `test_rdf_projector_projects_leaf_element_as_literal_property`                                                                                                                      | Covered  |
|          |                                                |                                                                    | `test_rdf_projector_projects_nested_element_as_linked_resource`                                                                                                                     |          |
|          |                                                |                                                                    | `test_rdf_projector_preserves_nested_leaf_under_nested_resource`                                                                                                                    |          |
|          |                                                |                                                                    | `test_rdf_projector_projects_qualified_attribute_as_literal_property`                                                                                                               |          |
|          |                                                |                                                                    | `test_rdf_projector_assigns_unique_resources_to_repeated_sibling_elements`                                                                                                          |          |
|          |                                                |                                                                    | `test_rdf_projector_preserves_attribute_on_leaf_element`                                                                                                                            |          |
| IT-4R2S2 | RDF projection produces the RDF instance graph | Preserve traceability to the source XML appraisal                  | `test_validation_run_records_rdf_projection_source_traceability`                                                                                                                    | Covered  |
| IT-4R3S1 | User experience controls technical visibility  | User experience hides RDF implementation details                   | `test_rdf_projection_user_experience.py`                                                                                                                                            | Covered  |
| IT-4R3S2 | User experience controls technical visibility  | Developer experience shows RDF projection status                   | `test_rdf_projection_developer_experience.py`                                                                                                                                       | Covered  |
| IT-4R4S1 | RDF projection failures are reported clearly   | RDF projection cannot create an RDF instance graph                 | `test_rdf_projection_failure_reporting.py`                                                                                                                                          | Covered  |
| IT-4R5S1 | Projection is deterministic                    | Reproject the same loaded appraisal                                | `test_rdf_projector_reprojects_same_xml_as_equivalent_graph`                                                                                                                        | Covered  |
