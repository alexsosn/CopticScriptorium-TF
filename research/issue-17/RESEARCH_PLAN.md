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


## 2026-10-10 follow-up: full Git transfer is not yet usable

The native TT converter and user-local Agora/cfabric-mcp handoff succeeded in merged
Agora #198; however the *automatic* source acquisition checked by that PR
failed fetching `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`
with a 120-second limit and `fatal: early EOF`. The published source repository
is ~2.7 GiB and stores non-TT formats the converter never consumes. As such,
the acquired-source exit criterion is **not** complete, irrespective of issue
state. Agora #205 and merged PR #210 introduce explicit `sparse_patterns`
without changing legacy full Git sources.

Research finding: this converter reads `<corpus>/<dataset>_TT/*.tt` and
`<corpus>/<dataset>_TT.zip`, including the pinned real-source family of
`AP`, `sahidica.nt`, `thomas-gospel`. The **root-anchored**
non-cone sparse patterns `/*/*_TT/**` and `/*/*_TT.zip` select both
supported packaging forms, and omit adjacent PAULA/ANNIS/CoNLL-U/TEI data.

Follow-up gates: RED first for the exact manifest pattern contract; then
update the manifest on a new Coptic commit; run Coptic full CI; separately
wait for reviewed + merged Agora #210; update Agora registry from its old
immutable Coptic pin to the *new* reviewed commit; run pinned automatic
real upstream acquisition plus actual materialization and Context-Fabric
load (2,628 physical records / 2,394,354 TF slots / 130 native TF
feature files are the prior reference observations). Independently review
each PR at its final head. Do **not** mark the acquired-source path or issue
as finished before the full live verification is green. This change is
Coptic-side manifest wiring, not a claim about upstream completeness.


### Complete upstream Git-tree census (independent of converter)

On the pinned `CopticScriptorium/corpora` commit, inspected root + all
79 top-level directory trees through the Git Trees API at `?recursive=1`.
All subtrees were untruncated. 78 directories contain TT packages;
`bible/` is the sole directory without TT blobs. Every tracked path with
`_TT` matches `<corpus>/<dataset>_TT.zip` or
`<corpus>/<dataset>_TT/<member>`: **565 matching Git blobs** totaling
**220,289,125 bytes (210.08 MiB)**. All tracked blobs, including root
`README.md` and `meta.json`, total **1,894,430,888 bytes**;
TT material is **11.63%** by uncompressed blob-size bytes.
These figures are *not measured network transfer or worktree size*.
The root `meta.json` is excluded: the present Python converter only
reads TT packages, but future extra source formats may require another
selection strategy.

Acceptance must compare the *actual* sparse checkout inventory against
the 565 pinned Git blob paths **and** run full conversion against the
previous 2,628-document/2,394,354-slot/130-TF-file observations before
closing issue #17. A manifest schema check or successful tiny fixture alone
cannot establish that source completeness.

### 2026-10-10 live host gate resolved, integration still open

Agora PR #210 merged as commit
`39c18b43ead861e614daf8b2bb8f452a551de7c6`. Independent final
review on exact head `0b7f65fb9e144abf32ecac19860afe2169a10b5f`
found no blocker; all four CI workflows passed. Its real GitHub-hosted
pinned-source acquisition matched all **565 TT blobs** by path/size,
220,289,125 bytes, at upstream commit
`3ac067f1709a0012daf39ea8da2fac79980176a5`.
This proves *acquisition*, **not** the registered new Coptic commit,
native TF conversion, or Context-Fabric import.

This PR's real-host CI is pinned to that exact merged Agora commit.
Next gates: finish exact Coptic CI and independent final review,
merge the manifest release, update Agora's canonical immutable plugin
registry pin to the reviewed Coptic commit, then run the full registered
remote acquisition → real TF conversion → Context-Fabric import checks.
Do not close issue #17 on upstream acquisition alone.

### Real-source representative conversion RED→implementation gate

- RED manifest/CI contract `test_live_real_source_workflow_is_bound_to_pinned_thomas_smoke` added before implementation.
- Live workflow `issue17-agora.yml` invokes `tests/live_issue17_thomas.py` after installing Coptic wheel, verifying merged Agora host schema and enabling real Bubblewrap.
- The script clones a single real pinned Git blob:
  `thomas-gospel/thomas.gospel_TT/thomas_gospel.tt` (1,474,064 bytes)
  from immutable commit `3ac067f1709a0012daf39ea8da2fac79980176a5`
  via the same Agora `acquire_git_source` implementation, with an intentionally
  *narrower test-only* sparse selection. It then hands that real checked-out
  source explicitly to the *actual network-denied Agora materialize host*,
  reloads native TF and verifies commit binding, real slots and lemma access.
- The receipt accurately records `source.type=user-local` for this explicit
  second-stage source override; the upstream acquisition step independently
  verifies the immutable Git `resolved_commit`.
- This is **representative real-data** verification, **not** production
  registry-ID automatic acquisition of all TT files, whose 565-blob completeness
  is proven separately on merged Agora #210. Full registered acquired-source
  2,628-record native-TF conversion + Context-Fabric handoff still gates closure.
- Exact-head workflow results and independent adversarial review are pending
  for the Coptic head containing this test.
