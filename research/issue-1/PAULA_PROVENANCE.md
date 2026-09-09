# Issue #1 — PAULA generation provenance

Pinned corpus revision: `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`.

Independent adversarial review of PR #7 identified an evidence gap: the corpus-wide audits covered TT, CoNLL-U, `meta.json` and relANNIS, while PAULA was represented only by samples/packaging inventory. Issue #1 and its research plan require PAULA's semantic contribution to be accounted for before the source-authority contract can be finalized.

## Public publishing pipeline evidence

The Coptic Scriptorium publishing repository provides a direct derivation path for PAULA:

- `publish.py` downloads/loads TreeTagger SGML and TEI source exports and writes the corpus-level `_meta` payload into a `<corpus>.meta` file before running Pepper;
- `pepper/convert_scriptorium.pepperparams` imports the TT input with `TreeTaggerImporter`;
- the Pepper graph receives an `OrderRelationAdder` over `{norm, norm_group, orig, orig_group}`;
- that same graph is then serialized independently by `PAULAExporter` and `ANNISExporter`.

The Pepper parameter template was introduced at `CopticScriptorium/publish@ebe45f31c14ce770f7302bdd6019c4c3d9d6db72` on 2025-04-15 and had no later file revision before the pinned corpus date. `publish.py` itself had no later revision before the pinned corpus date than `bb33e05ad7a3dfc939ca055b6cc5e7d46f012878` (2022-05-04).

This is strong provenance evidence that PAULA document annotations are a derived serialization of the TT-imported Salt graph rather than an independent annotation authority. The corpus metadata input is the extra source entering that graph before both PAULA and ANNIS export.

## Remaining empirical gate

Generation provenance does not by itself prove that every pinned PAULA artifact is well-formed, complete, or free from historical/export divergence. Before closing issue #1, run a deterministic corpus-wide PAULA audit over the pinned artifacts that:

1. balances every PAULA source package as parsed or explicitly classified;
2. inventories PAULA body/list kinds and annotation `type` values without relying on filenames;
3. surfaces malformed XML, duplicate package identities and unsupported package shapes rather than silently skipping them;
4. records corpus/document metadata feature types present in PAULA;
5. compares the observed layer/metadata inventory with the already measured TT/CoNLL-U/relANNIS authority matrix;
6. treats any PAULA-only semantic type that cannot be explained as a Pepper-derived structural/order serialization as a blocker requiring field-level research.

The audit is research evidence only; it must not introduce PAULA as a production parser unless the measured result demonstrates a semantic field unavailable from the narrower authority set.