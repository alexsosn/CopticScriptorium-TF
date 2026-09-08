# Issue #1 — source exception ledger

Pinned upstream: `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`.

This ledger classifies source shapes discovered by corpus-scale research. Production conversion must balance every input record against converted output or one of these explicit source classifications; none of these cases authorizes a silent skip.

## Valid packaging asymmetry

- TT is directory-packaged for some datasets and ZIP-packaged for others. At the pinned revision the semantic census reads 561 TT documents from visible directories and 2,067 from archives.
- CoNLL-U can likewise be exposed through aggregate packaging. Inventory code records archive presence separately from visible per-record coverage.
- Opaque archive packaging is **not** evidence that a particular source record is missing.

Classification: valid source packaging; parser/transport must support the package or explicitly declare the representation opaque for record-level comparison.

## TT-only visible records

The TT↔CoNLL-U identity audit finds 911 TT source records in `sahidic.ot` with no visible matching CoNLL-U record at the pinned revision. No CoNLL-U-only record identities are observed.

Classification: valid format asymmetry. TT conversion proceeds; CoNLL-U-only enrichments are simply unavailable for those records and must remain absent rather than fabricated.

## Whitespace-only CoNLL-U placeholders

There are 227 paired CoNLL-U paths whose file content is whitespace-only. They occur in the aggregate Sahidica NT source packaging measured by the audit.

Classification: valid placeholder/empty supplementary representation, not token-count drift. TT remains convertible; no CoNLL-U semantic enrichment is merged for the placeholder.

## Structurally invalid basic CoNLL-U dependencies

The basic dependency validator reports 18 errors across nine CoNLL-U source files:

- `book-bartholomew/book.bartholomew_CONLLU/book.bartholomew_part1.conllu` — token ID `0`;
- `book-bartholomew/book.bartholomew_CONLLU/book.bartholomew_part2.conllu` — token ID `0`;
- `helias/helias_CONLLU/helias_martyrdom_part1.conllu` — token ID `0`;
- `helias/helias_CONLLU/helias_martyrdom_part4.conllu` — token ID `0`;
- `life-hilaria/life.hilaria_CONLLU/life.hilaria.bnf132frg2.conllu` — token ID `0`;
- `life-marina/life.marina_CONLLU/life.marina.HC_giron.conllu` — token ID `0` with a dependency reference outside the valid sentence token set;
- `sahidica.nt/sahidica.nt_CONLLU/41_Mark_01.conllu` — dangling and negative HEAD values;
- `sahidica.nt/sahidica.nt_CONLLU/41_Mark_07.conllu` — token ID `0`;
- `sahidica.nt/sahidica.nt_CONLLU/41_Mark_09.conllu` — token ID `0` occurrences.

Classification: malformed/non-standard supplementary source for basic dependency merge. TT remains source-native authority. These CoNLL-U documents are excluded from semantic parity/enrichment merge and emitted in `malformed_conllu_documents`; they are not repaired heuristically.

## Duplicate TT metadata attributes

Sixty-four TT documents contain repeated metadata attribute names. Most repeated occurrences are equal-value repetitions, but six occurrences contain conflicting values (observed for fields including `people` and `places`).

Classification: malformed XML but source-readable SGML-like metadata. The research lexer preserves all literal values and flags conflicts; production metadata policy may not silently choose the last occurrence or discard conflict evidence.

## Global `meta.json` field-shape anomalies

The global metadata index contains literal field names with leading/trailing whitespace, including `" segmentation"` and `"msItem_title "`, alongside canonical-looking names. `meta.json` also normalizes many values that are represented as HTML links in TT.

Classification: valid source evidence with normalization/quality anomalies. Exact keys and literal values remain provenance; normalization must be explicit and tested rather than implemented by unconditional `.strip()`/overwrite.

## Missing TT license metadata

Three TT records have no `license` attribute at the pinned revision.

Classification: unresolved redistribution metadata. Conversion/testing may retain the record with explicit missing-license provenance, but publication is fail-closed until follow-up #8 resolves the source terms.

## Duplicate/alternate scholarly records

Global `meta.json` has 2,390 keys while the TT census contains 2,628 copies. Reconciliation is complete: 2,152 metadata keys map to one TT copy and 238 keys map to two copies. Upstream also documents treebank duplicates, individual biblical-book vs aggregate analyses, and `redundant="yes"` parallel witnesses.

Classification: valid scholarly overlap, not a parser duplicate. No record is automatically discarded by issue #1. Identity/preference/filter semantics belong to #2.

## Release regression rule

The counts and paths above are evidence for the pinned revision, not eternal allowlists. A newer upstream revision must rerun the inventory/semantic/parity suite. New, removed, or changed exceptions require research classification before a release gate can call the source contract satisfied.
