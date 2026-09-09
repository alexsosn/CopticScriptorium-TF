# Issue #1 — TEI provenance and corpus-wide evidence gate

Pinned corpus revision: `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`.

Independent adversarial review of PR #7 found that TEI, like PAULA, was represented in the source-authority recommendation mainly by hand-inspected samples. Unlike PAULA, TEI cannot be dismissed by the Pepper derivation argument: the public publishing pipeline requests TEI directly from GitDox using the `scriptorium_tei` or `scriptorium_tei_p` stylesheet, while TT is requested separately with `tt_sgml`.

## Measured topology already available

The deterministic pinned source inventory contains:

- 76 datasets with TEI;
- 1,458 visible TEI XML records;
- no TEI representation for `sahidic.ot/sahidic.ot` or `sahidica.nt/sahidica.nt`;
- all TEI representations at this revision are visible directory packages rather than opaque archives;
- 12 visible TEI/TT source identities differ only by filename case;
- the large Bohairic OT/NT TEI sets are visible while their TT source records are archive-packaged, so a semantic comparison must not infer TT absence from the Git tree.

## Sample evidence to test corpus-wide

The paired AP and documentary samples show TEI/EpiDoc carrying:

- `teiHeader` source/manuscript/responsibility/license metadata;
- document CTS title references;
- diplomatic page/column/line and text-part structure;
- word lemma and fine POS;
- morpheme segmentation;
- language and rendition/highlight spans;
- sentence-level English translations.

Those same samples do not expose UD dependency arcs or the entity identity graph in the direct form present in TT/CoNLL-U. Sample inspection is not enough to conclude that no production TEI parser is required.

## Corpus-wide gate

Before issue #1 can be finalized, a deterministic TEI audit must:

1. balance every pinned TEI XML record and preserve source identity;
2. reject or explicitly ledger malformed/non-TEI XML rather than silently skipping it;
3. census TEI element and attribute presence per document, including header metadata, diplomatic/layout elements, words/morphemes, language/rendition and translations;
4. distinguish header and text-body vocabulary so metadata tags are not conflated with linguistic structure;
5. pair TEI and TT source records case-insensitively across both visible and archive-packed TT representations;
6. measure at least token-count/lemma/fine-POS parity where both formats expose the same word layer, and classify unpaired records explicitly;
7. identify any TEI element/attribute family with no already established TT/CoNLL-U/metadata authority and treat it as a research blocker rather than assuming equivalence.

The audit is evidence only. A TEI production parser is justified only if this corpus-wide measurement demonstrates a semantic layer that cannot be preserved from the narrower authority set.