"""TF-independent normalized source model for Coptic Scriptorium records."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

# Inside-norm TT wrappers requiring source-exact positional conservation.
# Source evidence is not a certified whole-word morphological analysis.
TOKEN_WRAPPER_TYPES = (
    "morph", "norm_func", "norm_head", "norm_xml:id", "norm_new_sent",
)
# Native edition numbering distinct from manuscript layout and biblical refs.
EDITION_WRAPPER_TYPES = ("ed_line_n", "ed_lb_n", "ed_page_n", "ed_pg_n")
# Source grouping over multiple normalized words; not new word slots.
MULTIWORD_WRAPPER_TYPES = ("multiword",)
# Textual edition reference labels, never inferred Coptic biblical/LXX mapping.
REFERENCE_WRAPPER_TYPES = (
    "chapter_n", "marcion_chapter_n", "marcion_verse_n",
    "petermann_chapter_n", "petermann_verse_n",
)
# Single-literal, source-preserving editorial witness annotations.
EDITORIAL_WRAPPER_TYPES = (
    "hi_rend", "note", "gap_reason", "supplied_reason", "note_note",
    "gap_unit", "supplied_source", "gap_quantity", "gap_extent",
    "supplied_evidence", "unclear_reason", "unclear",
)
# Exact source-attribute dictionaries for ambiguous interventions/abbreviations.
INTERVENTION_WRAPPER_KEYS = {
    "gap": frozenset(("gap", "extent", "reason", "unit")),
    "supplied": frozenset(("supplied", "source", "reason")),
    "abbr": frozenset(("type",)),
}
INTERVENTION_WRAPPER_TYPES = tuple(INTERVENTION_WRAPPER_KEYS)
# Source entity/name labels; no automatically certified ontology identity.
ENTITY_SOURCE_WRAPPER_TYPES = (
    "entity_head_tok", "entity_text", "entity_identity",
    "persName_type", "placeName_type", "placeName_ref",
    "roleName_type", "rs_type", "org_type",
)
DOCUMENT_SOURCE_WRAPPER_TYPES = (
    "pb_coptic_id", "p_n", "p", "p_source", "pb_n", "lb_nb",
)
# Alternate upstream biblical/CTS identifiers: no inferred canonical crosswalk.
ALTERNATE_REFERENCE_WRAPPER_TYPES = (
    "verse", "verse_n_vid_n", "verse_n_vname", "v_id", "vid__n",
    "chapter_name", "ed_chapter_n", "chapter_2", "ch_n", "chapter",
)
# Source-attested one-attribute long-tail editorial/translation wrappers.
RESIDUAL_SOURCE_WRAPPER_TYPES = (
    "date_type", "german", "section_title", "quote_ref", "quote_type",
    "gap_exent", "ignore_note", "ed_page", "sup", "supplied_quantity",
    "supplied_unit", "sic", "surplus", "source_lang", "pb", "add_place",
    "pb_id", "sub", "gap_reasaon", "gap_reasonn", "hi", "surplus_reason",
    "cb", "del_rend", "figDesc", "figure", "pb_coptic_xml",
)
# Original <hi> has rend=... not hi=...; spelling is part of TT provenance.
RESIDUAL_SOURCE_ATTRIBUTE = {k: ("rend" if k == "hi" else k) for k in RESIDUAL_SOURCE_WRAPPER_TYPES}
# Independently sourced Horner English rendering of the same Coptic words.
HORNER_TRANSLATION_WRAPPER_TYPES = ("trans_horner",)



@dataclass(frozen=True, slots=True)
class Word:
    ordinal: int
    source_id: str | None
    norm: str | None
    lemma: str | None
    pos: str | None
    func: str | None
    head_literal: str | None
    dependency_head_ordinal: int | None
    source_text: str
    # Source-local biblical verse evidence; *not* an LXX passage assertion.
    verse_n: str | None = None
    vid_n: str | None = None
    verse_vid: str | None = None


@dataclass(frozen=True, slots=True)
class Sentence:
    ordinal: int
    word_ordinals: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class Orig:
    value: str | None
    word_ordinals: tuple[int, ...]
    norm_group_index: int


@dataclass(frozen=True, slots=True)
class NormGroup:
    value: str | None
    orig_indices: tuple[int, ...]
    direct_word_ordinals: tuple[int, ...]
    orig_group_index: int | None


@dataclass(frozen=True, slots=True)
class OrigGroup:
    value: str | None
    norm_group_indices: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class LayoutEvent:
    ordinal: int
    kind: str
    value: str | None
    word_ordinal: int | None
    char_offset: int | None
    after_word_ordinal: int


@dataclass(frozen=True, slots=True)
class Entity:
    ordinal: int
    parent_entity_ordinal: int | None
    entity_class: str | None
    identity: str | None
    head_literal: str
    head_word_ordinal: int
    word_ordinals: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class Translation:
    ordinal: int
    text: str
    word_ordinals: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class SblAnnotation:
    """One upstream annotation occurrence; Greek text is not a Coptic word."""

    ordinal: int
    kind: str
    value: str
    word_ordinals: tuple[int, ...]
    source_verse_n: str | None
    start_word_ordinal: int | None
    start_char: int | None
    start_after_word_ordinal: int
    end_word_ordinal: int | None
    end_char: int | None
    end_after_word_ordinal: int
    # Every original TT source attribute, including optional and empty values.
    source_attributes: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class SupplementalWord:
    ordinal: int
    form_literal: str
    form: str
    lemma: str | None
    upos: str | None
    xpos: str | None
    feats: Mapping[str, str]
    head_ordinal: int
    deprel: str | None
    misc: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class ConlluSupplement:
    source_path: str
    words: tuple[SupplementalWord, ...]


@dataclass(frozen=True, slots=True)
class DocumentModel:
    source_record_id: str
    source_path: str
    source_sha256: str
    packaging: str
    upstream_repository: str
    upstream_commit: str
    corpus: str
    dataset: str
    record: str
    scholarly_id: str | None
    metadata: Mapping[str, str]
    metadata_duplicates: Mapping[str, tuple[str, ...]]
    words: tuple[Word, ...]
    sentences: tuple[Sentence, ...]
    origs: tuple[Orig, ...]
    norm_groups: tuple[NormGroup, ...]
    orig_groups: tuple[OrigGroup, ...]
    layout_events: tuple[LayoutEvent, ...]
    entities: tuple[Entity, ...]
    translations: tuple[Translation, ...]
    arabic_translations: tuple[Translation, ...]
    source_text: str = field(repr=False)
    # CoNLL-U supplementation outcome. ``None`` means supplementation was not
    # attempted; the converter always records an explicit status.
    conllu_status: str | None = None
    conllu_source_path: str | None = None
    conllu_source_sha256: str | None = None
    conllu_words: tuple[SupplementalWord, ...] | None = field(default=None, repr=False)
    sbl_annotations: tuple[SblAnnotation, ...] = ()
    # Separate upstream language wrapper occurrences; not SBL Greek text.
    language_annotations: tuple[SblAnnotation, ...] = ()
    # One opening-ordered occurrence track for crossed token-internal TT tags.
    token_annotations: tuple[SblAnnotation, ...] = ()
    # Precise edition pagination wrappers, preserving source literals and offsets.
    edition_annotations: tuple[SblAnnotation, ...] = ()
    # Source-exact multiword wrappers over existing canonical norm tokens.
    multiword_annotations: tuple[SblAnnotation, ...] = ()
    # Literal source edition chapter and verse wrapper occurrences.
    reference_annotations: tuple[SblAnnotation, ...] = ()
    # Source-attested editorial markup; no restored-text interpretation.
    editorial_annotations: tuple[SblAnnotation, ...] = ()
    # Source-exact multi-attribute gap/supplied/abbr interventions.
    intervention_annotations: tuple[SblAnnotation, ...] = ()
    # Original entity/name-label spans separate from interpreted entity nodes.
    entity_source_annotations: tuple[SblAnnotation, ...] = ()
    document_source_annotations: tuple[SblAnnotation, ...] = ()
    alternate_reference_annotations: tuple[SblAnnotation, ...] = ()
    residual_annotations: tuple[SblAnnotation, ...] = ()
    horner_translation_annotations: tuple[SblAnnotation, ...] = ()
