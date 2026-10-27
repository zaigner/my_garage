# Deferred Work

- source_spec: `_bmad-output/implementation-artifacts/spec-2-3-executor-portfolio-view.md`
  summary: Give executors a way to end their portal session (a "Leave portal" action that clears the `estate_executor_*` keys).
  evidence: Story 2.2 sessions last 30 days (`EXECUTOR_SESSION_DAYS`) and the portfolio page shows the whole estate's values and beneficiaries, but no sign-out path exists; on a shared computer the next user sees it. Needs a POST view, an exception to the portal's safe-methods-only rule, and tests.
- source_spec: `_bmad-output/implementation-artifacts/spec-2-4-executor-item-detail-view.md`
  summary: Format custom fields for readers. Use the schema's `label` and schema order instead of `key.title()`, and render lists, dicts and booleans readably (not Python reprs) on both the owner and the executor item pages.
  evidence: `get_item_display_custom_fields` keeps the owner page's existing behaviour, which shows e.g. "Drink Window Start" for a field labelled "Drink From", and `['a', 'b']` for lists. It's pre-existing, but Story 2.4 now shows it to executors.
