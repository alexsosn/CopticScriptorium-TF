# Issue #3 — Text-Fabric graph schema research plan

Pinned upstream repository: `CopticScriptorium/corpora`

Pinned upstream commit: `3ac067f1709a0012daf39ea8da2fac79980176a5`

Repository base for this cycle: `684bd629156c193cb2296ed09a23c84af539660f`

## Goal

Design the Text-Fabric graph contract for the local union-corpus materializer in issue #11. This ticket produces measured schema/ADR decisions only; it does not implement the production converter or writer.

The design must preserve the source-authority contract from #1 and the physical/scholarly identity and overlap policy from #2.

## Prior-project lessons to enforce

### Pseudepigrapha-TF

- A larger textual locus (`unit`) looked structurally elegant but was rejected as slot type because ordinary word-level TF queries and BHSA-style traversal became worse. Prefer the normal linguistic query unit when source fidelity permits it.
- Putting mutually exclusive variant tokens in the slot stream creates a fictitious text. Non-primary textual alternatives instead use ordinary nodes/edges around the primary slot stream.
- A non-slot node that technically spans/anchors on slots can render misleading descendant text through `T.text()`. Node-type-specific formats are required when the node's semantic text differs from its anchor slots.
- Non-textual metadata objects should use O(1) technical anchors only when TF serialization requires them; anchors must never masquerade as semantic content.
- Deep/heterogeneous source citations should remain literal features even when projected onto a smaller standard section hierarchy.
- Section coverage/address uniqueness must be checked corpus-wide, not inferred from successful serialization.

### ORACC-TF

Accepted project-family architecture distinguishes semantic/source slots from synthetic empty slots. An independently positioned textual zero-span object that otherwise lacks a slot uses an explicit surface-less synthetic slot in source order. Ancestors reuse descendant anchors. Non-textual objects may use a documented O(1) technical anchor instead. Reports must distinguish semantic, synthetic, and total TF slots.

### TLHdig-TF

- Human-facing document identifiers are not necessarily unique section keys; physical source identity must remain separately recoverable.
- A successful `nodeFromSection()` probe does not prove section-address completeness. Every intended section node/address must be validated exhaustively.
- Known-defect allowlists are regression guards, not zero-defect proofs; issue #3 should not normalize a measured graph defect into a permanently green baseline.

## Coptic source constraints already measured

- TT provides 2,628 physical document streams with `orig_group -> norm_group -> orig -> norm` linguistic structure.
- `norm` tokens carry local IDs, lemma, fine POS and source dependency relation/head; structurally valid CoNLL-U aligns token-for-token to this layer for 2,361 documents.
- Page/column/line markup can cross a normalized token's rendered character content. In pinned `AP.004.poemen.65`, token `u7` spans line 34→35 and token `u13` spans 35→36.
- Entities can span multiple normalized tokens and carry a source head token plus optional identity.
- English and Arabic translation layers are present in TT for subsets of documents.
- #2 requires one logical union corpus, every physical source copy preserved, corpus/dataset membership queryable, literal scholarly CTS identity separate, and explicit overlap/witness relations non-destructive.

## Competing slot models

The research census and adversarial fixtures must compare these models rather than choosing from convenience:

### A. normalized `norm` token as `word` slot

Advantages: direct linguistic query unit; dependency/entity edges target slots naturally; aligns with validated CoNLL-U basic tokens; closest to ordinary TF/BHSA ergonomics.

Risk: diplomatic layout boundaries can fall inside a slot. Layout therefore cannot be represented solely by ordinary `oslots` spans without duplicating the whole token in multiple lines or losing the boundary offset.

Candidate mitigation to test: keep `word` slots semantic, represent layout as ordinary layout nodes plus exact token-relative start/end character offsets / boundary events and a literal diplomatic text feature. Layout nodes may overlap token slots, but their default text format must render their own source text rather than blindly `T.text()` descendant slots.

### B. `orig` or orthographic-group slots

Potentially closer to diplomatic text, but the observed line crossing can occur inside `orig`/`norm` content as well. It also moves lemma/POS/dependencies away from the slot unit and complicates CoNLL-U alignment. It must be rejected or accepted from measured source shapes, not assumed.

### C. character/source-piece slots

Can model all layout intersections exactly through normal `oslots`, but multiplies slot count, makes linguistic queries less direct, and turns each `norm` token into a non-slot span. Accept only if word-slot + offset/event modelling cannot preserve or query the source faithfully.

Splitting one linguistic `norm` token into multiple semantic word slots solely to satisfy page/line layout is not an acceptable model.

## Corpus-wide graph-shape census

RED-first research tooling must measure at least:

1. total documents, normalized tokens, original segments, norm groups and orig groups;
2. cardinality distributions (`orig_group`→`norm_group`, group→orig, orig→norm) and any empty groups/tokens;
3. sentence-start coverage from TT (`new_sent`) and whether every semantic token can be partitioned deterministically into sentence nodes;
4. page/column/line boundary counts, boundary nesting/order, and number of boundaries occurring while a `norm` token is open;
5. for token-internal layout crossings: token ID, source-relative character offset, boundary kind/value, and whether multiple boundaries occur inside one token;
6. entity counts, empty entities, nested/overlapping entities, entity token coverage, missing/unresolved `head_tok`, identities and classes;
7. translation/Arabic translation scopes, empty translations, and their relationship to sentence/token spans;
8. zero-span/textless textual structures that would require a synthetic slot under the shared architecture rule;
9. chapter/verse/video/source-reference markers and their coverage across heterogeneous corpora, to prove they cannot be the universal section hierarchy;
10. document/source-record address uniqueness and sentence-address uniqueness under the proposed union-corpus scheme.

Malformed source shapes are errors/ledgers, not silent skips.

## Section/navigation hypotheses to test

The universal section hierarchy must not fabricate biblical chapter/verse semantics for documentary/literary records.

Candidate default:

- level 1: physical `document`, addressed by deterministic source-record identity from #2 (or a reversible technical form of it);
- optional level 2: `sentence` using a deterministic document-local ordinal if TT sentence starts cover every token stream reliably.

Corpus/dataset, scholarly CTS, chapter, verse, video/source references, manuscript identifiers and titles remain ordinary source features/nodes. Biblical-specific citation can be exposed through features/helper queries rather than redefining union-corpus section semantics.

If sentence coverage is incomplete, prefer one universal `document` section level plus ordinary sentence nodes over synthesizing sentences silently.

Every section node must have exactly one deterministic address; every semantic slot must belong to exactly one document and, if sentence is a section type, exactly one sentence. Address validation must be exhaustive.

## Candidate node/edge families to evaluate

- `document` — physical source record; provenance, dataset/corpus, scholarly ID, license/quality metadata;
- `word` — candidate semantic slot corresponding to TT `norm`;
- `orig`, `norm_group`, `orig_group` — grouping/diplomatic hierarchy without assuming XML nesting is globally valid;
- `sentence` — source-derived from sentence starts;
- `page`, `column`, `line` — diplomatic/layout nodes with source labels and exact token-relative coverage/event metadata;
- `entity` — span/class/identity; valued or ordinary edge to head word;
- `translation` / `arabic_translation` — textual annotation node with literal translated text and source locus;
- explicit document-level overlap relations from #2 (`same_scholarly`, measured duplicate class, documented book↔aggregate class, witness relations);
- metadata/provenance nodes only where a node is useful to query; do not make one node per scalar metadata field.

Dependency modelling candidate: source `func` as word feature plus `head` edge word→word; preserve literal local XML ID separately. CoNLL-U-specific normalized relation/head and enrichment features remain separately named so source TT values are never overwritten.

## Technical-anchor / zero-span policy to decide

Classify every node family as one of:

1. semantic slot;
2. textual span/locus node with real descendant slots;
3. independently positioned zero-span textual node requiring a surface-less synthetic slot;
4. non-textual graph object anchored through an existing locus or documented O(1) technical anchor.

No node may borrow a neighbouring real slot merely to satisfy TF. Any technical anchor must have a node-type-specific rendering rule that cannot emit the anchor's unrelated text.

## Source-text/rendering invariants

- normalized linguistic text and original/diplomatic text remain separately reconstructable;
- a layout line crossing a word can reconstruct the literal line without duplicating or truncating the word;
- ordinary word text does not acquire layout-inserted whitespace/newlines unless a named text format requests diplomatic rendering;
- `T.text()` for non-token nodes must not silently display misleading descendant/anchor content;
- no synthetic slot carries fabricated visible Coptic content.

## Identity/overlap invariants from #2

- all physical source records survive;
- `source_record_id` and literal `document_cts_urn` remain distinct;
- same-CTS duplicates do not collapse to one document node;
- documented book↔aggregate pairs keep both documents and relation/classification;
- `redundant=yes` is query/filter evidence, not deletion;
- literal witness text and extracted CTS targets remain separately recoverable;
- corpus/dataset membership remains a feature suitable for corpus-specific views over the union graph.

## RED-first design-fixture plan

Before any converter implementation, synthetic graph-contract tests/fixtures should establish the desired intermediate graph semantics for at least:

1. one ordinary norm token and orig/norm group hierarchy;
2. one norm token split by a line boundary at a character offset;
3. one token crossed by two layout boundaries;
4. dependency root and non-root head resolution without global use of TT-local IDs;
5. multi-token entity with head token and identity;
6. nested/overlapping entity spans if corpus census observes them;
7. sentence partition start/end edge cases;
8. translation attached to a locus without becoming slot text;
9. one physical duplicate-CTS pair and one documented book↔aggregate pair;
10. one witness relation across documents;
11. a textual zero-span locus requiring a synthetic empty slot, if observed/required;
12. a non-textual node using a technical anchor whose default rendering is not anchor text;
13. heterogeneous document section addresses including repeated human titles/CTS IDs;
14. missing optional metadata without fabricated values.

Because #3 is a design ticket, these fixtures may test a schema/model validator rather than a production TF writer. Production conversion remains #11.

## Deliverables

- deterministic corpus-wide graph-shape census and artifact;
- feature/node/edge matrix;
- slot-choice ADR;
- section/address ADR;
- layout-crossing representation ADR;
- zero-span/technical-anchor ADR applying the project-family default to Coptic data;
- rendering/text-format contract;
- synthetic adversarial graph-contract fixtures and acceptance criteria for #11;
- update to `research.md`;
- logically independent exact-head adversarial review.

## Gates

1. Research: upstream source shapes + prior converters + #1/#2 evidence.
2. Plan: this measurement/schema plan committed before behavior tooling.
3. RED-first tests for the graph-shape census/model contract.
4. Minimal research tooling/model validator implementation.
5. Exact-head unit tests + pinned corpus graph-shape census.
6. ADRs written only from generated evidence.
7. Independent adversarial review re-derives decisions from issue #3, prior-project failures, raw TT samples, generated artifact and diff.
8. Merge only if the reviewed exact head is unchanged.
