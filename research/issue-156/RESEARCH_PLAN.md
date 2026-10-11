# #156 — source-literal attributes for gap/supplied/abbr

## Research (2026-10-12)
- Main `research/issue-118/tag_matrix.csv` counts from immutable `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`: 1,162 `gap` openings (1,160 inside `norm`, keys `extent, gap, reason, unit`), 1,865 `supplied` (889 inside `norm`, keys `reason, source, supplied`), and 1,620 `abbr` (1,594 inside `norm`, key `type`, not `abbr`). Total **4,647** original events.
- Existing issue #153 (merged PR #155) already preserves 10,817 `gap_reason`, `supplied_reason`, `note`, etc. as native positioned `SblAnnotation` nodes. Those are **distinct original tag names**; do not merge them with `gap`/`supplied`/`abbr`. Current parser requires source tag name as primary attribute; that requirement is incorrect for `<abbr type="...">`. Independent per-kind stacks deliberately permit crossed SGML annotations.
- The native graph/writer currently carries only one `value` field on annotations. It cannot represent three original source attributes on one opening without data loss; a stringified dict would violate native TF modeling.
- Parent constraints: exactly 2,394,354 Coptic word slots, no new words, full-corpus existing 2,628 TT records and *crossing-aware* source positions. A source attribute is philological literal evidence, not an editorial expansion, lacuna reconstruction, or bilingual alignment.
- Existing `_scan_attrs` already HTML-unescapes literals, rejects repeated non-meta attributes and malformed attribute syntax. We will reuse this parser rather than weaker regex extraction.

## Plan, TDD and independent review gates
1. RED-first tests: `<gap extent="2" reason="lost" unit="character">`, `<supplied source="scribe" reason="lacuna">`, `<abbr type="nomina_sacra">` (without a same-name attr), crossed positions, present-empty vs absent, invalid duplicate attribute, orphan and unclosed tag, no slot increase, exact scalar native-TF reload.
2. Extend existing `EDITORIAL_WRAPPER_TYPES` to the three *original* names; extend optional immutable `SblAnnotation.attributes` and `GraphNode.source_attributes` tuples with source-key and decoded value, keeping all existing constructor contracts/fingerprints unchanged when empty. `value` stays an optional presentation convenience, **never** sole representation of the original attributes.
3. Add collision-safe native node scalar TF features `tt_attr_<tag>_<key>` for attested original attributes, discover/serialize dynamically by one feature batch at a time. `@sourceTag`, `@sourceKey` metadata provides exact source key identity. A missing field is absent, a present-empty field is the empty string. No JSON/XML blobs or sidecar.
4. CI: existing Python unit/reload regression, and dedicated pinned real three-sample corpus test (including actual Sahidic OT ZIP abbreviation). Full pinned 4,647-tag census with attr key/value/node/source position parity must be run before final merge. Reuse sparse acquisition strategy, not unrestricted Git fetch.
5. Independent skeptical review against original raw bytes and exact-head CI for missing-attribute/empty-value semantics, extra invalid attributes, wrong node IDs/collisions, non-native blobs, fingerprint drift, memory and crossing.
6. Keep issue open and draft PR until complete real-data gate; unresolved anomalies trigger focused issue, no silent dropping.

## Known separate concerns
- OT/LXX alignments are reference **candidates**, not certified verse equivalences; this ticket leaves the bilateral module unchanged.
- `abbr type` is a source label, **not** a resolved expansion; `gap` may denote uncertainty, not word deletion.
