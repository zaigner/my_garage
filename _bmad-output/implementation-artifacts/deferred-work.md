# Deferred Work

- source_spec: `_bmad-output/implementation-artifacts/spec-2-3-executor-portfolio-view.md`
  summary: Give executors a way to end their portal session (a "Leave portal" action that clears the `estate_executor_*` keys).
  evidence: Story 2.2 sessions last 30 days (`EXECUTOR_SESSION_DAYS`) and the portfolio page shows the whole estate's values and beneficiaries, but no sign-out path exists; on a shared computer the next user sees it. Needs a POST view, an exception to the portal's safe-methods-only rule, and tests.
