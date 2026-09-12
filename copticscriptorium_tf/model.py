"""TF-independent normalized source model for Coptic Scriptorium records."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class Sentence:
    ordinal: int
    word_ordinals: tuple[int, ...]


@dataclass(frozen=True)
class Orig:
    value: str | None
    word_ordinals: tuple[int, ...]
    norm_group_index: int


@dataclass(frozen=True)
class NormGroup:
    value: str | None
    orig_indices: tuple[int, ...]
    direct_word_ordinals: tuple[int, ...]
    orig_group_index: int | None


@dataclass(frozen=True)
class OrigGroup:
    value: str | None
    norm_group_indices: tuple[int, ...]


@dataclass(frozen=True)
class LayoutEvent:
    ordinal: int
    kind: str
    value: str | None
    word_ordinal: int | None
    char_offset: int | None


@dataclass(frozen=True)
class Entity:
    ordinal: int
    parent_entity_ordinal: int | None
    entity_class: str | None
    identity: str | None
    head_literal: str
    head_word_ordinal: int
    word_ordinals: tuple[int, ...]


@dataclass(frozen=True)
class Translation:
    ordinal: int
    text: str
    word_ordinals: tuple[int, ...]


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class ConlluSupplement:
    source_path: str
    words: tuple[SupplementalWord, ...]


@dataclass(frozen=True)
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
