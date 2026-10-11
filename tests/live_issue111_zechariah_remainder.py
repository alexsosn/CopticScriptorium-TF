"""Real pinned source/Greek *diagnostic* for Bohairic Zechariah 2:7–13.

No versification rule is changed here. Source Brenton English translations are
a non-independent verse-local comparison aid; not Coptic/Greek collation.
Only source counts and hand-curated motif evidence are printed, never text.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

from tf.fabric import Fabric

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.lxx_module import verify_lxx_parent_feature_blobs
from copticscriptorium_tf.lxx_reference import resolve_coptic_lxx_references
from copticscriptorium_tf.lxx_versification import BOHAIRIC_ZECH_CHAPTER_SHA

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
LXX_PIN = "f32a98eddf7eb239aa73ab863d70381e416d5076"
CTS = "urn:cts:copticLit:ot.zach.bohairic_ed:02"
ZIP = "bohairic.ot/bohairic.ot_TT.zip"
RECORD = "bohairic.ot/bohairic.ot:38_Zacharias_02"
RECORD_MEMBER = "38_Zacharias_02.tt"
EN_STEMS = {
    7: ("ion", "babylon"), 8: ("apple", "eye"), 9: ("hand", "spoil"),
    10: ("rejoic", "ion"), 11: ("nation", "dwell"),
    12: ("juda", "jerusalem"), 13: ("flesh", "cloud"),
}
GREEK_STEMS = {
    11: ("σιων", "βαβυλων"), 12: ("κορ", "οφθαλμ"),
    13: ("χειρ", "σκυλ"), 14: ("θυγατ", "σιων"),
    15: ("εθν", "κατασκην"), 16: ("ιουδα", "ιερουσαλημ"),
    17: ("σαρξ", "νεφελ"),
}
WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)


def normalized_tokens(value: str) -> tuple[str, ...]:
    plain = "".join(
        ch.casefold() for ch in unicodedata.normalize("NFD", value)
        if not unicodedata.combining(ch)
    )
    return tuple(WORD_RE.findall(plain.replace("ς", "σ")))


def stem_score(words: tuple[str, ...], stems: tuple[str, ...]) -> int:
    return sum(any(stem in word for word in words) for stem in stems)


def verse_translation_words(document, ordinals: tuple[int, ...]) -> tuple[str, ...]:
    # Accept only source translation spans *entirely* within a marked verse.
    word_set = set(ordinals)
    fragments = sorted(
        (min(set(t.word_ordinals)), t.text)
        for t in document.translations
        if t.word_ordinals and set(t.word_ordinals) <= word_set
    )
    return normalized_tokens(" ".join(text for _, text in fragments))


def run(coptic_root: Path, lxx_root: Path) -> None:
    verify_lxx_parent_feature_blobs(lxx_root)
    api = Fabric(locations=[str(lxx_root)], silent="deep").load(
        "book chapter verse subverse word orig_order", silent="deep"
    )
    assert api and api.F.otype.maxSlot == 623693
    assert len(api.F.otype.s("verse")) == 30371

    archive_path = coptic_root / ZIP
    assert archive_path.is_file() and not archive_path.is_symlink()
    with ZipFile(archive_path) as zip_file:
        members = tuple(
            m for m in zip_file.namelist() if m.endswith("/" + RECORD_MEMBER) or m == RECORD_MEMBER
        )
        if len(members) != 1:
            raise ValueError(f"expected exact one Zechariah chapter2 TT member, found {len(members)}")
        raw = zip_file.read(members[0])

    doc = parse_tt_record(
        raw, source_record_id=RECORD, source_path=f"{ZIP}!{members[0]}",
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit=PIN, packaging="archive",
    )
    assert doc.source_sha256 == BOHAIRIC_ZECH_CHAPTER_SHA[2]
    assert doc.metadata.get("document_cts_urn") == CTS
    assert doc.metadata.get("chapter", "").lstrip("0") == "2"
    assert "Brenton" in (doc.metadata.get("translation") or ""), (
        "source English translation provenance changed"
    )

    def greek_reference(verse: int):
        node = api.T.nodeFromSection(("Zech", 2, verse))
        if node is None or api.F.otype.v(node) != "verse":
            return None, ()
        words = tuple(api.L.d(node, otype="word"))
        return node, normalized_tokens(" ".join(api.F.word.v(w) or "" for w in words))

    actual = resolve_coptic_lxx_references(
        doc, lookup=lambda b, c, v: api.T.nodeFromSection((b, c, v))
    )
    rows = []
    for source_verse in range(7, 14):
        spans = [x for x in actual if x.source_verse_n == str(source_verse)]
        if len(spans) != 1:
            raise ValueError(f"not one real source span at Boh Zech2:{source_verse}: {len(spans)}")
        ref = spans[0]
        # Fail-closed current production rule is prerequisite, not an issue.
        assert ref.status == "ambiguous" and ref.shared_id is None
        english = verse_translation_words(doc, ref.source_word_ordinals)
        shifted_node, greek = greek_reference(source_verse + 4)
        competing_node, competing_greek = greek_reference(source_verse)
        row = {
            "source": f"Bohairic Zech 2:{source_verse}",
            "current_status": ref.status,
            "coptic_words": len(ref.source_word_ordinals),
            "verse_local_english_words": len(english),
            "candidate_greek_address": f"Zech 2:{source_verse + 4}",
            "candidate_node_exists": shifted_node is not None,
            "competing_same_number_node_exists": competing_node is not None,
            "english_motif_matches": stem_score(english, EN_STEMS[source_verse]),
            "greek_candidate_motif_matches": stem_score(greek, GREEK_STEMS[source_verse + 4]),
            "greek_competing_motif_matches": stem_score(competing_greek, GREEK_STEMS[source_verse + 4]),
            "status": "diagnostic_only_no_textual_equivalence",
        }
        rows.append(row)
    summary = {
        "coptic_upstream": PIN, "lxx_parent": LXX_PIN,
        "source_record_id": RECORD, "source_sha256": doc.source_sha256,
        "edition_cts": CTS, "rows": rows,
        "status": "hypothesis; NOT verified manuscript correspondence",
    }
    print(json.dumps(summary, sort_keys=True), flush=True)
    if not all(
        row["candidate_node_exists"]
        and row["verse_local_english_words"] > 0
        and row["english_motif_matches"] >= 1
        and row["greek_candidate_motif_matches"] >= 1
        and row["greek_competing_motif_matches"] < row["greek_candidate_motif_matches"]
        for row in rows
    ):
        raise AssertionError("At least one of seven textual-numbering hypotheses lacks positive discriminating evidence")
    print("PASS seven individually supported verse-numbering candidate hypotheses, NOT bilingual alignment")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python tests/live_issue111_zechariah_remainder.py COPTIC_ROOT LXX_TF")
    run(Path(sys.argv[1]), Path(sys.argv[2]))
