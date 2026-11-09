@IT-72
Feature: Monitor validation usage and closing-cycle demand
  As an authorized UAD service operator
  I want traceable usage measurements across all calendar days and monthly closing periods
  So that I can measure adoption and plan for concentrated appraisal-validation demand

  # Supplements IT-25, IT-64, and IT-65 through IT-67 without changing their lifecycle or credit rules.
  # A paid allowance is one IT-66 entitlement, even when linked successor cycles use its remaining validations.
  # Closing-cycle concentration is an operating hypothesis to compare with observed demand.
  # The 0.5 percent market-share goal and assumed market size are planning inputs, not measured usage.

  Background:
    Given account-owned validation uses the existing lifecycle and credit services
    And monitoring facts have stable identities, event times, and source references
    And monitoring configuration is governed under IT-62
    And the reporting time zone and reporting calendar are explicitly configured
    And UTC event instants are retained independently of local reporting dates
    And monitoring distinguishes production, Demo, and test activity
    And operator access to service-wide monitoring is authorized

  @IT-72R1
  Rule: Paid allowances and validation work are measured separately

    @IT-72R1S1
    Scenario: Count one paid allowance separately from its included validations
      Given one production account starts one paid allowance using one credit
      And the initial UAD validation and nine included resubmissions complete
      And some resubmissions use explicitly linked successor cycles
      When the operator inspects usage for the period
      Then the usage identifies one paid allowance started
      And it identifies ten completed UAD validation executions
      And it identifies one initial completion and nine resubmission completions
      And linked cycle identities do not inflate the paid-allowance count
      And the counts remain traceable to the entitlement and attempt identities

    @IT-72R1S2
    Scenario: Distinguish free checks and unsuccessful work from paid completions
      Given the reporting period contains free schema checks, Demo validations, production UAD validations, and service failures
      When usage is summarized
      Then each service and operating mode is reported separately
      And completed validations that find appraisal defects remain completed executions
      And service failures and cancellations are reported separately from completed executions
      And failed work remains visible as resource demand even when a credit is reversed
      And debits, reversals, and net credit consumption are separate financial measures
      And monitoring does not debit, reverse, or refund credits

    @IT-72R1S3
    Scenario: Count repeated event deliveries once
      Given a lifecycle or credit fact has already been included in monitoring
      When that same fact is delivered again or arrives out of order
      Then its stable source identity prevents duplicate counting
      And summaries reflect event time rather than delivery order
      And a late fact updates the affected period with a visible refresh time

  @IT-72R2
  Rule: Usage reporting includes weekends and uses explicit time boundaries

    @IT-72R2S1
    Scenario: Report all seven days of a calendar week
      Given production validations occur on weekdays, Saturday, and Sunday
      When the operator views a complete week's daily usage
      Then the report includes all seven local calendar dates in order
      And days with no activity are shown with zero counts when monitoring coverage is complete
      And weekend activity contributes to weekly and monthly totals
      And no business-day multiplier substitutes for observed activity

    @IT-72R2S2
    Scenario: Assign events to local dates across daylight-saving changes
      Given the reporting time zone is "America/Denver"
      And events span local midnight and a daylight-saving transition
      When daily usage is calculated
      Then each event belongs to exactly one local date using that zone's rules
      And repeated local clock times remain distinguishable by their UTC instants
      And a local day may contain 23, 24, or 25 elapsed hours
      And interval boundaries include the start instant and exclude the end instant

  @IT-72R3
  Rule: The expected pre-closing peak is compared with observed monthly demand

    @IT-72R3S1
    Scenario Outline: Identify the configured week before the last-Friday closing week
      Given the configured expected peak is the Monday-through-Sunday week before the week containing the month's last Friday
      When the calendar is calculated for <month>
      Then the last Friday is <last_friday>
      And the expected peak starts on <peak_start> and ends on <peak_end>
      And the closing anchor is a calendar convention rather than a claim about actual closing volumes

      Examples:
        | month   | last_friday | peak_start | peak_end   |
        | 2026-10 | 2026-10-30  | 2026-10-19 | 2026-10-25 |
        | 2026-05 | 2026-05-29  | 2026-05-18 | 2026-05-24 |
        | 2026-02 | 2026-02-27  | 2026-02-16 | 2026-02-22 |

    @IT-72R3S2
    Scenario: Measure the peak week's share of monthly demand
      Given a complete month contains 1250 paid allowances started and 4000 UAD execution starts
      And its expected peak week contains 500 paid allowances started and 1800 UAD execution starts
      When the monthly closing-cycle summary is calculated
      Then it reports 40 percent of paid-allowance starts in that week
      And it reports 45 percent of UAD execution starts in that week
      And the two measures retain their separate denominators
      And each total can be reconciled with the underlying daily records

    @IT-72R3S3
    Scenario: Show when the observed busiest week differs from the expected peak
      Given a complete month has its largest UAD execution-start count in another calendar week
      When the operator inspects monthly demand
      Then the report identifies the observed busiest Monday-through-Sunday week using events within that month
      And it shows the expected peak week separately
      And it identifies all tied busiest weeks
      And observations do not silently change the configured calendar convention

    @IT-72R3S4
    Scenario: Distinguish incomplete or unavailable observations from zero demand
      Given the current month is incomplete or monitoring has an identified collection gap
      When the operator views monthly totals and peak-week comparisons
      Then the report identifies the covered interval and collection gaps
      And partial totals are labeled as partial
      And unavailable observations are not represented as zero activity
      And a zero denominator produces an unavailable percentage rather than a fabricated percentage

  @IT-72R4
  Rule: Monitoring results are inspectable without exposing customer report content

    @IT-72R4S1
    Scenario: Inspect and export a reproducible usage summary
      Given an authorized operator selects a reporting interval and operating-mode filters
      When the operator views or exports usage
      Then the result includes daily counts, monthly totals, and closing-cycle comparisons for those selections
      And it identifies its reporting time zone, metric definitions, configuration version, and refresh time
      And trace references permit authorized reconciliation with lifecycle facts
      And the summary does not expose XML contents, property addresses, email addresses, passwords, or usable resubmission codes
      And an unauthorized customer cannot retrieve service-wide usage
