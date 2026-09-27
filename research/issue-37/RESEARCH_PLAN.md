# Issue #37 research and plan

## Research

The direct converter already has two publication-safety contracts:

- native TF output must use a nonexistent destination;
- issue #35 forbids the operational JSON summary from living at or below that TF destination.

The summary writer itself is still:

```python
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(...)
```

so an existing regular file is truncated, an existing symlink is followed, and an
existing directory fails only after the TF dataset has already been published.

This is inconsistent with the converter's fail-closed fresh-output behavior and can
destroy unrelated user data. It is also avoidably fail-late for directories.

Agora is not affected by this policy decision: its summary path is internal to an
empty, host-owned staging directory and is not supplied as a direct-user CLI path.

## Plan

1. RED: prove direct CLI rejects an existing file, directory, and symlink summary
   path before `convert_source_tree()` can run, preserving existing data/targets.
2. Keep issue #35 containment rejection and the fresh external summary happy path.
3. Add a minimal direct-CLI preflight helper. Treat `exists() or is_symlink()` as
   occupied, matching the destination guard including dangling symlinks.
4. Document that `--summary` must name a fresh path outside the TF destination.
5. Run exact-head CI and perform a logically independent adversarial review before
   readiness/merge.

## Non-goals

No cross-process reservation or general filesystem locking is introduced here.
