"""Fail-closed prevention of three confirmed *numeric-address* Psalm false positives.

These are ONLY three exact original Bohairic Psalm verse-1 source records.
The Greek verse 1 of each contains a different superscription than the
source's first body verse. This guard does not guess the true Greek span.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any

SOURCE_PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
RULE_ID = "bohairic-pss-first-body-not-greek-title-v1"
SOURCE_SHA: dict[int, str] = {
    3: "cbeb4996b0cd142e888bcd630eaac6123af05d7084d49b614066fa9799b5b9d6",
    17: "0fc5384f9baa44f0d4a180539b84b9cf06f5a3be5176360fdf7b27c9451e3af3",
    51: "fd179fe092f1adc0feb4bf4b9c0ae38a001175c18e745db014a8ca6bb7231d64",
}


def blocked_same_number_psalm_verse1(
    document: Any, *, lxx_book: str | None,
    source_chapter: int | None, source_verse: int | None,
) -> str | None:
    """Return explicit provenance-qualified reason to drop misleading LXX ID.

    This returns None for a nonprotected document/chapter/verse. For a
    recognized protected witness, *any* edition/revision/source-byte drift
    returns a blocker rather than silently enabling same-number matching.
    """
    if (
        lxx_book != "Ps" or source_verse != 1
        or source_chapter not in SOURCE_SHA
        or document.corpus != "bohairic.ot"
        or document.dataset != "bohairic.ot"
    ):
        return None
    chapter = source_chapter
    expected_id = f"bohairic.ot/bohairic.ot:19_Psalmi_{chapter:03d}"
    expected_cts = f"urn:cts:copticLit:ot.pss.bohairic_ed:{chapter:02d}"
    actual_id = document.source_record_id
    actual_cts = document.metadata.get("document_cts_urn")
    if actual_id != expected_id and actual_cts != expected_cts:
        return None
    if (
        actual_id != expected_id
        or actual_cts != expected_cts
        or document.upstream_repository != "CopticScriptorium/corpora"
        or document.upstream_commit != SOURCE_PIN
        or document.metadata.get("chapter") != f"{chapter:02d}"
        or document.source_sha256 != SOURCE_SHA[chapter]
        or not isinstance(document.source_text, str)
        or sha256(document.source_text.encode("utf-8")).hexdigest()
            != SOURCE_SHA[chapter]
    ):
        return (
            RULE_ID
            + ": recognized Psalm verse 1 but source SHA/CTS/edition/revision "
            "or physical source identity differs; refuse equal-number Greek title"
        )
    return (
        RULE_ID
        + f": pinned original Bohairic Ps {chapter}:1 begins body after its "
        "source verse-zero superscription, whereas same-number Greek Ps "
        f"{chapter}:1 is a title; exact Greek 1:N/word span remains unverified"
    )
