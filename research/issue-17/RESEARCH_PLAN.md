# Issue #17 — Agora materializer integration: research and plan

## Current state and boundaries

- CopticScriptorium-TF `main` after #29 has a complete native-TF `convert_source_tree(source_root, destination, upstream_repository=..., upstream_commit=...)` and CLI, verified on pinned `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`. The converter requires a **nonexistent destination**, preserves physical source paths/hashes, does no acquisition/network work, and emits an operational summary.
- Parser discovery accepts both `<corpus>/<dataset>_TT/*.tt` and `<corpus>/<dataset>_TT.zip` under a source tree; archive-only and direct-only inputs are valid. Malformed/unsupported layouts fail explicitly.
- Agora's current v1 materializer schema (`registry/schema/materializer-plugin.schema.json`) requires plugin metadata, git/user-local acquisition, directory input with `required_globs`, a Python-module execution with `{source}`, `{output}`, `{source_revision}` only and `network: deny`, and required output paths. Glob entries are conjunctive; one `*/*_TT*` pattern admits either direct or ZIP datasets; the converter remains authoritative for actual TT validation.
- Agora's host (`scripts/agora_materialize.py`) prepares an **already existing, empty output directory** in a private staging workspace. It runs the module in a sandbox with `/input` read-only, a writable private output parent, and no network; verifies required output paths, writes `agora-materialization.json` itself, then publishes atomically. It supplies a 40-hex source revision for acquired Git, possibly an empty revision for a non-Git local tree. Local source identity also has Agora's tree hash; do not label missing Git revision as a real commit.
- Pseudepigrapha-TF is the reference upstream with root `agora.materializer.json`, installable Python package and a separate source/TF materializer contract.
- Agora v1.0 explicitly freezes existing plugin families/catalog and defers generic managed-artifact → Context-Fabric composition (#97/#99/#100/#101). Upstream integration can be implemented and tested now; canonical Agora registration and clean-environment Context-Fabric handoff are **separate gates** and this issue must not be closed on manifest-only evidence.

## Selected narrow implementation

1. Add a distributable Python project pinned to supported `text-fabric==13.1.0` and a root `agora.materializer.json` describing both immutable Git acquisition of upstream corpora and user-local source trees, without auto-approving code execution.
2. Add a thin `copticscriptorium_tf.agora` Python-module adapter. It accepts the pre-created empty `{output}` directory, sends the real converter to its nonexistent `output/tf` child, and publishes an operational `conversion-summary.json` at the output root. Normalize summary `output_path` to the stable **relative** path `tf`, not a temporary sandbox pathname that becomes invalid after Agora publishes the artifact.
3. Use `{source_revision}` as upstream commit when available; for non-Git local input write an explicitly non-commit marker `unversioned-local`. Per-source-record SHA-256 remains in TF, and Agora records local tree SHA-256 separately. Do not pretend a local mutable tree is pinned to a commit; never initiate a network request inside the adapter.
4. Manifest output requires `tf/otype.tf`, `tf/oslots.tf`, `tf/otext.tf`, and `conversion-summary.json`. Agora owns reserved `agora-materialization.json`. Keep output in a TF subdirectory because the designated Agora output root already exists.
5. No extra `materializer` invocation path, source re-parser or schema-guessing is introduced into the converter. No public generated corpus, corpus certification or aggregate relicensing.

## RED → GREEN gates

- RED manifest/packaging contract: schema-shaped manifest with immutable 40-hex Git ref, both acquisition strategies, `network: deny`, supported placeholders, accurate `required_paths`, and an importable module; the module and files are initially missing.
- RED executable fixture: ordinary direct + ZIP source under a synthetic tree, existing empty output, `source_revision` Git SHA → native TF in `tf/`, stable summary path `tf`, clean reload and representative query. Compare resulting TF feature bytes against direct conversion of the exact same fixture and provenance arguments, excluding the Agora-only sidecars.
- RED local unversioned input -> explicit marker; unsupported/empty source and nonempty output -> error with no misleading summary/dataset publication; no network calls in the adapter.
- Make the minimal implementation and run focused plus full tests on exact head. Where available, test through Agora's actual materialization host under sandbox and through its registered install path after a reviewed Agora registration; do not claim these happened from unit tests alone.
- Independent adversarial review must specifically check output preexistence, source-revision identity, direct-vs-ZIP glob semantics, immutable Git ref, the absolute temporary-path leak, failure atomicity, installation, and Agora 1.0 scope.

## Remaining integration dependency

A **separate Agora-side registry PR** must bind an immutable CopticScriptorium-TF commit and explicitly approved materializer installation to this manifest. After Agora 1.0's frozen scope is lifted, test actual acquired and user-local sources via Agora, then prove generated `tf/` loads through supported Context-Fabric/cfabric-mcp local-artifact API (or record its dependency if that API is not available). Do not mark #17 complete until this end-to-end gate succeeds.
