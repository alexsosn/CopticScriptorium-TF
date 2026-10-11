"""Source-byte-qualified *alternative Greek edition* verse-address probes (#149).

Never select a Coptic textual edition based on matching numeric references.
All results remain 'unresolved_edition', even if one Greek alternative has
more matching addresses than the other. This is research, not a TF sidecar.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Callable, Mapping

PINNED_COPTIC = "3ac067f1709a0012daf39ea8da2fac79980176a5"
PROVEN_SOURCE_REPORT_RUN = 38165316273
PROVEN_SOURCE_REPORT_JOB = 114546559963
PROVEN_SOURCE_HEAD = "8b02a2507b48b9e4f93ba5c1559d47cd69e4edfe"
SCHEMA = "coptic_ot_unclassified_variant_gap_events_v1"
# Independently derived from the 10 exact event tuples in the successful
# run 38165316273 source-anomaly artifact, sorted by (record, chapter, ordinal)
# and serialized with json.dumps(..., ensure_ascii=True, separators=(",", ":")).
# A valid-looking TT SHA does not otherwise authenticate the *marker* fields.
EXPECTED_EVENT_TUPLE_SHA256 = "dff2461419ca0088f353c9a89226d863b4aa59c50151f96d0047d513fedde49a"
GREEK_VARIANTS = {
    "ot.dan": ("Dan", "DanTh"),
    "ot.tob": ("TobBA", "TobS"),
    "ot.sus": ("Sus", "SusTh"),
    "ot.bel": ("Bel", "BelTh"),
}
# Exact physical source record hashes independently measured by full pinned
# Coptic CI. This whitelist rejects a valid-looking but unreviewed TT edition.
SOURCE_SHA256: Mapping[str, tuple[str, str, int]] = {
    "sahidic.ot/sahidic.ot:27_Daniel_04": (
        "0c473af5a8b50b83f447cc98bbfc4a4235970d53723992f7055385797d5594a9", "ot.dan", 4,
    ),
    "sahidic.ot/sahidic.ot:27_Daniel_05": (
        "9db35a519774dfaf1b8e58537fac8ad94e2431a08f8a82d39c291b9027c102fc", "ot.dan", 5,
    ),
    "sahidic.ot/sahidic.ot:27_Daniel_10": (
        "831fedf2b4956ab4ecc595d8ec67ed6787b5a3d96a879123e5936c0a00cfd70e", "ot.dan", 10,
    ),
    "sahidic.ot/sahidic.ot:67_Tobit_04": (
        "d23211beabe033f7f10d4a2bdaea1724a6c8e450e0c2fdbb7a27e9f9bdb82ecc", "ot.tob", 4,
    ),
    "sahidic.ot/sahidic.ot:67_Tobit_05": (
        "07b0e575b016bb3b996f5efce18d70f0e19ec65f12fc2537fb8791748c04caaf", "ot.tob", 5,
    ),
    "sahidic.ot/sahidic.ot:75_Susanna_01": (
        "c4af337ee2d1d0fb7f50f3982eb6e8a049c04ff99e46bec67066e952c4a3d258", "ot.sus", 1,
    ),
    "sahidic.ot/sahidic.ot:76_Bel_and_the_Dragon_01": (
        "52f68085124e4f4e6b7a05d65e79a8e3d44332e41813ce28cfba4b9e63081ea5", "ot.bel", 1,
    ),
}


class EditionProbeError(ValueError):
    """Invalid or untrusted original source evidence or parent address lookup."""


@dataclass(frozen=True, slots=True)
class GreekAddressEvidence:
    verse: int
    node: int | None
    subverse_count: int

    @property
    def address_exists(self) -> bool:
        return self.node is not None


@dataclass(frozen=True, slots=True)
class GreekVariantEvidence:
    book: str
    before: GreekAddressEvidence
    after: GreekAddressEvidence
    intermediate: tuple[GreekAddressEvidence, ...]


@dataclass(frozen=True, slots=True)
class SourceEditionGapProbe:
    source_record_id: str
    source_sha256: str
    source_cts_work: str
    source_edition: str
    source_chapter: int
    source_marker_ordinal: int
    previous_verse: int
    current_verse: int
    status: str
    selected_lxx_book: None
    variants: tuple[GreekVariantEvidence, GreekVariantEvidence]


def _integer(value: object) -> bool:
    return type(value) is int and value > 0


def _validate_fixture(data: Mapping[str, object]) -> list[tuple[str, str, str, int, int, int, int]]:
    if (
        data.get("schema") != SCHEMA
        or data.get("coptic_source_commit") != PINNED_COPTIC
        or data.get("source_report_run") != PROVEN_SOURCE_REPORT_RUN
        or data.get("source_report_job") != PROVEN_SOURCE_REPORT_JOB
        or data.get("source_report_pr_head") != PROVEN_SOURCE_HEAD
    ):
        raise EditionProbeError("unreviewed source report schema, provenance or Git revision")
    records = data.get("records")
    if not isinstance(records, list) or len(records) != len(SOURCE_SHA256):
        raise EditionProbeError("incomplete source record edition-variant cohort")

    seen_records: set[str] = set()
    seen_events: set[tuple[str, int]] = set()
    items: list[tuple[str, str, str, int, int, int, int]] = []
    for record in records:
        if not isinstance(record, dict):
            raise EditionProbeError("source record must be a typed object")
        rid = record.get("source_record_id")
        sha = record.get("source_sha256")
        work = record.get("source_cts_work")
        chapter = record.get("source_chapter")
        edition = record.get("source_edition")
        if (
            not isinstance(rid, str)
            or rid not in SOURCE_SHA256
            or rid in seen_records
            or sha != SOURCE_SHA256[rid][0]
            or work != SOURCE_SHA256[rid][1]
            or chapter != SOURCE_SHA256[rid][2]
            or edition != "coptot"
        ):
            raise EditionProbeError("unknown, repeated or changed source edition/byte identity")
        seen_records.add(rid)
        events = record.get("events")
        if not isinstance(events, list) or not events:
            raise EditionProbeError("missing source numeric-gap evidence")
        for event in events:
            if not isinstance(event, dict):
                raise EditionProbeError("source marker must be an object")
            ordinal = event.get("source_marker_ordinal")
            prior = event.get("previous_verse")
            after = event.get("current_verse")
            if (
                not _integer(ordinal)
                or not _integer(prior)
                or not _integer(after)
                or after <= prior + 1
                or (rid, ordinal) in seen_events
            ):
                raise EditionProbeError("nonpositive, duplicated or invalid numeric source gap")
            seen_events.add((rid, ordinal))
            items.append((rid, sha, work, chapter, ordinal, prior, after))

    if (
        set(seen_records) != set(SOURCE_SHA256)
        or len(items) != 10
        or sum(after - prior - 1 for _, _, _, _, _, prior, after in items) != 50
    ):
        raise EditionProbeError("full pinned source-gap cohort is missing or modified")
    sorted_items = sorted(items, key=lambda x: (x[0], x[3], x[4]))
    digest = sha256(json.dumps(
        sorted_items, ensure_ascii=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()
    if digest != EXPECTED_EVENT_TUPLE_SHA256:
        raise EditionProbeError("forged or changed source marker ordinal/verse transition")
    return sorted_items


def probe_pinned_variant_gaps(
    data: Mapping[str, object],
    *,
    lookup: Callable[[str, int, int], int | None],
    subverse_count: Callable[[int], int] | None = None,
) -> tuple[SourceEditionGapProbe, ...]:
    """Check both Greek book editions, never adjudicate their textual identity.

    Verse existence is parent-corpus address evidence *only*. The caller must
    verify the exact CenterBLC/LXX parent version and feature fingerprints.
    """
    if not isinstance(data, dict) or not callable(lookup):
        raise EditionProbeError("missing structured source report or Greek verse lookup")
    items = _validate_fixture(data)
    rows: list[SourceEditionGapProbe] = []

    for rid, sha, work, chapter, ordinal, prior, after in items:
        variants: list[GreekVariantEvidence] = []
        for book in GREEK_VARIANTS[work]:
            def address(verse: int) -> GreekAddressEvidence:
                node = lookup(book, chapter, verse)
                if node is not None and not _integer(node):
                    raise EditionProbeError("LXX verse callback returned invalid parent node")
                n_subverses = 0 if node is None or subverse_count is None else subverse_count(node)
                if type(n_subverses) is not int or n_subverses < 0:
                    raise EditionProbeError("LXX subverse count callback returned invalid count")
                return GreekAddressEvidence(verse=verse, node=node, subverse_count=n_subverses)

            variants.append(GreekVariantEvidence(
                book=book,
                before=address(prior),
                after=address(after),
                intermediate=tuple(address(n) for n in range(prior + 1, after)),
            ))
        # No numerical arrangement is sufficient to select a text tradition.
        rows.append(SourceEditionGapProbe(
            source_record_id=rid,
            source_sha256=sha,
            source_cts_work=work,
            source_edition="coptot",
            source_chapter=chapter,
            source_marker_ordinal=ordinal,
            previous_verse=prior,
            current_verse=after,
            status="unresolved_edition",
            selected_lxx_book=None,
            variants=(variants[0], variants[1]),
        ))
    return tuple(rows)
