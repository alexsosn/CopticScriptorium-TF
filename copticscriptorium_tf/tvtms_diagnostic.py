"""Read-only STEPBible TVTMS diagnostic for Coptic→LXX reference *candidates*.

The English→Greek table is neither a Coptic witness versification nor a
verified textual alignment. No correspondence is updated by this module.
The external CC BY 4.0 dataset is user/CI supplied, not vendored.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from .lxx_versification import (
    BOHAIRIC_ZECH_CROSSWALK_VERSION, propose_bohairic_zechariah,
)

TVTMS_REPO_COMMIT = "f426b7253623731ce788c8ce7abcd1d8f95c1f70"
TVTMS_GIT_BLOB_SHA = "fe3cd19cdef252e7537bb739b8cf4117dcabe927"
TVTMS_SOURCE_COMMIT = "86ab0b75e195d3269c081201f2ff66afa10d5a30"
TVTMS_SOURCE_SHA256 = "934350a6b9246ca7c017dca78a4292b4f8eeab0aed9a30cc3d27a00afbf9895a"
SCHEMA = "coptic_tvtms_english_to_lxx_diagnostic_v1"
CANDIDATE_STATUSES = frozenset({"reference_candidate", "versification_candidate"})

# Explicitly scoped: every code must be an unambiguous corresponding English
# book label. Exclude Greek alternate-edition Dan/Tob/Sus/Bel and Kingdoms.
# The test of source-numbering semantics happens separately, *per witness*.
ENGLISH_BOOK_FOR_LXX: dict[str, str] = {
    "Gen": "Genesis", "Exod": "Exodus", "Lev": "Leviticus",
    "Num": "Numbers", "Deut": "Deuteronomy", "Josh": "Joshua",
    "Judg": "Judges", "Ruth": "Ruth", "1Chr": "1 Chronicles",
    "2Chr": "2 Chronicles", "Esth": "Esther", "Ps": "Psalms",
    "Prov": "Proverbs", "Qoh": "Ecclesiastes", "Cant": "Song of Solomon",
    "Job": "Job", "Hos": "Hosea", "Mic": "Micah", "Amos": "Amos",
    "Joel": "Joel", "Jonah": "Jonah", "Obad": "Obad",
    "Nah": "Nahum", "Hab": "Habakkuk", "Zeph": "Zephaniah",
    "Hag": "Haggai", "Zech": "Zechariah", "Mal": "Malachi",
    "Isa": "Isaiah", "Jer": "Jeremiah", "Lam": "Lamentations",
    "Ezek": "Ezekiel",
}


def load_pinned_tvtms(path: str | Path) -> dict[str, object]:
    """Load exact external JSON bytes, failing before JSON parsing on any drift.

    SHA is the Git blob content hash, not the *commit* hash or upstream TVTMS
    source SHA-256. The license of this external dataset is CC BY 4.0.
    """
    raw = Path(path).read_bytes()
    oid = sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
    if oid != TVTMS_GIT_BLOB_SHA:
        raise ValueError("external TVTMS Git blob checksum/pin mismatch")
    obj = json.loads(raw)
    if not isinstance(obj, dict) or not isinstance(obj.get("English->LXX"), dict):
        raise ValueError("invalid pinned TVTMS English->LXX shape")
    if len(obj["English->LXX"]) != 4438:
        raise ValueError("pinned external English->LXX row count changed")
    return obj


def _positive_verse(value: object) -> int | None:
    if (
        isinstance(value, str) and value.isascii() and value.isdecimal()
        and int(value) > 0
    ):
        return int(value)
    return None


def _small_examples(row: dict[str, Any], source_id: str) -> None:
    examples = row.setdefault("examples", [])
    if source_id not in examples:
        examples.append(source_id)
        examples.sort()
        del examples[3:]


class TvtmsDiagnostic:
    """Accumulate bounded metadata by OT Coptic physical source record.

    Only the exact, byte-locked, already-reviewed Bohairic Zechariah source
    edition can yield a supported same/different *numbering rule* verdict.
    All other explicit English→Greek differences are hypotheses because
    Sahidic/Bohairic sources may already be numbered in the Greek system.
    """

    def __init__(self, mapping: Mapping[str, object]):
        table = mapping.get("English->LXX")
        if not isinstance(table, dict):
            raise ValueError("missing English->LXX external crosswalk")
        # Never retain original texts, external full JSON, or raw per-verse
        # source groups in the output. A small lookup table is acceptable RAM.
        self._table: Mapping[str, object] = table
        self._counts: Counter[str] = Counter()
        self._words: Counter[str] = Counter()
        self._by_book: dict[str, Counter[str]] = {}
        self._by_family: dict[str, dict[str, Any]] = {}
        self._by_edition: dict[str, Counter[str]] = {}

    @staticmethod
    def _reviewed_zechariah(document: Any, ref: Any, verse: int) -> bool:
        if (
            ref.status != "versification_candidate"
            or ref.lxx_book != "Zech"
            or getattr(ref, "source_record_id", None) != document.source_record_id
            or not isinstance(ref.evidence, str)
            or not ref.evidence.endswith(BOHAIRIC_ZECH_CROSSWALK_VERSION)
        ):
            return False
        chapter = _positive_verse(document.metadata.get("chapter"))
        if chapter is None:
            return False
        proposal = propose_bohairic_zechariah(
            document, lxx_book="Zech", source_chapter=chapter,
            source_verse=verse,
        )
        return (
            proposal is not None and proposal.blocked_reason is None
            and proposal.rule_id == BOHAIRIC_ZECH_CROSSWALK_VERSION
        )

    def _classify(self, document: Any, ref: Any) -> str:
        if ref.status not in CANDIDATE_STATUSES or ref.shared_id is None:
            return "unclassifiable"
        verse = _positive_verse(ref.source_verse_n)
        chapter = _positive_verse(document.metadata.get("chapter"))
        book = ENGLISH_BOOK_FOR_LXX.get(ref.lxx_book)
        if verse is None or chapter is None or book is None:
            return "unclassifiable"

        key = f"{book} {chapter}:{verse}"
        if key not in self._table:
            # This dataset is exception-only. Missing != same numbered reading.
            return "no_explicit_exception"
        target = self._table[key]
        if target is None:
            return "external_non_1to1"
        if (
            not isinstance(target, dict)
            or type(target.get("chapter")) is not int
            or type(target.get("verse")) is not int
            or target["chapter"] <= 0 or target["verse"] <= 0
        ):
            raise ValueError("malformed pinned TVTMS target entry")
        if "part" in target:
            # Verse subdivision cannot be represented as one LXX verse ID.
            return "external_non_1to1"
        if not self._reviewed_zechariah(document, ref, verse):
            return "source_scheme_unverified"
        return (
            "reviewed_agree"
            if (ref.lxx_chapter, ref.lxx_verse)
            == (target["chapter"], target["verse"])
            else "reviewed_disagree"
        )

    def add(self, document: Any, references: Any) -> None:
        """Consume only source records already classified as OT by caller."""
        family = document.corpus
        source_id = document.source_record_id
        cts = (document.metadata.get("document_cts_urn") or "")
        # Edition designation from source, not a normalized Greek edition.
        edition = cts.rsplit(":", 1)[0].rsplit(".", 1)[-1] if cts else "<no_cts>"
        for ref in references:
            status = self._classify(document, ref)
            self._counts[status] += 1
            self._words[status] += len(ref.source_word_ordinals)
            book = ref.lxx_book or "<unclassified>"
            self._by_book.setdefault(book, Counter())[status] += 1
            self._by_edition.setdefault(f"{family}:{edition}", Counter())[status] += 1
            row = self._by_family.setdefault(family, {"counts": Counter(), "examples": []})
            row["counts"][status] += 1
            _small_examples(row, source_id)

    def report(self) -> dict[str, object]:
        return {
            "schema": SCHEMA,
            "source": "STEPBible TVTMS / Tyndale House Cambridge, CC BY 4.0",
            "source_url": "https://github.com/STEPBible/STEPBible-Data",
            "derived_mapping_repo_commit": TVTMS_REPO_COMMIT,
            "derived_mapping_git_blob": TVTMS_GIT_BLOB_SHA,
            "original_tvtms_commit": TVTMS_SOURCE_COMMIT,
            "original_tvtms_sha256": TVTMS_SOURCE_SHA256,
            "direction": "English->LXX; Coptic numbering NOT assumed English",
            "reference_groups": sum(self._counts.values()),
            "word_slots": sum(self._words.values()),
            "status_counts": dict(sorted(self._counts.items())),
            "word_statuses": dict(sorted(self._words.items())),
            "by_book": {
                name: dict(sorted(counter.items()))
                for name, counter in sorted(self._by_book.items())
            },
            "by_edition": {
                name: dict(sorted(counter.items()))
                for name, counter in sorted(self._by_edition.items())
            },
            "by_family": {
                name: {
                    "counts": dict(sorted(row["counts"].items())),
                    "examples": list(row["examples"]),
                }
                for name, row in sorted(self._by_family.items())
            },
            "interpretation": (
                "External English-to-LXX reference-numbering diagnostics only. "
                "Only source-byte-locked Bohairic Zechariah may be reviewed; "
                "no Greek/Coptic textual or word alignment is certified."
            ),
        }
