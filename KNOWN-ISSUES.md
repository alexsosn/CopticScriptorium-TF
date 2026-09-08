# Known issues and research blockers

This is a current-state register, not a debugging diary. Before the first generated corpus exists, most entries are research blockers or unverified architectural risks rather than converter defects.

Status key:

- ⛔ **blocked** — requires upstream/corpus research or an explicit design decision;
- ⚠ **unverified risk** — evidence exists that the implementation must cover it, but corpus-wide scope is not measured yet;
- ❌ **open defect** — implemented behavior is known to be wrong/lossy;
- ✅ **resolved/verified** — retain only when useful for current users.

## ⛔ Canonical source representation is not yet established

Upstream publishes CoNLL-U, relANNIS, PAULA XML, TEI XML, TreeTagger SGML (`*.tt`), and aggregated metadata. `*.tt` is documented as generally having the most complete annotations, while corpus-level metadata is associated with PAULA/relANNIS. The field-level authority and disagreement rate have not yet been measured. See #1.

## ⛔ Document identity and overlap semantics are not yet established

The upstream repository intentionally contains identical treebank copies, alternate analyses of overlapping biblical material, and parallel witnesses. These cannot be collapsed under one generic duplicate rule. Stable identity/addressing and user-facing filtering are deferred to #2.

## ⛔ Text-Fabric slot and section models are not yet established

The semantic slot could plausibly be the normalized token/morpheme, orthographic group, or another layer. Biblical `book/chapter/verse` navigation also does not automatically fit documentary, monastic, literary, and papyrological corpora. Choosing these before #1–#3 would bake convenience assumptions into the graph.

## ⚠ Layout boundaries can cross token rendering

A sampled `*.tt` document contains a line boundary inside the rendered character content of one normalized token. A line-oriented parser, or a tree model that assumes all layout spans nest cleanly outside linguistic tokens, can split/drop content or create false token boundaries.

Required protection: adversarial parser fixture and corpus-wide structural conservation audit.

## ⚠ Upstream XML/token IDs are document-local

Dependency references such as `xml:id="u3"` and `head="#u3"` are local identifiers. Treating them as global graph identities would create collisions across documents.

## ⚠ Multi-format metadata/annotation conflicts may exist

The same document is represented in several generated/export formats. Until issue #1 measures parity, precedence rules would risk silently selecting stale or lossy values.

## ⚠ Mixed licensing may restrict generated-data distribution

Most upstream data is described as CC-BY, but corpus-specific exceptions and share-alike/special terms exist and individual files include license metadata. Converter-code licensing does not settle generated-corpus redistribution.

## ⚠ Technical TF anchors can render misleading text

Prior Text-Fabric converters showed that non-slot nodes requiring `oslots` can display the anchored primary text through `T.text()` unless type-specific formats are defined. Any metadata/entity abstraction using technical anchoring must be tested with real Text-Fabric.

## ⚠ Green regression baselines can conceal known loss

If future corpus-wide gates use allowlists for malformed/excluded/lossy source records, those lists must be reported as known defects/limitations. A non-growing allowlist is a regression guarantee, not evidence of losslessness.

## ⚠ Corpus scale has not yet been budgeted

The upstream repository is large and contains multiple representations. Full conversion must not repeatedly parse redundant formats or use quadratic slot×structure validation. Runtime, memory, checkout size, and CI caching strategy remain to be measured.

## No implemented converter defects yet

Production converter behavior has not been implemented. When implementation begins, known failures must be added here or to generated reports rather than hidden in test skips.
