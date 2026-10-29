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
- source_spec: `_bmad-output/implementation-artifacts/epic-3-retro-2026-10-29.md`
  summary: Log `LINK_REVOKED` for each beneficiary link that ends because its issuing executor code was deactivated (executor rename, reactivation, "Revoke access", executor removal).
  evidence: F3. Links are usable only while their `issued_by_token` is (`get_beneficiary_session_link` in `api/selectors.py`), so those links stop working with no audit row; the owner's security panel shows only `TOKEN_REVOKED`. The retro fixes changed only the owner-facing copy.
- source_spec: `_bmad-output/implementation-artifacts/epic-3-retro-2026-10-29.md`
  summary: Warn on the claim confirm page when the browser holds executor session keys or a logged-in owner, since confirming spends the link and replaces nothing they need.
  evidence: F7. An executor or owner who opens the URL to check it before sending it can claim it by pressing the button, and the beneficiary then gets the 404. Recoverable by reissue.
- source_spec: `_bmad-output/implementation-artifacts/epic-3-retro-2026-10-29.md`
  summary: Give code events and link events separate limits in the owner's security panel, and fix the `get_executor_access_status` docstring that still says "TOKEN_*/CODE_*".
  evidence: F16. `ESTATE_SECURITY_EVENTS` now includes `LINK_*`, and each reissue logs two rows, so link churn can push `CODE_REJECTED` rows out of the 10-row panel. A `LINK_REJECTED` event (Q3) adds to it.
- source_spec: `_bmad-output/implementation-artifacts/epic-3-retro-2026-10-29.md`
  summary: Log `LINK_REVOKED` when deleting a beneficiary ends their active link.
  evidence: F17. `BeneficiaryAccessLink.beneficiary` is `CASCADE` (`models.py`), so the link row disappears and no revoke is logged. The earlier `EstateAccessLog` rows survive because they store names, not FKs.
- source_spec: `_bmad-output/implementation-artifacts/spec-epic-3-retro-item-11-estate-shared-helpers.md`
  summary: Make the owner dashboard's "assigned" count agree with the executor portal when an item's beneficiary has been deleted.
  evidence: `BeneficiaryAssignment.beneficiary` is `SET_NULL`. `get_estate_dashboard_context` counts any assignment row as assigned (`Exists`), so `completeness_pct` includes the orphaned item, while `_designation_fields` marks it `is_unassigned` and the portal's `unassigned_count` includes it. Pre-existing; review pass 1, B5.
- source_spec: `_bmad-output/implementation-artifacts/spec-epic-3-retro-item-11-estate-shared-helpers.md`
  summary: Update CLAUDE.md §2 and §6 for `api/estate_selectors.py` and its one-way import rule (it may import `selectors`; `selectors` never imports it).
  evidence: Both sections still describe a single `api/selectors.py`, so a future session may add estate queries back there. Review pass 1, B16.
- source_spec: `_bmad-output/implementation-artifacts/spec-epic-3-retro-item-11-estate-shared-helpers.md`
  summary: Fix the `get_item_display_custom_fields` docstring, which names the owner page and executor portal but not the beneficiary item page.
  evidence: Story 3.5 added the beneficiary caller (`get_beneficiary_item_detail_context`). Review pass 1, B1b.
