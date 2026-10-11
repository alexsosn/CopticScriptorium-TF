# Known issues, limitations, and verified capabilities

This is a **current-state** register, not a pre-implementation research plan.
Code behavior below refers to the pinned upstream Coptic Scriptorium source
`CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`.
The upstream texts, editorial decisions, and source licenses are not certified
by a successful converter test. For reproduced numbers, see [research.md](research.md)
and [README.md](README.md).

## ✅ Implemented and verified

- **Native Text-Fabric converter exists.** The `*.tt` parser, graph and
  writer have passed real full-source conversion and fresh TF reload checks
  (2,628 physical TT records, 2,394,354 Coptic `word` slots). Each TT `norm`
  is one word slot. `document` is the sole universal TF section; sentence,
  morphology, entity, layout, translation, physical/scholarly identity,
  overlaps, and source provenance use native node/edge/scalar features.
  Source-visible layout/reference events inside words do not require falsely
  splitting a `word` slot. No semantic JSON/XML blobs are required.
- **Registered Agora production path works.** Community-verified plugin
  `copticscriptorium-tf` and materializer
  `copticscriptorium-text-fabric` use explicitly approved third-party code
  and a required network-denied conversion sandbox. The registry pinned the
  reviewed Coptic commit in merged Agora PR #213; full pinned sparse remote Git
  acquisition → native Text-Fabric conversion → Context-Fabric import,
  load, search and cleanup was accepted by merged
  [Agora PR #215](https://github.com/alexsosn/Agora/pull/215), workflow
  `38063116201`. Source acquisition selects only relevant TT files and ZIPs.
- **Coptic OT ↔ LXX is a reference-candidate overlay, not a verified translation.**
  Native, edition-pinned bilateral Text-Fabric modules can attach common
  reference-address IDs to Coptic word spans and existing
  `CenterBLC/LXX` Greek verse nodes. Source-local `verse_n`, `vid_n`,
  `verse_vid` remain preserved. Matching numeric addresses cannot establish
  actual Coptic/Greek textual equivalence, Greek word alignment, manuscript
  reconstruction or agreement on versification.

## ⚠ Known limitations and research blockers

- **CoNLL-U supplementation is not wired into conversion** (#66).
  TT is authoritative for the current native TF output. Validated CoNLL-U
  parsing exists, but optional UD FEATS, CoNLL-U-only relations and missing-TT
  heads are not automatically added. Other upstream PAULA/ANNIS/TEI exports
  are not converter inputs.
- **Coptic/LXX verse and word alignment is not scholarly-certified**
  (#70, #75, #92, #95, #97). The reference-index crosswalk excludes
  unclassifiable sources and records missing/contradictory references;
  Greek editions with alternatives require an explicit reviewed mapping.
  Token-internal verse-position evidence remains native and may not justify
  assigning the *entire* Coptic word unqualified to one verse.
  Proposed edition-local Zechariah remaps are *candidates*, not independent
  Greek/Coptic word alignment.
- **Automatic Context-Fabric import is not chained onto every materialization.**
  Agora's end-to-end CI exercised the full composed path, but ordinary users
  still explicitly invoke Context-Fabric `install_local_corpus`,
  `prepare_corpus`, `load_corpus`, etc. The source must be accessible from
  the MCP server host; do not expose server-local path import unauthenticated.
  See the [Agora local-import guide](https://github.com/alexsosn/Agora/blob/main/wiki/guides/context-fabric-local-import.md).
- **Full-corpus memory requirements are substantial.** Reviewed full
  conversion peaked near 7 GiB RSS, while generated TF feature files occupy
  roughly 619 MB. These are observed environment-specific figures, not
  a guaranteed scaling ratio or memory ceiling for other upstream snapshots.
- **Local source provenance cannot be attested from a typed SHA alone.**
  The converter validates an explicitly supplied upstream commit string's
  format but cannot verify arbitrary user-local bytes against a remote Git
  tree. Registered immutable Git acquisition checks the actual checkout and
  records its provenance. Unknown source revisions can introduce new shapes.
- **Duplicates and conflicting upstream metadata are preserved.**
  Repeated physical witnesses/alternative analyses do not collapse to
  preferred editions; source-local IDs must not become global TF IDs.
  Repeated metadata keys and conflicting values survive in distinct native
  `meta_*` features, with no editorial repair or ranking.
- **Upstream licenses are heterogeneous, not one MIT data license.**
  Software in this repository is MIT; that does not authorize redistribution
  of original or converted Coptic Scriptorium corpus data. Some records lack
  a literal license attribute; other sources include share-alike,
  non-commercial and more restrictive notices. Review individual upstream
  source licenses before distributing derivative TF data.

The register should be updated whenever a verified defect or limitation is
found. Do not hide loss/ambiguity in a silent skip, guessed reference,
opaque semantic sidecar, or test allowlist.
