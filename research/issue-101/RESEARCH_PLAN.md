# Issue #101 — stop obsolete Coptic↔LXX CI runs without weakening validation

## Research (2026-10-11)
GitHub workflow inspection of the **exact main** at `c73834082f70e4d1a26c090eeea2baff11c75d0d` found 24 workflow YAML files. Ten have a top-level `concurrency` policy (including `research-tests`, parser/graph/writer, memory, web and research), and **14 do not**:

- `issue17-agora.yml`, `issue43-console-command.yml`;
- `issue69-full-verse-census.yml`, `issue69-pinned-verses.yml`, `issue70-real-lxx.yml`, `issue73-dual-lxx-modules.yml`;
- `issue75-ot-inventory.yml`, `issue78-multiwork-lxx.yml`;
- `issue80-lxx-coverage.yml`, `issue82-full-streamed-lxx.yml`;
- `issue89-dual-native-modules.yml`, `issue95-zechariah.yml`, `issue97-crosswalk.yml`, `issue97-zechariah-sequences.yml`.

In particular `issue80` carries a 65-minute job limit and `issue82` 90 minutes, both acquiring exact Coptic TT and pinned `CenterBLC/LXX` parent. #101 cites three superseded PR #100 heads that each executed these costly acquisitions. Existing `research-tests.yml` already uses `github.event.pull_request.number || github.ref` to isolate PRs; the new gate will additionally limit cancellation to **PR events only**, preserving independent push/manual executions.

## Research → plan → RED → implementation → CI → independent review

1. RED-first static unittest checks *all 14* affected workflows have exactly one **top-level** GitHub concurrency block, with group scoped by the workflow and PR number (or Git ref when not a PR), and `cancel-in-progress` conditioned on `github.event_name == 'pull_request'`. Existing workflow names, triggers, step bodies, immutable source pins, permissions and job timeout contracts remain unchanged.
2. Add the **same three-line block** to each audited workflow directly after its trigger stanza and before its existing permissions block. This is a minimal infrastructure-only change. Use **one atomic Git tree commit for all 14** to avoid 14 intermediate CI heads that exacerbate the very problem being fixed.
3. RED evidence: all 14 fail the new contract on baseline main; the new test must be green on implementation branch. Verify each changed YAML is parsable, not simply string-containing; use GitHub workflow registration and exact-head job scheduling as the authoritative YAML/trigger check.
4. Each workflow remains triggered by its original `pull_request.paths`; no heavy job will be bypassed. GitHub's **same-workflow, same-PR** superseded heads should be canceled. Distinct workflow names remain independent. Push-to-main is not cancelled, and unrelated PR numbers cannot collide.
5. Track CI statuses, actual cancellation statuses if subsequent heads exist, and ideally runner-minute reduction in a later active PR; **do not manufacture a quantitative speedup** from the code change alone. No external corpus text/cache artifacts are added.
6. Skeptical logically independent review of actual diff, exact-head job logs, workflow names/group collision, YAML parsing and preserved data pins before merge. A queued or failed full-corpus gate blocks merge.

## Acceptance
- [ ] RED contract fails on baseline and passes updated workflow files.
- [ ] All 14 previously uncovered PR workflows cancel only superseded runs of their own workflow/PR.
- [ ] All source revisions and every full-pinned real validation unchanged; no additional corpus caching/upload.
- [ ] All exact-head CI applicable jobs green (or explicit approvals for unrelated flaky infrastructure only with evidence), independent review, merge.
- [ ] Operational before/after measurement recorded honestly, without claiming timings we have not observed.
