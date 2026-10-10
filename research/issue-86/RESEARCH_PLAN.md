# Issue #86 — Researcher guide after complete Coptic↔LXX streaming merge

## Research and evidence (2026-10-10)
- Exact merged streaming implementation: PR #83 / merge commit `1036f1c4cc6d0f710d279c4e042394a43e602dfe`; full genuine GitHub Actions run `38080479109`, job `114296178502`, validated 565 pinned TT blobs, 2,628 source documents, 2,394,354 Coptic word slots, native wefts on both Coptic/LXX parent warps, fresh reload and matching 21,120 unique Greek candidate verse IDs.
- Full word statuses: `reference_candidate=1,072,234`, `unclassified_corpus=1,309,117`, `unresolved=12,951`, `ambiguous=52`. Neither unclassified status nor a matching Greek address asserts text equivalence or Greek lexical matching.
- Combined converter→module→fresh TF reload process peak RSS 7,460,860 KiB, wall 9:48.45 in that CI job. Not the streaming stage alone.
- Main `copticscriptorium_tf/lxx_reference.py` has multi-work exact CTS work aliases for the corpus (curated ~43 Greek books), not just the 3 initial real pilot families. `docs/coptic-lxx-alignment.md` currently incorrectly says the current pilot still knows only three families despite later full coverage. Coptic source and Greek target pins remain `3ac067f1709a0012daf39ea8da2fac79980176a5` / `f32a98eddf7eb239aa73ab863d70381e416d5076`.
- Source hash identity is checked per parent Coptic `document` in streaming. PR #85 improves the legacy API and is independent; this doc PR must not imply its merge until it happens.

## Research → RED TDD → docs → CI → independent review
1. Add failing `tests/test_issue86_lxx_guide_freshness.py` requiring a documented status table and accurate full pinned metrics, source scope caveat, native TF word/verse module semantics and exact Git identities; forbidding obsolete three-family-only assertion.
2. Update **only** `docs/coptic-lxx-alignment.md` with accurate current coverage, operational provenance, caveats and future versification/witness/word-alignment research. Preserve actual code examples and three-document pilot history.
3. Run exact-head `research-tests` and researcher-doc CI, separate logically independent review grounded in code and live CI counts. Do not claim raw corpora/derivatives are redistributed.
4. Merge after code-focused #85 to avoid gratuitous branch contention; if main changes, update branch before final review.

## Not in scope
No algorithmic change, semantic assertions, new sidecar, rewriting literal source references, or known-versification repair (those stay #75/#70).
