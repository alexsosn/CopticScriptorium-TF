# Issue #10 — remove historical full-source audits from normal implementation CI

## Research

Issue #10 was reopened because PR #28's product-relevant full conversion/reload gate waited behind redundant historical full-source parser/CoNLL-U and graph jobs. PR #30 demonstrates that ordinary implementation changes still trigger the same three historical workflows:

- `.github/workflows/issue13-parser.yml`: `parser-census` executes unit tests *and* clones full pinned upstream TT/CoNLL-U, then runs both complete censuses on every PR and push.
- `.github/workflows/issue14-graph.yml`: focused `graph-unit` is separate, but `graph-census` unconditionally follows it, checks out full TT, and builds/validates graph twice on every PR and push.
- `.github/workflows/issue3-research.yml`: one `graph-shape-audit` job bundles fast tests and a historical full TT census, also firing on every PR/push.

The generic `research-tests` workflow already provides exact-head unit and integration tests, while `issue16-full-converter` and `issue26-memory` use explicit branches/dispatch for their product-relevant full-source gates. This issue must not alter their source semantics or test/pinned revision contracts.

## Plan

1. Preserve PR and main push triggers for **focused issue 3, 13, 14 tests**, with exact-head checkout and SHA verification; add `workflow_dispatch` to the three historical workflows.
2. Split #3 and #13 mixed jobs into focused test jobs plus distinct full-source census jobs. Restrict all three census jobs via `if: github.event_name == 'workflow_dispatch'`, with `needs` on the focused tests to preserve fail-fast prerequisites. #14 already has a dedicated graph unit job, so it needs only manual trigger and census condition.
3. Retain pinned upstream refs, source SHA verification, historical report generation and artifacts under manual dispatch. No new cache or provenance/certification machinery. Do not weaken the independent issue16/26 converter/resource gates.
4. RED tests parse all three workflow YAML files and assert PR/push/dispatch entrypoints; per-job triggers, exact-head verification for focused jobs, source checkout and pin verification in manual jobs, and preservation of issue16 converter dispatch. Then minimal workflow edits, complete exact-head tests, and adversarial independent review.

## Acceptance

A normal implementation PR automatically runs its quick focused tests but does not checkout complete historical source for issue #3/#13/#14 or perform double graph construction. A user can manually dispatch each historical census on a chosen ref. The existing independent product conversion/resource CI remains unchanged. These CI gates check converter implementation only and do not certify upstream Coptic Scriptorium data.
