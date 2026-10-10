# Issue #18 — executable user-facing installation/feature/query documentation

## Research

The implementation prerequisites for the direct-use documentation are now stable on `main`:

- #15 defines the native TF surface. The sole slot type is `word`; non-slot node types are `document`, `sentence`, `orig_group`, `norm_group`, `orig`, `page`, `column`, `line`, `entity`, `translation`, and `arabic_translation`.
- Physical records are sections keyed by `source_record_id`. A separate `scholarly_id` preserves the source scholarly identifier (normally the document CTS URN) where present. `corpus` and `dataset` are document features; physical records are never silently collapsed by scholarly identity.
- Core slot/node features exposed by the writer include `norm`, `lemma`, `pos`, `func`, `source_text`, `source_record_id`, `source_word_ordinal`, `source_id`, `scholarly_id`, `corpus`, `dataset`, `entity_class`, `identity`, `own_text`, provenance/source-path features, and deterministic `meta_*` document metadata features.
- Native edge features include `dependency_head`, `entity_head`, `parent`, `direct_word`, `same_scholarly`, `documented_overlap`, and `witness`, with separate valued evidence features for overlap classification/family and witness literals/target scholarly IDs.
- Text formats are generated from actual data: normalized `text-orig-full`, diplomatic `text-diplomatic-full`, and own-text defaults for translation/layout nodes.
- #16 proved complete pinned-source conversion/reload and representative semantic access. #26 reduced the same pinned run from 11,075.7 MiB to 7,157.1 MiB peak RSS. The reviewed full run produced 2,628 source records, 2,394,354 word slots, 3,854,785 non-slot nodes, 2,505,872 graph edges, and 618,769,322 bytes across 130 TF files; its end-to-end smoke including clean reload took about 7m47s on GitHub Actions. These are measurements of that pinned run/environment, not promises for every machine or later upstream snapshot.
- The repository is now an installable Python project and direct conversion is available through `python -m copticscriptorium_tf.converter`.
- PR #30 added an Agora-v1-compatible manifest and offline adapter, verified against Agora's real schema/host and Bubblewrap sandbox. Cross-repository #17 is still open because Agora 1.0 has not been manually published and automatic materialized-artifact → Context-Fabric/cfabric-mcp composition remains deferred upstream. Documentation must distinguish "adapter works" from "canonically registered and automatically loadable through Context-Fabric".

The current README is stale in two user-visible ways: it still describes #16/#26 as active resource work, and it labels #17 as only later work despite the merged adapter. Its feature overview is accurate but too terse to support the #18 research-query acceptance criteria.

## Plan

1. Add RED-first documentation contract tests before editing README. The test will require:
   - current full-corpus resource measurements and their environment caveat;
   - direct install/convert/load commands using the shipped package/CLI;
   - explicit native feature/text-format names;
   - a representative query example covering normalized/diplomatic text, lemma/POS, dependency traversal, entity traversal, English and Arabic translation nodes;
   - physical `source_record_id` versus `scholarly_id`;
   - relation edges;
   - troubleshooting/fail-closed behavior;
   - an explicit Agora boundary that does not claim registry/Context-Fabric completion while #17 remains open.
2. Add one synthetic executable fixture test that performs the same documented query operations against freshly generated TF. This guards feature/API examples against documentation drift without introducing a documentation framework.
3. Rewrite README into a short user path:
   - install;
   - convert;
   - load;
   - feature model;
   - common queries;
   - measured footprint;
   - Agora status;
   - troubleshooting and scope.
4. Run focused and full exact-head CI.
5. Perform a logically independent adversarial review against the README claims, writer feature definitions, #16/#26 measurements, and #17/Agora boundary before merge.

## Scope boundary

This slice can be merged while #17 is externally blocked. It must not close #18 until the canonical Agora registration/Context-Fabric section can be finalized, and it must not describe the synthetic query fixture as certification of upstream scholarly correctness.


## Final Agora documentation gate

Issue #18 was reopened because its direct-use documentation was merged while the
cross-repository dependency #17 was still incomplete. The existing README and
this plan still preserve that historical boundary as if it were current.

Agora #196 has now merged the supported server-local native-TF import path:
`install_local_corpus` copies a generated native TF directory into
Context-Fabric's managed cache, after which the ordinary
`prepare_corpus`/`load_corpus`/cfabric-mcp query workflow applies. This is an
explicit handoff; it is not automatic converter-to-consumer composition.

Agora #198 is the remaining dependency for canonical Coptic materializer
registration. Its final acceptance now includes a real stdio MCP smoke that
takes the registered Coptic materializer's generated `tf/` output through
`install_local_corpus -> prepare_corpus -> load_corpus -> search`.

The final documentation change must not land until that #198 exact-head gate is
GREEN and merged. At that point README should give the shortest supported Agora
path using the canonical plugin id `copticscriptorium-tf`, materializer id
`copticscriptorium-text-fabric`, and the registered materializer scripts
documented by Agora, followed by the explicit Context-Fabric handoff. It must
remove the stale claims that canonical registration/composition is still
blocked, while retaining the distinction between manual handoff and automatic
orchestration.


## Implementation outcome after Agora #198 merge

As of 2026-10-10, canonical registration is merged in Agora #198 at
`98414646eef24a98a1dd88518a8fbac7ae5e570d`. Final exact-head
Foundation, sandbox E2E, and registered-install tests passed. The registered
Coptic fixture was actually materialized in a network-denied sandbox and
loaded, searched, unloaded and removed through the stdio Context-Fabric MCP
server. The old "not canonically registered" README claim is now false.

The separate no-`--source` bulk automatic acquisition encountered
`git fetch` early EOF / the 120-second hard limit on the approximately
2.7 GiB `CopticScriptorium/corpora` repository; Agora #205 owns the
bounded exact-source acquisition research. CopticScriptorium-TF #17 remains
open for that acceptance. The new README must not imply that automatic
full-corpus acquisition has succeeded.

RED-first documentation contracts on draft PR #64 require accurate
registered IDs, explicit code-execution approval, a local-source command,
server-host `install_local_corpus` and offline prepare/load operations,
and an explicit remaining #205 limitation. The documentation change is
separate from converter semantics; no source data or output model changes.
