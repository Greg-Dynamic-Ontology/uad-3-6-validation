# LQAS manual-test register

Use this file to record completed and blocked **manual Live QA Script executions**. It is an execution register; listing a script does not certify that its scenario passed. No manual execution dates or outcomes have been inferred from chat messages or pytest results.

Keep this register at:

`C:\Users\grego\projects\uad-3-6-validation\tests\live-tests-lqas\LQAS-MANUAL-TEST-REGISTER.md`

## How to record a manual test

1. Choose the scenario's LQAS below and follow its prerequisites and steps.
2. Give the execution a unique ID, for example `LQAS-YYYYMMDD-001`.
3. Add a row to **Execution history**, including local date/time, tester, application commit/build, result, and evidence. Use America/Denver time; include MST or MDT when recording a time.
4. Record the environment and relevant nonsecret account, fixture, and coverage details in **Execution details** using the same execution ID.
5. Update **Latest recorded execution** for that scenario. Retain earlier history, including failed and blocked attempts. A rerun gets a new row and ID.

| Result | Meaning |
| --- | --- |
| GREEN | All required manual steps and expected evidence passed. |
| RED | Executed behavior or evidence failed a scenario requirement. |
| BLOCKED | A prerequisite prevented completing the scenario; record the specific blocker. |
| INCOMPLETE | Execution started but stopped before all required checks were completed. |
| Not recorded | This register has no recorded manual execution for the scenario. |

Record supporting pytest results separately in the notes if useful. A pytest pass by itself is not a completed manual execution. GREEN applies to the recorded application version, environment, fixtures, and evaluated coverage.

## Script manifest

The filenames below match the actual LQAS files currently in the destination folder. Keep these links and the manifest synchronized as scripts are added or renamed.

| Scenario | Manual test | LQAS file |
| --- | --- | --- |
| IT-64R1S1 | Reach the account validation page after successful sign-in | [lqas_it_64_r1_s1_reach_account_validation_after_sign_in.md](C:/Users/grego/projects/uad-3-6-validation/tests/live-tests-lqas/lqas_it_64_r1_s1_reach_account_validation_after_sign_in.md) |
| IT-64R1S2 | Preserve Demo entry behavior for a Demo visitor | [lqas_it_64_r1_s2_preserve_demo_entry_behavior.md](C:/Users/grego/projects/uad-3-6-validation/tests/live-tests-lqas/lqas_it_64_r1_s2_preserve_demo_entry_behavior.md) |
| IT-64R1S3 | Require sign-in before creating an account-owned cycle | [lqas_it_64_r1_s3_require_sign_in_before_account_cycle.md](C:/Users/grego/projects/uad-3-6-validation/tests/live-tests-lqas/lqas_it_64_r1_s3_require_sign_in_before_account_cycle.md) |
| IT-64R1S4 | Reject a cycle request without account authorization | [lqas_it_64_r1_s4_reject_cycle_without_account_authorization.md](C:/Users/grego/projects/uad-3-6-validation/tests/live-tests-lqas/lqas_it_64_r1_s4_reject_cycle_without_account_authorization.md) |
| IT-64R2S1 | Submit a report and inspect its first actionable result through the browser | [lqas_it_64_r2_s1_submit_report_and_inspect_first_actionable_result.md](C:/Users/grego/projects/uad-3-6-validation/tests/live-tests-lqas/lqas_it_64_r2_s1_submit_report_and_inspect_first_actionable_result.md) |
| IT-64R2S2 | Close a new cycle when the first actionable result passes | [lqas_it_64_r2_s2_close_new_cycle_on_first_passing_result.md](C:/Users/grego/projects/uad-3-6-validation/tests/live-tests-lqas/lqas_it_64_r2_s2_close_new_cycle_on_first_passing_result.md) |

## Latest recorded execution

Update a row only after adding its execution-history entry. Use the latest execution outcome even when an earlier run was GREEN.

| Scenario | Latest execution ID | Executed date/time | Tester | Commit/build | Result |
| --- | --- | --- | --- | --- | --- |
| IT-64R1S1 | — | — | — | — | Not recorded |
| IT-64R1S2 | — | — | — | — | Not recorded |
| IT-64R1S3 | — | — | — | — | Not recorded |
| IT-64R1S4 | — | — | — | — | Not recorded |
| IT-64R2S1 | — | — | — | — | Not recorded |
| IT-64R2S2 | — | — | — | — | Not recorded |

## Execution history

Append one row per scenario execution. Copy the blank row as needed. For a manual test session containing several scenarios, give each scenario its own execution ID and outcome.

| Execution ID | Scenario | Local date/time | Tester | Commit/build | Environment / base URL | Result | Evidence / issue reference | Notes / next action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| | | | | | | | | |

## Execution details

Use these details to make the evidence reproducible. Put a dash in a field that does not apply. Use an account ID or test-user email, never a password or token.

| Execution ID | Browser/version | Operating mode | Test user / account ID | Fixture filename and SHA-256 | Schema / constraint-set version or digest | Created cycle / submission / run IDs | Supporting pytest result, if run |
| --- | --- | --- | --- | --- | --- | --- | --- |
| | | | | | | | |

## Evidence notes

For additional detail, copy this entry for each execution that needs it:

### Execution ID: __________

- **Scenario:**
- **Expected result:**
- **Observed result and failed/blocked step, if any:**
- **Screenshot, terminal output, saved result, or issue reference:**
- **Prerequisite resolution or follow-up:**

Keep credentials, API keys, verification codes, usable session cookies, and callback query strings out of this register and its evidence. Submission tests may create durable test cycles and consume development credits; record the created identities instead of treating them as unexplained changes on a later run.
