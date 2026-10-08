# Issue #66 — wire validated CoNLL-U supplementation into conversion

## Problem

The #1 source contract designates validated CoNLL-U as the supplementary authority for UD FEATS, construction/MISC enrichments, normalized dependency relations and heads absent from TT. #3 (`GRAPH_SCHEMA.md`) requires these to be separately named supplemental features/edges that never overwrite TT. #13 implemented `parse_conllu_supplement` and deferred the feature decision to graph construction; #14/#15 never took it. The converter and Agora adapter therefore emit TT annotations only.

## Measured evidence (pinned `CopticScriptorium/corpora@3ac067f1709a0012daf39ea8da2fac79980176a5`)

Re-measured locally with the current `parse_conllu_supplement` over a sparse TT+CoNLL-U checkout:

| Measure | Value |
| --- | ---: |
| TT records / CoNLL-U records / paired (case-insensitive) | 2,628 / 2,628 / 2,628 |
| paired identities whose literal spelling differs | 0 |
| supplemented documents / words | 2,361 / 2,104,966 |
| `placeholder` / `malformed_conllu` | 227 / 40 |
| `unsupported_conllu_shape` / `token_alignment` | 0 / 0 |
| CoNLL-U heads where TT has no head (non-root + root) | 51,627 + 1,146 = 52,773 |
| CoNLL-U heads disagreeing with an existing TT head | 0 |
| DEPREL ≠ TT `func` | 4,902 |
| CoNLL-U LEMMA ≠ TT `lemma` / XPOS ≠ TT `pos` | 5 / 1 |
| FORM literal ≠ unescaped FORM (XML entity serialization only) | 4 |
| empty UPOS / empty DEPREL in supplemented words | 0 / 0 |

FEATS keys (16): `PronType`, `Number`, `Definite`, `Gender`, `Person`, `VerbForm`, `Foreign`, `Poss`, `Mood`, `Number[psor]`, `Gender[psor]`, `Polarity`, `NumType`, `ExtPos`, `Emph`, `Reflex`.

MISC keys (7): `Entity` (345,466), `Orig` (304,180), `OrigLang` (140,794), `Morphs` (32,032), `CxnElt` (15,584), `Cxn` (8,708), `Subject` (27). No MISC value contains `|`, tab or newline.

Two MISC values carry structure inside a literal string: `Entity` uses bracket span notation (`(person`, `person)`, `(event)`) that parallels the authoritative TT entity layer, and `CxnElt` prefixes a **sentence-local** CoNLL-U word ID (`20:Conditional-…Protasis`). The converter keeps both as literal source strings; turning them into graph structure would be new inference and needs its own gate.

The pinned full-corpus workflows (#16, #26) already check out the complete upstream tree, which contains the CoNLL-U exports. Agora's Git acquisition uses `subpath: "."`, so it does too.

## Source contract

- Discovery mirrors TT discovery strictness: `corpus/dataset_CONLLU/*.conllu` directories and `corpus/dataset_CONLLU.zip` packages whose members are root-level or under `dataset_CONLLU/`, with a case-insensitive `.conllu` suffix. Symlinks, nested layouts, non-regular files and record-less datasets/archives fail closed, as they do for TT.
- Identity is `corpus/dataset:record`, the same as TT `source_record_id`, and pairing is case-insensitive as in the #13 census. A case-insensitive collision among CoNLL-U records fails closed.
- Records are located during discovery and read one at a time while pairing, so the CoNLL-U corpus text is never held in memory at once.
- TT remains canonical. A TT record is converted identically whether or not a CoNLL-U counterpart exists or validates.

## Per-document status (never silent)

Each document node carries `conllu_status`:

- `supplemented`: valid and token/sentence-aligned;
- `placeholder`, `malformed_conllu`, `unsupported_conllu_shape`, `token_alignment`: existing `SupplementUnavailable` reasons;
- `invalid_utf8`: new non-supplementing reason (currently an uncaught `UnicodeDecodeError`);
- `missing`: no CoNLL-U counterpart (for example a TT-only source tree).

`conllu_source_path` and `conllu_source_sha256` record the literal counterpart and its hash whenever one exists. CoNLL-U records without a TT counterpart are not converted (TT is canonical) and are listed in the summary.

## Graph contract

Word slots of supplemented documents gain separately named native features. TT features are untouched.

| TF feature | Kind | Source |
| --- | --- | --- |
| `ud_lemma`, `ud_upos`, `ud_xpos`, `ud_deprel` | str word | LEMMA, UPOS, XPOS, DEPREL |
| `ud_head_ordinal` | int word | document-normalized HEAD; `0` = root |
| `ud_head` | edge word→word | non-root HEAD |
| `ud_feat_<key>` | str word, one per FEATS key | FEATS value |
| `ud_misc_<key>` | str word, one per MISC key | literal MISC value |
| `conllu_status`, `conllu_source_path`, `conllu_source_sha256` | str document | status/provenance |

CoNLL-U-only heads live only on `ud_head`; `dependency_head` stays TT-only. Users who want the union can traverse both edges explicitly. No packed `Key=Val|…` strings are emitted.

Key → feature-name mapping is deterministic. A UD-shaped key `[A-Z][A-Za-z0-9]*` with an optional `[layer]` becomes snake_case plus `_layer` (`PronType` → `pron_type`, `Number[psor]` → `number_psor`). Any other key uses the existing hex fallback (`ud_feat__hex_<utf8hex>`). Two distinct literal keys mapping to one name fail closed. Each per-key feature records its literal `sourceKey` in TF feature metadata.

Not mapped, with reasons:

- FORM: alignment already requires unescaped FORM == TT `norm`, and the literal differs only by XML-entity serialization in 4 words.
- Multiword-token rows: orthographic grouping is the authoritative TT `norm_group` layer.
- Comment lines: sentence boundaries are validated against TT.
- Empty nodes and enhanced DEPS: already `unsupported_conllu_shape`, with 0 occurrences.

## Operational summary

The summary adds `conllu_supplemented_source_records` (count), `conllu_unavailable_source_records` (sorted `{source_record_id, conllu_source_path, reason, detail}`), `conllu_missing_source_records` and `conllu_records_without_tt`.

## Failure modes considered

- Silent loss: every TT document has exactly one status; every CoNLL-U record is supplemented, unavailable or listed as without TT.
- Overwrite: TT-only conversion and supplemented conversion must give byte-identical TT feature files.
- Misaligned heads: heads are sentence-local and normalized by the reviewed function; the graph validates `ud_head` as a same-document word→word edge.
- Feature-name instability or collision: deterministic mapping, fail-closed collisions, literal key in metadata.
- Memory: about 2.1M supplemental words. Categorical strings are interned and `GraphSlot` references the `SupplementalWord` rather than copying it. Peak RSS is re-measured against the #26 envelope.
- Tests reproducing the implementation: the full-corpus gate re-reads raw CoNLL-U with a separate minimal reader and compares against reloaded TF values.

## Test strategy

1. RED unit tests (`tests/test_issue66_conllu_wiring.py`) on synthetic directory/archive trees: discovery strictness, all statuses, TT invariance, feature names/values/edges, archive vs directory equality, name collision, TT-only trees, summary contents, Agora adapter parity.
2. Pinned full-corpus gate: convert, reload, assert 2,361 supplemented / 227 placeholder / 40 malformed / 0 other / 0 without TT, then independently reread every supplemented CoNLL-U file and compare each word's UD values and the 52,773 TT-absent heads against TF.
3. Resource re-measurement against #26.
