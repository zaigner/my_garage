# Deferred Work

- source_spec: `_bmad-output/implementation-artifacts/spec-2-3-executor-portfolio-view.md`
  summary: Give executors a way to end their portal session (a "Leave portal" action that clears the `estate_executor_*` keys).
  evidence: Story 2.2 sessions last 30 days (`EXECUTOR_SESSION_DAYS`) and the portfolio page shows the whole estate's values and beneficiaries, but no sign-out path exists; on a shared computer the next user sees it. Needs a POST view, an exception to the portal's safe-methods-only rule, and tests.
- source_spec: `_bmad-output/implementation-artifacts/spec-2-4-executor-item-detail-view.md`
  summary: Format custom fields for readers. Use the schema's `label` and schema order instead of `key.title()`, and render lists, dicts and booleans readably (not Python reprs) on both the owner and the executor item pages.
  evidence: `get_item_display_custom_fields` keeps the owner page's existing behaviour, which shows e.g. "Drink Window Start" for a field labelled "Drink From", and `['a', 'b']` for lists. It's pre-existing, but Story 2.4 now shows it to executors.
- source_spec: `_bmad-output/implementation-artifacts/spec-epic-2-retro-fixes.md`
  summary: Move the deploy workflow's superseded-commit guard into a script under version control with its own test (skip only when the deployed tag strictly descends from the built SHA; deploy for the same SHA, `latest`, an empty image, or an unknown tag).
  evidence: The guard in `.github/workflows/deploy.yml` is inline shell that no test or lint runs. Swapping the `merge-base --is-ancestor` arguments, or mistyping the step id, would either roll production back or skip every deploy while the job stays green, and only a real deploy would show it.
- source_spec: `_bmad-output/implementation-artifacts/spec-3-2-estate-scope-executor-replacement.md`
  summary: Run the executor Update form's confirm-prompt logic in a test (browser or JS harness), and align its name normalisation with `_person_name_key` (casefold vs toLowerCase; Python `split()` vs JS `\s`, e.g. U+FEFF).
  evidence: `TestConfirmPrompt` only asserts the rendered attributes. Flipping `===` or dropping the lower-casing in the inline handler passes every test. The repo has no Playwright or Selenium harness. Server-side revocation (`save_executor`) is covered and is the real safeguard.
- source_spec: `_bmad-output/implementation-artifacts/spec-3-2-estate-scope-executor-replacement.md`
  summary: Decide whether app-wide item counts and totals should exclude soft-deleted collections, as the estate now does: the profile `total_items` (`src/config/views.py:150`), and the home NFP and year-over-year selectors (`api/selectors.py` around `:89`, `:102`, `:159`).
  evidence: Story 3.2 excludes items in soft-deleted collections from every estate total. The profile page now shows `total_items` (all items) next to `estate_items_total` (active collections only), so the two counts can differ. The non-estate behaviour predates this story.

- source_spec: `_bmad-output/implementation-artifacts/spec-epic-3-retro-fixes.md`
  summary: The executor's link-issued page (`portal/link_issued.html:21`) should say the link also stops working when the owner revokes or replaces the executor code, not only on reissue or revoke.
  evidence: F3 fixed only the owner-facing copy. The executor hands the link over and is the one who must explain a dead link (review pass 1, B4).
