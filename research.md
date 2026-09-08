# Research: Coptic Scriptorium → Text-Fabric

## Scope

This document records the initial research baseline for converting the public `CopticScriptorium/corpora` repository to Text-Fabric. Findings are preliminary until issue #1 completes a corpus-wide inventory.

## Upstream representations

The upstream README documents multiple representations of the same documents:

- CoNLL-U
- relANNIS
- PAULA XML
- TEI XML
- TreeTagger SGML (`*.tt`)

Upstream states that `*.tt` files generally contain the most complete document annotations. Corpus-level metadata is available in PAULA XML and relANNIS; document metadata is aggregated in `meta.json` and is also commonly present in the first `<meta ...>` line of `*.tt` files.

This means the converter must not begin by choosing the easiest format. Issue #1 will establish a field-by-field authority matrix and measure disagreements between representations.

## Annotation quality metadata

Upstream exposes quality levels for at least:

- segmentation
- tagging
- parsing
- entities
- identities

Values include `automatic`, `checked`, and `gold`. These levels must be preserved as provenance/quality features. They must not be converted into an implicit destructive preference policy.

## Duplicate, overlap, and parallel-witness semantics

The upstream README explicitly identifies several overlap classes:

1. `coptic-treebank` repeats gold treebanked documents that also occur in their source corpora; these copies may be text-identical.
2. Individual biblical-book corpora such as `sahidica.mark`, `sahidica.1corinthians`, and `sahidic.ruth` overlap larger automatically annotated `sahidica.nt`/`sahidic.ot` collections; analyses can differ and the individual corpora are generally more accurate.
3. Parallel witnesses are not necessarily text-identical but can be marked `redundant="yes"` for quantitative workflows that want to avoid double counting.

A single `deduplicate=true` rule would collapse distinct scholarly situations. Issue #2 therefore separates stable scholarly identity, release-scoped source-record identity, alternate annotation, identical duplication, and parallel witness relations.

## Observed `*.tt` structure

A sampled file (`AP/apophthegmata.patrum_TT/AP.111.poemen.167.tt`) contains document metadata followed by nested structural and linguistic markup including:

- page (`pb_xml_id`), column (`cb_n`), verse-like (`verse_n`), and line (`lb_n`) boundaries;
- translations;
- `orig_group` and `norm_group` bound-group structures;
- `orig` surface segments;
- `norm` normalized tokens/morphemes with local `xml:id`, `pos`, `lemma`, dependency `func`, and `head`;
- entity spans with an entity class and a head token.

A line boundary can occur inside the rendered character content belonging to one `norm` token. Therefore a line-oriented parser is unsafe. The parser needs an event/stack representation that allows layout boundaries to intersect token rendering without splitting or dropping the linguistic node.

Dependency IDs such as `u1`/`#u3` are source-local references. They should be resolved within the document and re-expressed as TF edges/features; they are not suitable as global graph IDs.

## Candidate semantic layers to preserve

The schema research should account for at least:

- source record / corpus membership;
- stable document identifiers such as CTS URNs where present;
- original orthography and normalized form;
- orthographic/bound groups and morpheme/token segmentation;
- lemma and fine-grained POS;
- sentence boundaries where available;
- Universal Dependencies heads and relations;
- named/referring-expression entity spans and head tokens;
- identity/Wikification links where available;
- page/column/line/layout information;
- translations;
- manuscript, repository, provenance, bibliographic, and geographic metadata;
- annotation-quality fields;
- redundancy/overlap information;
- license and upstream version metadata.

The final node/edge model remains intentionally unresolved pending issues #1–#3.

## Licensing/distribution

Upstream documentation says most documents are CC-BY 3.0 or 4.0, with explicit corpus-level exceptions including a special Sahidica New Testament license and CC-BY-SA material. Individual files also carry license metadata. The converter code can be independently licensed, but publishing generated TF data must wait for a measured license inventory and a policy for mixed-license releases.

## Lessons from previous TF converter projects

### Pseudepigrapha-TF

The OCP converter established several practices that should be reused:

- pin an immutable upstream revision;
- preserve source-relative path, hash, and upstream provenance;
- keep literal source identifiers while using deterministic technical disambiguation when TF addressing requires uniqueness;
- test real Text-Fabric behavior, not only an internal graph representation;
- make node-specific text formats explicit when technical anchors would otherwise render misleading primary text;
- require an independent raw-source → generated-TF semantic parity report;
- validate corpus-scale section coverage and graph invariants with linear-time/indexed algorithms rather than slot×section scans;
- discover full-corpus exceptions through pinned integration CI, then add a failing synthetic fixture before implementing support.

### TLHdig-TF

TLHdig exposed failure modes that should be prevented earlier here:

- XML well-formedness alone cannot prove structure conservation;
- repairs/normalizations can require philological decisions and must not be hidden as parser cleanup;
- source coverage needs a balancing ledger: input records = converted + explicitly classified exclusions;
- ambiguous human-facing section identifiers require a separate unambiguous source-record identity;
- known-loss/exception allowlists are regression guards, not zero-defect certification;
- release certification should distinguish regression-valid from research-ready states;
- published release directories should be immutable and provenance-bound;
- generated census/structure reports should be the authority for measured counts, not hand-maintained documentation.

### ORACC-TF

ORACC-TF adds an agent-coordination lesson for autonomous development:

- reconcile issue/PR/claim state before implementation;
- bind one canonical PR to one active task claim;
- test the exact PR head;
- invalidate stale review after implementation changes;
- separate implementation reasoning from independent review reasoning.

Issue #5 will decide how much of that machinery is appropriate for this smaller repository.

## Initial architectural risks

1. **Wrong canonical input.** CoNLL-U is convenient for syntax but may omit original/layout/entity/metadata information; `*.tt` is richer but corpus-level metadata may need merging.
2. **Crossing semantic/layout boundaries.** Layout tags can interrupt token character content, so naive XML-to-tree assumptions can lose or fragment tokens.
3. **False deduplication.** Identical copies, alternate analyses, and parallel witnesses require different treatment.
4. **Misleading TF sections.** Biblical and non-biblical corpora have different citation systems; a universal fabricated `book/chapter/verse` projection could misrepresent sources.
5. **Local IDs leaking globally.** Upstream XML IDs are document-local.
6. **Technical-anchor text leakage.** Non-slot nodes can render unrelated slot text unless formats/anchors are designed explicitly.
7. **Silent format disagreement.** Merging metadata/annotations by precedence without measuring disagreement can hide upstream inconsistencies.
8. **Mixed licensing.** Generated corpus redistribution cannot be assumed from converter-code licensing.
9. **Scale.** The upstream repository is large; synthetic tests need a pinned corpus-scale validation path and explicit performance budget.

## Research queue

- #1: source-format inventory and canonical conversion contract
- #2: identity/overlap/redundancy/addressing policy
- #3: TF graph-model design
- #5: autonomous-agent coordination protocol

Implementation tickets should be derived from reviewed outputs of these research/design tasks rather than pre-created against an unreviewed schema.
