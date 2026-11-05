@IT-69
Feature: Monitor validation capacity and service performance
  As an authorized UAD service operator
  I want measured execution load, waiting time, failures, and capacity alerts
  So that the service remains responsive during weekends and concentrated closing-cycle demand

  # Uses IT-68 usage classifications and calendar definitions.
  # Monitoring observes existing authorization, scheduling, lifecycle, and billing behavior.
  # Alert thresholds are configured operating decisions; this feature invents no production service-level promise.

  Background:
    Given validation requests and worker executions have stable trace identities
    And durable monitoring records link accepted requests, attempts, and worker execution intervals
    And production, Demo, test, schema-only, initial, and resubmission work are distinguishable
    And monitoring configuration is governed under IT-62
    And reporting time zone, sampling intervals, retention, and alert policies are explicitly configured
    And operator access to service-wide monitoring is authorized

  @IT-69R1
  Rule: Concurrent load reflects actual overlapping execution

    @IT-69R1S1
    Scenario: Measure concurrent executions across service workers
      Given execution A runs from "2026-10-20T16:00:00Z" until "2026-10-20T16:00:10Z"
      And execution B runs from "2026-10-20T16:00:05Z" until "2026-10-20T16:00:15Z"
      And execution C runs from "2026-10-20T16:00:10Z" until "2026-10-20T16:00:20Z"
      When concurrency is calculated across their workers
      Then the maximum active execution count is two
      And an execution is active from its start instant inclusive until its end instant exclusive
      And queued requests are not counted as active executions
      And the result identifies the measurement interval and participating workers

    @IT-69R1S2
    Scenario: Preserve evidence of a worker lost during execution
      Given a worker stops reporting while its execution has no terminal lifecycle fact
      When the configured worker-liveness interval expires
      Then monitoring identifies the worker and execution as stale or of unknown status
      And it does not invent a successful completion or an execution end time
      And confirmed active work and unresolved execution status are shown separately
      And lifecycle recovery determines any later terminal status

  @IT-69R2
  Rule: Waiting time and execution time remain separately observable

    @IT-69R2S1
    Scenario: Separate queue delay from processing and result delivery
      Given a request is accepted at "2026-10-20T16:00:00Z"
      And its execution starts at "2026-10-20T16:00:03Z"
      And execution finishes at "2026-10-20T16:00:08Z"
      And its result becomes retrievable at "2026-10-20T16:00:09Z"
      When its performance measurements are inspected
      Then queue delay is three seconds
      And execution duration is five seconds
      And acceptance-to-result availability is nine seconds
      And durations use a clock source suitable for elapsed-time measurement
      And invalid or missing timing evidence is reported rather than converted to zero duration

    @IT-69R2S2
    Scenario: Summarize throughput and latency with their populations
      Given a selected interval contains completed work, failed work, and requests still waiting
      When the operator inspects performance
      Then the view shows accepted-request count, execution starts, completions, and service-failure counts
      And it shows current queue depth and oldest waiting-request age
      And it reports median, 95th-percentile, and maximum latency with sample counts and a declared calculation method
      And completed-work latency is distinguished from ongoing request age
      And separate service classes remain selectable
      And appraisal constraint violations are distinguished from service execution failures

  @IT-69R3
  Rule: Capacity observations use closing-cycle demand and actual retry load

    @IT-69R3S1
    Scenario: Compare expected peak periods with observed service load
      Given IT-68 identifies expected pre-closing weeks and observed usage
      When the operator inspects capacity over several months
      Then each period shows peak concurrency, peak queue depth, latency, failures, and execution volume
      And initial executions and included resubmissions are separately visible
      And weekend measurements are included
      And the view identifies both the expected peak week and the observed busiest periods
      And a monthly average does not replace measured short-interval peaks

    @IT-69R3S2
    Scenario: Keep capacity forecasts separate from observed measurements
      Given a planning case assumes 15000 paid allowances per year
      And each allowance permits at most ten completed validations under IT-66
      When the operator views that planning case
      Then 150000 completed validations is labeled as the included-allowance upper-bound scenario
      And actual usage is displayed separately
      And service failures and recovery work may add execution demand beyond that completion count
      And assumed peak concentration and requests per second remain explicit planning inputs
      And a 0.5 percent market-share target is not reported as achieved market share without an independently sourced denominator

  @IT-69R4
  Rule: Capacity alerts identify sustained conditions and recovery

    @IT-69R4S1
    Scenario: Alert on a configured sustained capacity condition
      Given an alert policy defines a metric, threshold, evaluation window, minimum coverage, and notification destination
      And observed queue depth exceeds that threshold for the required window
      When the policy is evaluated
      Then one active alert identifies the condition, observed value, threshold, interval, and configuration version
      And the configured operator destination is notified
      And repeated evaluations update that alert without issuing duplicate opening notifications
      And evaluation and notification remain available on weekends

    @IT-69R4S2
    Scenario: Record recovery and retry failed alert delivery
      Given a capacity alert is active
      When its configured recovery condition is satisfied
      Then the alert records its recovery time and supporting measurements
      And the configured destination receives the recovery notification according to policy
      And a failed notification remains visible and retryable
      And retrying delivery does not create a second alert or alter validation execution

    @IT-69R4S3
    Scenario: Identify missing monitoring coverage
      Given required monitoring observations stop arriving
      When the configured coverage policy detects the gap
      Then monitoring identifies its affected interval and service scope
      And it exposes a monitoring-health condition
      And missing observations cannot prove normal load or resolve an active capacity alert

  @IT-69R5
  Rule: Monitoring survives restarts without changing validation or financial outcomes

    @IT-69R5S1
    Scenario: Reopen retained performance history after a restart
      Given execution measurements and alert history have been durably recorded
      When the application restarts and an authorized operator reopens the retained interval
      Then the measurements and alert identities remain available under the retention policy
      And repeated source events do not duplicate the measurements
      And deleted or expired observations are identified as unavailable
      And monitoring does not rerun validations or modify cycles, findings, entitlements, or credit balances
