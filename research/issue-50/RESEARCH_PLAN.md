# Issue #50 research and plan

## Research

The direct CLI's `_write_summary()` currently creates the final summary path with
`path.open("x")` and then writes JSON into that already-visible file. This correctly
rejects an existing path, including a race after CLI preflight, but it does not make
publication atomic: a write error or process interruption can leave a truncated final
summary that the freshness contract then refuses to overwrite.

Agora is intentionally different. Its summary lives inside Agora's private staging
root, and Agora owns publication of that whole root. This ticket changes only the
direct CLI summary path.

Issue #48 introduced the exact atomic no-clobber filesystem primitive needed for final
publication. Its implementation is currently private to `writer.py`, although the
primitive works for paths rather than specifically directories. The clean design is
to extract that unchanged primitive into an internal filesystem module and reuse it
from both the TF writer and direct summary publisher.

The summary should be written completely to a same-directory temporary file first.
Same-directory staging guarantees the final atomic rename stays on one filesystem.
Normal exceptions remove the temporary file. A hard process kill may leave only the
internal temp name; it must never expose partial bytes under the requested final path.

## Plan

1. RED interruption regression: require a staged-summary write failure to leave no
   final path and no normal-failure temp residue.
2. RED publication-race regression: inject a competing file, directory, and symlink
   only at final publication; each must survive and force `FileExistsError`.
3. Extract issue #48's no-clobber path primitive into one internal module without
   changing its Linux/macOS/Windows behavior; keep the writer regression contract.
4. Stage direct summary JSON with `NamedTemporaryFile(delete=False)` in the final
   parent, then atomically publish through the shared no-clobber primitive and clean
   the staging path in `finally`.
5. Preserve summary JSON schema/content and all boundary/parent/freshness behavior.
6. Run exact-head research/unit/parser/graph/writer/Agora/console-command gates and
   the pinned real Coptic writer slice.
7. Freeze the head and perform a logically independent adversarial review grounded
   in the race tests, existing summary contracts, shared publication primitive, and
   real-corpus regressions.

## Non-goals

No power-loss durability guarantee, no rollback of an already-published TF dataset,
no Agora transaction change, and no TF schema/feature change.
