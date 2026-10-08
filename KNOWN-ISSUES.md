# Known issues and limitations

This is a current-state register, not a debugging diary. It lists what users of the converter should know today: open integration gaps, documented limitations, and upstream source characteristics that the converter preserves rather than repairs. Measurements refer to the pinned upstream snapshot `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5` unless stated otherwise; see `research.md` for the evidence.

Status key:

- ⛔ **blocked** — waits on a cross-repository dependency or an explicit design decision;
- ⚠ **limitation** — known, documented behavior or boundary users must account for;
- ❌ **open defect** — implemented behavior is known to be wrong/lossy;
- ✅ **resolved** — retained only where the resolution matters to current users.

## Open converter defects

No open converter defects are currently known. New ones must be recorded here or in generated reports rather than hidden in test skips or regression allowlists.

## ⛔ Agora registration and Context-Fabric handoff are not finished

The repository ships `agora.materializer.json` and the offline `copticscriptorium_tf.agora` adapter, validated against Agora's v1 materializer schema and exercised in Agora's network-denied Bubblewrap host. CopticScriptorium-TF is not yet a canonically registered Agora materializer: registration and the `install_local_corpus → prepare_corpus → load_corpus` handoff to Context-Fabric/cfabric-mcp wait on Agora PR #198. Tracked in #17; the matching README update is #18 / draft PR #64.

## ⚠ Full-corpus conversion needs about 7 GiB of memory

The reviewed full-source run peaked at 7,157.1 MiB RSS (down from 11,075.7 MiB, #26), took about 7m47s in GitHub Actions including clean reload, and produced 618,769,322 bytes of TF. These figures are tied to that source revision and CI environment, not hardware-independent guarantees. Neither the direct CLI nor the Agora adapter has a corpus-selection option, so a smaller footprint requires converting a smaller source tree.

## ⚠ Only TreeTagger SGML (`*.tt`) input is supported

Input discovery accepts `<corpus>/<dataset>_TT/*.tt` directories and `<corpus>/<dataset>_TT.zip` packages. Other upstream exports (CoNLL-U, PAULA, relANNIS, TEI) are not accepted as converter input. Unsupported layouts fail explicitly rather than being guessed.

## ⚠ CoNLL-U supplementation is not wired into conversion

The #1 source contract names validated CoNLL-U as the supplementary authority for UD FEATS, `Cxn`/`Morphs`-style MISC enrichments, normalized relations, and dependency heads absent from TT (52,773 such heads on the pinned snapshot). `copticscriptorium_tf.conllu.parse_conllu_supplement` implements validated, non-overwriting parsing and is unit-tested, but neither the direct converter nor the Agora adapter calls it, and no generated feature carries its data. Generated TF therefore contains TT annotations only: there are no UD morphological features, and `dependency_head` covers only heads present in TT.

## ⚠ Only the pinned upstream revision is regression-tested

Full-corpus conversion/reload and the graph-shape invariants are verified against the pinned snapshot above. Other upstream revisions may convert, but they are not covered by regression gates. A new source shape, for example an independently positioned textual annotation with no word locus, needs a new research/TDD gate rather than an ad hoc anchor.

## ⚠ Provenance commit IDs are checked for form only

`--upstream-commit` must be a full 40-hex or 64-hex commit ID (or the explicit `unversioned-local` sentinel), but the converter does not contact the repository to prove that the local tree matches that commit.

## ⚠ Duplicate scholarly identities stay separate records

The corpus has 2,628 physical source records but 2,520 scholarly CTS identities; 108 identities occur twice (91 byte-identical, 1 core-identical variant, 15 alternate analyses, 1 textually divergent). Separately, 36 documented biblical book↔aggregate overlaps exist under different CTS identities. The converter preserves every physical record and exposes these relations as `same_scholarly`, `documented_overlap` and `witness` edges. Counting across the whole union corpus therefore counts duplicate copies; filter by `corpus`/`dataset` or the relation edges as the research question requires. No "best parsing" winner exists: all 108 duplicate groups tie on annotation quality.

## ⚠ Upstream metadata anomalies are preserved, not repaired

Sixty-four TT documents repeat metadata attribute names (121 equal-value and 6 conflicting repeats). They are kept as deterministic occurrence-suffixed `meta_*` features instead of being resolved by precedence. Literal anomalous keys and values are kept as published.

## ⚠ Licensing is per record; no aggregate data license is asserted

Upstream records carry 17 literal license strings, including share-alike, non-commercial and academic-use terms, and some URL/label pairs disagree. Three `book.bartholomew` records have no TT license attribute; the conversion summary lists records without a literal license field. The MIT license covers this repository's code only (see `LICENSE_SCOPE.md`). Publishing prebuilt TF data is deferred (#8).

## ⚠ The converter does not certify upstream scholarship

Converter tests and full-corpus gates verify conversion behavior. They do not certify the correctness, completeness, licensing eligibility or editorial quality of Coptic Scriptorium data, and converter errors are not claims about upstream scholarship.

## ✅ Resolved design questions that shape the output

- **Source authority (#1):** TT is the canonical document stream; validated CoNLL-U is designated as a supplement (not yet wired in, see above), and the other formats are measured evidence.
- **Slot and sections (#3):** one source `norm` token is one `word` slot, with no synthetic slots. The only TF section level is the physical document (`source_record_id`). Sentence, chapter, verse and video markers stay ordinary nodes/features.
- **Intersecting layout (#3, #13):** 13,015 page/column/line boundaries fall inside word content. Words are not split; layout nodes keep their literal diplomatic text and token-relative offsets and render through their own text formats.
- **Document-local IDs:** upstream `xml:id`/`head` values remain literal features and are resolved per document into native `dependency_head` / `entity_head` edges, never used as global node IDs.
- **Rendering through `oslots`:** translations and layout nodes use node-specific own-text formats, so they do not render the Coptic slot text they span.
