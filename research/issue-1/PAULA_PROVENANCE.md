# Issue #1 — PAULA generation provenance and measured contribution

Pinned corpus revision: `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`.

Independent adversarial review of PR #7 identified an evidence gap: TT, CoNLL-U, `meta.json` and relANNIS had corpus-wide audits while PAULA was sample-only. That finding blocked merge until PAULA was measured directly.

## Public publishing pipeline evidence

The Coptic Scriptorium publishing repository provides a direct derivation path for PAULA:

- `publish.py` loads TreeTagger SGML and writes corpus-level `_meta` payload into a `<corpus>.meta` file before Pepper runs;
- `pepper/convert_scriptorium.pepperparams` imports TT with `TreeTaggerImporter`;
- the Pepper graph receives an `OrderRelationAdder` over `{norm, norm_group, orig, orig_group}`;
- that same Salt graph is serialized independently by `PAULAExporter` and `ANNISExporter`.

The Pepper parameter template was introduced at `CopticScriptorium/publish@ebe45f31c14ce770f7302bdd6019c4c3d9d6db72` on 2025-04-15 and had no later file revision before the pinned corpus date. `publish.py` itself had no later relevant revision before the pinned corpus date than `bb33e05ad7a3dfc939ca055b6cc5e7d46f012878` (2022-05-04).

This establishes PAULA document annotation as a derived serialization of the TT-imported Salt graph; corpus metadata is the additional source injected before both PAULA and ANNIS export.

## Observed PAULA source shapes

The corpus audit had to model source shapes rather than infer them from PAULA examples:

- actual Coptic document metadata uses `featList` with `xml:base="anno.xml"`;
- some standard/reference metadata forms also use `<dataset>.anno.xml` or `xml:base="meta"`;
- token-level features such as POS use token/mark bases and are not mistaken for document metadata;
- `annoFeat` is annotation inventory, not document metadata;
- `multiFeatList` metadata is expanded by named feature;
- `bohairic.nt_PAULA.zip` and `bohairic.ot_PAULA.zip` are one-level wrappers containing a single inner `*_PAULA.zip` with the XML payload.

The reader supports only the observed one-level wrapper shape. Ambiguous/multiple/deeper wrappers remain fail-closed.

## Corpus-wide result

At the pinned revision:

- 78/78 PAULA packages are opened and classified;
- 118,511 PAULA XML members are parsed;
- no package remains in the unsupported/error ledger after modelling the observed Bohairic wrappers;
- all 2,628 document records have PAULA document metadata;
- PAULA document metadata exposes exactly the same 80 field names observed in TT metadata;
- there are no document metadata field names unique to PAULA and none unique to TT;
- field occurrence counts are equal for 77/80 document fields;
- `document_cts_urn` is less complete in PAULA (2,579 vs 2,628 TT documents);
- `next` is less complete in PAULA (285 vs 1,828);
- `previous` is less complete in PAULA (267 vs 1,810).

PAULA additionally contains 18 corpus-scope metadata types. Four of those names (`Project`, `projects`, `verion_date`, `version_number`) are not TT document-metadata field names. They remain dataset-level provenance and do not justify importing PAULA as a second document source.

## Authority conclusion

PAULA provides useful reproducibility and corpus-metadata evidence, but the measured document layer adds no unique field vocabulary and is less complete than TT for three fields. Combined with the public Pepper derivation path, the corpus evidence supports the narrow production parser set: TT for source-native documents, validated CoNLL-U for measured enrichment, and reviewed metadata sources at their appropriate scope.

A production PAULA parser should be added only if later graph/schema work identifies a concrete semantic requirement that cannot be preserved from that narrower authority set.
