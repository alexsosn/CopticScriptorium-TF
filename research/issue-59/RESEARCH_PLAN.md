# Issue #59 research and plan

## Research findings

The researcher-facing contract is already determined by the native TF writer and
graph builder; this ticket should document that contract rather than invent a
second ontology.

### Stable corpus model

The sole slot type is `word`. Non-slot types are emitted only when present in
the selected source material and are ordered as `document`, `sentence`,
`orig_group`, `norm_group`, `orig`, `page`, `column`, `line`,
`entity`, `translation`, and `arabic_translation`.

Every non-slot node is measured over word slots through native `oslots`.
`parent` is directed child -> parent for `orig -> norm_group`,
`norm_group -> orig_group`, and nested entities. `direct_word` is directed
`norm_group -> word` only for words not mediated by an `orig` child.

Layout nodes are real measured TF nodes. Their `own_text` contains the exact
source-text segment between adjacent layout events; the
`start_word_ordinal/start_char/start_after_word_ordinal` and corresponding
end features preserve token-internal/inter-word boundaries.

### Linguistic and semantic edges

Words carry `source_word_ordinal`, optional source `source_id`, `norm`,
`lemma`, `pos`, `func`, literal dependency evidence, and source text.
`dependency_head` is directed dependent word -> head word. A source head
ordinal of `0` or `None` denotes a root/no resolved head and therefore emits
no `dependency_head` edge.

Entities are measured over their word span. `entity_head` is directed
entity -> head word; `entity_class` and `identity` preserve source
annotation. Entity `parent` edges, when present, point child entity -> parent
entity.

English and Arabic translations are measured nodes whose rendered text is
their own `own_text`, not the Coptic anchor text.

Document relations are directed physical-document edges:
`same_scholarly`, `documented_overlap`, and `witness`. Separate valued
edge features preserve classification/family/witness evidence. The converter
does not collapse related physical records into one document.

### Identity, metadata, provenance

`source_record_id` identifies the physical TT record and is the only TF
section address. `scholarly_id` is a separate source scholarly identity and
is not guaranteed unique.

Document metadata is projected to scalar `meta_*` features. Safe lowercase
ASCII keys remain readable as `meta_<key>`; unsafe/case-sensitive/
occurrence-looking keys use reversible UTF-8 hex. Repeated metadata occurrences
are stored as `__2`, `__3`, ... features. There is no semantic JSON/XML
sidecar.

Document provenance includes `source_path`, `source_sha256`, `corpus`,
`dataset`, and packaging. The TF file headers preserve
`upstreamRepository` and `upstreamCommit` globally. The project preserves
upstream assertions and converter provenance; it does not certify scholarly
correctness.

### Text-Fabric Search syntax

The project pins `text-fabric==13.1.0`. Its search reference confirms:

- node feature filters use forms such as `word lemma=value pos=N`;
- directed edge search uses `A -edge_feature> B`;
- reverse traversal uses `A <edge_feature- B`;
- valued edges accept ordinary feature value constraints inside the edge
  operator;
- search results are tuples in template-atom order.

The cookbook should use `api.S.search` directly for lexical, morphology,
dependency, entity-head, document-filter, and relation examples so the
documented syntax is executable rather than illustrative prose only.

## Plan

1. RED: add a documentation contract requiring a dedicated
   `docs/researcher-guide.md`, executable `examples/query_cookbook.py`, and
   README/web-app cross-links.
2. RED: build a representative generated TF fixture containing all documented
   semantic families and execute cookbook functions against it with exact result
   assertions.
3. Implement the researcher guide around the corpus model, annotation
   semantics, provenance/citation, optional/missing values, and the distinction
   between preserved source assertions and project claims.
4. Implement a small importable cookbook with reusable functions plus a CLI
   against a user-supplied generated TF directory. Keep results as ordinary
   Python scalars/tuples/dicts; no sidecars.
5. Cover at least these executable recipes:
   - lemma lookup;
   - POS/function filtering;
   - dependency edge search;
   - entity span/head lookup;
   - English/Arabic translation text;
   - corpus/dataset filtering;
   - physical vs scholarly identity;
   - same-scholarly/documented-overlap/witness relations;
   - normalized vs diplomatic rendering;
   - provenance tracing from a node to physical source information.
6. Require several recipes to use `api.S.search` and assert exact tuple/result
   shapes so documentation drift is visible in CI.
7. Add README links to the guide/cookbook and link the guide to
   `docs/web-app.md`; the web-app file may arrive through the independently
   tracked #58 PR.
8. Run the focused synthetic contract plus a bounded pinned-real-source smoke
   that chooses actual lexical/morphological values from the source slice and
   verifies cookbook search, dependency, rendering, and provenance behavior.
9. Run the full exact-head suite.
10. Freeze the head and perform a logically independent adversarial review
    against the generated feature inventory and real writer semantics.

## Non-goals

No general Text-Fabric tutorial, no replacement browser, no notebook-only opaque
state, no prebuilt corpus distribution, no upstream annotation certification,
and no Agora/Context-Fabric integration work.

## Adversarial refinement

The pre-final review tightened the document-relation regression so it checks
directed physical source -> target identities and every valued evidence edge,
not merely the presence of the three relation feature names. A separate pinned
real-source smoke was also added so the cookbook is exercised on actual TT
directory/archive data while the synthetic fixture remains responsible for
complete relation/entity/layout semantics.
