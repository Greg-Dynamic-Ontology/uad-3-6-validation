# IT-64: connect account cycles to production validation

Account-owned submissions authorize the verified WorkOS identity and active local validator membership before parsing client identity claims or changing lifecycle storage. The query account and submitted account must match. Anonymous Demo and configured Developer entry retain their existing behavior.

The HTTP adapter connects the existing IT-25 lifecycle functions and IT-44 permission checks to SQLite-backed cycle, submission, attempt, result, event, idempotency, and credit repositories. Accepted UTF-8 report bytes and SHA-256 digests are retained. One available account credit is consumed at execution start; execution failures and incomplete outcomes restore that credit. Development credits are explicitly labeled synthetic and never represent a payment.

The real production ValidationService performs the governed XSD assessment and selected workbook checks. Completed outcome coverage must match the schema and source digests and exact evaluated-rule IDs. Schema issues and business findings both prevent lifecycle passing; incomplete execution cannot produce an actionable result. A first result with issues opens the cycle; a first result without issues passes and closes it. A billable-service lifecycle fact is persisted with the result. This change does not implement payment checkout, property-linked correction allowances, or emailed resubmission codes.

Acceptance and execution-start records commit before synchronous engine execution; the final result and state transition commit together. Idempotent retries return the same cycle without another credit debit. Run retrieval for these cycles uses durable account-owned storage and rechecks authorization. Existing non-cycle run retrieval delegates to its existing handler. A process crash during execution can leave a pending record requiring recovery; automated crash recovery is outside this repair.

IT-64 browser tests use real hosted authentication. The first sign-in scenario still traverses AuthKit and the application callback. Later signed-in scenarios may reuse only that genuine session, in memory for the pytest process, and independently recheck the authenticated user and account membership over HTTP. No credentials or session state are written into fixture JSON. Headless invocations fail promptly with the required launcher command rather than waiting for invisible user input.

The sign-in no-cycle assertion compares a read-only SQLite inventory snapshot taken before authentication against the authenticated API inventory afterward. This preserves the side-effect assertion across repeat test runs that already contain legitimate cycles.

The controlled passing XML is a separate SF1 test copy with documented uniform date shifts. The original published XML is unchanged; the real engine must verify zero findings and complete passing coverage before a new fixture manifest is written. It is date-sensitive and must be reverified when it ages.
