# CopticScriptorium-TF

Text-Fabric converter for the public [Coptic Scriptorium corpora](https://github.com/CopticScriptorium/corpora).

## Status

Research and schema design are in progress. Production conversion has deliberately not started yet: the upstream repository exposes several overlapping representations and duplicate/parallel corpus records, so the canonical source contract, identity policy, and TF graph model are being established first.

Initial work is tracked in GitHub issues. The repository follows an issue-driven research → plan → RED-first TDD → exact-head verification → logically independent adversarial review workflow.

## Current research priorities

1. Inventory the upstream representations (`*.tt`, CoNLL-U, TEI, PAULA, relANNIS, `meta.json`) and assign semantic authority per field.
2. Define stable document identity, overlap/redundancy semantics, and release-stable addressing.
3. Design a loss-aware TF graph for original/normalized segmentation, UD syntax, entities, layout boundaries, translations, and metadata.
4. Only then create implementation tickets with executable acceptance criteria.

See `research.md`, `plan.md`, `KNOWN-ISSUES.md`, and `AGENTS.md`.

## Upstream facts already established

Coptic Scriptorium publishes each document in multiple formats. Upstream documentation states that TreeTagger SGML (`*.tt`) generally contains the most complete document annotations, while corpus-level metadata is available in PAULA XML and relANNIS; aggregated document metadata is also available in `meta.json`.

The upstream repository explicitly documents duplicate and overlapping data: the `coptic-treebank` collection repeats gold treebanked documents from source corpora, some individual biblical-book corpora overlap larger automatically annotated OT/NT corpora, and parallel witnesses may be marked `redundant="yes"`. The converter will preserve and classify these relationships rather than silently deduplicating them.

Licensing is document/corpus-sensitive and must be carried through provenance; generated-data redistribution is not assumed until the license inventory is complete.

## License

Software authored for this repository — including converter code, utility scripts, tests, and supporting software documentation — is licensed under the [MIT License](LICENSE). See [LICENSE_SCOPE.md](LICENSE_SCOPE.md) for the explicit code/data boundary.

The MIT license does **not** apply to Coptic Scriptorium corpora, source texts, translations, annotations, metadata, or imported/generated data artifacts. Those retain the licenses and terms of their original corpora and sources, and corpus/document-level provenance should preserve the applicable upstream licensing information.
