"""Read-only paired TT source verse-label evidence for reviewed 1Cor 14 only.

Neither the human verse tag nor the verse_vid tag is a Greek token alignment.
Each candidate needs both source labels corroborating an existing Coptic SBL
whole-word span and document CTS metadata. Source bytes are never edited.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re

from .model import DocumentModel
from .parser import TAG_RE, _scan_attrs

PHYSICAL_RECORD = "sahidica.1corinthians/sahidica.1corinthians:1Cor_14"
HUMAN = re.compile(r"^1 Corinthians 14:([1-9][0-9]*)$")
EDITOR = re.compile(r"^46N 14:([1-9][0-9]*)$")


@dataclass(frozen=True, slots=True)
class Pair:
    number: int
    human: str
    editor: str


def paired_word_verses(document: DocumentModel) -> tuple[Pair | None, ...]:
    """Re-read source tag lifetimes, fail closed on incomplete word labels.

    This is not a new TF converter: it only qualifies source address evidence
    already attached to native original SBL nodes.
    """
    if document.source_record_id != PHYSICAL_RECORD:
        return ()
    if sha256(document.source_text.encode("utf-8")).hexdigest() != document.source_sha256:
        raise ValueError("source bytes do not match the claimed Coptic TT SHA256")
    human_stack: list[str] = []
    editor_stack: list[str] = []
    word_open = False
    started: tuple[str | None, str | None] | None = None
    invalid_word = False
    pairs: list[Pair | None] = []

    def current() -> tuple[str | None, str | None]:
        return (human_stack[-1] if human_stack else None,
                editor_stack[-1] if editor_stack else None)

    for match in TAG_RE.finditer(document.source_text):
        closing = bool(match.group(1))
        name = match.group(2)
        if name not in {"verse", "verse_vid", "norm"}:
            continue
        if name == "norm":
            if not closing:
                if word_open:
                    raise ValueError("nested word in paired TT evidence")
                word_open = True
                started = current()
                invalid_word = False
            else:
                if not word_open:
                    raise ValueError("orphan word end in paired TT evidence")
                finished = current()
                if invalid_word or started is None or finished != started:
                    pairs.append(None)
                else:
                    human, editor = started
                    mh = HUMAN.fullmatch(human or "")
                    me = EDITOR.fullmatch(editor or "")
                    pairs.append(
                        Pair(int(mh.group(1)), human, editor)
                        if mh is not None and me is not None
                           and mh.group(1) == me.group(1)
                        else None
                    )
                word_open = False
                started = None
            continue
        if word_open:
            invalid_word = True
        stack = human_stack if name == "verse" else editor_stack
        # In the real 1Cor14 TT layer, editor -> human tags *open*
        # before each word, but close editor -> human (not XML nesting).
        # These independent concurrent markup layers may overlap at a
        # between-word boundary. The only admissible evidence is that BOTH
        # open scopes cover every complete Coptic word and agree on verse.
        # Never accept a start of human without editor or a new editor
        # while the previous human scope is still open.
        if not closing and (
            (name == "verse" and not editor_stack)
            or (name == "verse_vid" and human_stack)
        ):
            raise ValueError("invalid paired source label opening order")
        if closing:
            if not stack:
                raise ValueError("orphan paired TT verse label")
            stack.pop()
        else:
            attrs, _ = _scan_attrs(match.group(3))
            if name not in attrs or len(stack) > 0:
                raise ValueError("ambiguous nested paired TT verse labels")
            stack.append(attrs[name])
    if word_open or human_stack or editor_stack or len(pairs) != len(document.words):
        raise ValueError("unbalanced paired TT label scopes or Coptic word count")
    return tuple(pairs)


def source_pair_for_sbl(
    document: DocumentModel, word_pairs: tuple[Pair | None, ...],
    word_ordinals: tuple[int, ...],
) -> Pair | None:
    """Require EVERY fully enclosed original Coptic word to share both labels."""
    if document.source_record_id != PHYSICAL_RECORD or not word_ordinals:
        return None
    if any(type(i) is not int or i < 1 or i > len(word_pairs)
           for i in word_ordinals):
        return None
    scoped = {word_pairs[i - 1] for i in word_ordinals}
    if len(scoped) != 1:
        return None
    pair = next(iter(scoped))
    if pair is None:
        return None
    if any(document.words[i - 1].verse_n is not None
           or document.words[i - 1].vid_n is not None
           or document.words[i - 1].verse_vid != pair.editor
           for i in word_ordinals):
        return None
    return pair
