# Issue #33 — early rejection of dangling-symlink destinations

## Research

Both public conversion layers encode the same fresh-destination invariant with `Path.exists()`:

- `convert_source_tree()` checks the target before parsing, so ordinary occupied paths already fail cheaply;
- `write_graph()` checks again before creating the parent-local temporary staging directory and publishing it.

A dangling symlink is the gap: `Path.exists()` follows the referent and returns false, while `Path.is_symlink()` still identifies the directory entry. A focused POSIX experiment on the supported Linux path confirms that renaming the completed staging **directory** onto a dangling symlink raises `NotADirectoryError` and leaves the link intact. The current code therefore does not silently overwrite that link on this path, but it detects the condition only at final publication. At full-corpus scale that means parse + graph + TF serialization can run before a predictable destination error is surfaced.

Agora is different by contract: its adapter expects an already-created empty output directory and explicitly rejects symlink output roots. Issue #33 must not change that host-specific contract.

## Plan

1. RED: add a focused regression using a minimal valid TT fixture and a dangling destination symlink.
   - direct converter must raise `FileExistsError` and parser entry must not be called;
   - direct writer must raise `FileExistsError` for a valid graph before any TF output is published;
   - in both cases the symlink and literal link target remain unchanged.
2. GREEN: change the two fresh-destination guards to treat `target.exists() or target.is_symlink()` as occupied. Keep error text/type and all staging logic otherwise unchanged.
3. Run focused tests plus exact-head repository CI.
4. Perform a fresh adversarial review checking normal nonexistent destinations, ordinary occupied paths, broken-link semantics, error type, and Agora non-regression.

## Non-goals

No symlink traversal policy for source inputs, no generalized filesystem sandboxing, no output-cache changes, and no changes to atomic publication semantics.
