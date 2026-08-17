Feature: Project published UAD XML appraisals into RDF instance graphs

  The published UAD sample appraisals provide representative instances
  for discovering and correcting gaps in the XML-to-RDF projection.

  Rule: Each published appraisal type can be projected into RDF

    @IT-6R2S1
    Scenario: Project the published single-family appraisal samples
      Given the following published single-family appraisal samples:
        | XML file                                                  |
        | Appendix D-1 SF1_Appraisal/SF1_Appraisal_v1.4.xml         |
        | Appendix D-1 SF2_Appraisal/SF2_Appraisal_v1.4.xml         |
        | Appendix D-1 SF3_Appraisal/SF3_Appraisal_v1.4.xml         |
        | Appendix D-1 SF4_Appraisal/SF4_Appraisal_v1.4.xml         |
        | Appendix D-1 SF5_Appraisal/SF5_Appraisal_v1.2.xml         |
      When each appraisal is projected into RDF
      Then each appraisal produces an RDF instance graph
      And every inventoried XML occurrence has exactly one projection disposition
      And every represented occurrence identifies its RDF term
      And every excluded occurrence identifies its governing decision
      And no XML occurrence silently disappears

    @IT-6R2S2
    Scenario: Project the published condominium appraisal samples
      Given the following published condominium appraisal samples:
        | XML file                                                        |
        | Appendix D-1 Condo1_Appraisal/Condo1_Appraisal_v1.4.xml         |
        | Appendix D-1 Condo2_Appraisal/Condo2_Appraisal_v1.4.xml         |
      When each appraisal is projected into RDF
      Then each appraisal produces an RDF instance graph
      And every inventoried XML occurrence has exactly one projection disposition
      And every represented occurrence identifies its RDF term
      And every excluded occurrence identifies its governing decision
      And no XML occurrence silently disappears

    @IT-6R2S3
    Scenario: Project the published manufactured-home appraisal samples
      Given the following published manufactured-home appraisal samples:
        | XML file                                                  |
        | Appendix D-1 MH1_Appraisal/MH1_Appraisal_v1.4.xml         |
        | Appendix D-1 MH2_Appraisal/MH2_Appraisal_v1.4.xml         |
      When each appraisal is projected into RDF
      Then each appraisal produces an RDF instance graph
      And every inventoried XML occurrence has exactly one projection disposition
      And every represented occurrence identifies its RDF term
      And every excluded occurrence identifies its governing decision
      And no XML occurrence silently disappears

    @IT-6R2S4
    Scenario: Project the published 2-to-4-unit appraisal samples
      Given the following published 2-to-4-unit appraisal samples:
        | XML file                                                                                       |
        | Appendix D-1 2- to 4-unit_Appraisal/2- to 4-unit_Appraisal_v1.4.xml                             |
        | Appendix D-1 2- to 4-unit_Scenario_2_Appraisal/2- to 4-unit_Scenario_2_Appraisal_v1.2.xml       |
      When each appraisal is projected into RDF
      Then each appraisal produces an RDF instance graph
      And every inventoried XML occurrence has exactly one projection disposition
      And every represented occurrence identifies its RDF term
      And every excluded occurrence identifies its governing decision
      And no XML occurrence silently disappears
