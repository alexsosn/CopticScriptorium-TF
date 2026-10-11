"""Bounded real Coptic OT Zechariah numbering audit against pinned Greek TF.

Evidence only; never silently reclassify a numeric reference as a certified
Greek/Coptic passage or word alignment. No source or generated corpus export.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
import sys
from zipfile import ZipFile

from tf.fabric import Fabric

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.lxx_reference import resolve_coptic_lxx_references
from copticscriptorium_tf.lxx_module import verify_lxx_parent_feature_blobs

COPTIC_PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
LXX_PIN = "f32a98eddf7eb239aa73ab863d70381e416d5076"
OT_ZIPS = (
    "sahidic.ot/sahidic.ot_TT.zip",
    "bohairic.ot/bohairic.ot_TT.zip",
)
# Exact metadata CTS namespace/work, *not* a permissive filename match.
ZACH_CTS = re.compile(
    rb'document_cts_urn="urn:cts:copticLit:ot\.(?:zach|zech)\.[A-Za-z0-9_-]+:[0-9]+"',
    re.IGNORECASE,
)


def is_zechariah_source(raw: bytes) -> bool:
    """Match only Coptic OT Zechariah work in the leading source metadata."""
    meta = raw.split(b">", 1)[0]
    return bool(meta.startswith(b"<meta ") and ZACH_CTS.search(meta))


def focused_verse(chapter: int | None, verse: int | None) -> bool:
    """Review both sides of a historically disputed chapter boundary."""
    return (
        (chapter == 1 and verse is not None and 15 <= verse <= 21)
        or (chapter == 2 and verse is not None and 1 <= verse <= 6)
    )


def propose_bohairic_zechariah_target(
    corpus: str, source_cts: str | None, chapter: int, verse: int,
) -> tuple[int, int] | None:
    """*Diagnostic hypothesis*, NOT a verified chapter/verse mapping.

    This explicitly matches the actual pinned Bohairic Zechariah work/edition.
    Never apply it to Sahidic OT, other Bohairic works, or unreviewed ranges.
    """
    if corpus != "bohairic.ot" or not source_cts:
        return None
    match = re.fullmatch(
        r"urn:cts:copticLit:ot\.zach\.bohairic_ed:(0*[1-9][0-9]*)",
        source_cts,
    )
    if match is None or int(match.group(1)) != chapter:
        return None
    if chapter == 1 and 18 <= verse <= 21:
        return (2, verse - 17)
    if chapter == 2 and 1 <= verse <= 6:
        return (2, verse + 4)
    return None


def _short_source(words, ordinals: tuple[int, ...]) -> str:
    # At most three source words and 50 code points, not a text export.
    return " ".join((words[n - 1].norm or "") for n in ordinals[:3])[:50]


def run(source_root: Path, greek_tf: Path) -> None:
    verify_lxx_parent_feature_blobs(greek_tf)
    api = Fabric(locations=[str(greek_tf)], silent="deep").load(
        "book chapter verse subverse word orig_order", silent="deep"
    )
    if not api or api.F.otype.maxSlot != 623693 or len(api.F.otype.s("verse")) != 30371:
        raise ValueError("pinned LXX native Text-Fabric profile drift")

    def lookup(book: str, chapter: int, verse: int) -> int | None:
        node = api.T.nodeFromSection((book, chapter, verse))
        if node is not None and api.F.otype.v(node) != "verse":
            raise ValueError("Greek section returned non-verse")
        return node

    def greek_at(chapter: int, verse: int) -> dict[str, object]:
        node = lookup("Zech", chapter, verse)
        if node is None:
            return {"ref": f"Zech {chapter}:{verse}", "found": False}
        tokens = tuple(api.L.d(node, otype="word"))
        return {
            "ref": f"Zech {chapter}:{verse}",
            "found": True,
            "verse_node": node,
            "word_count": len(tokens),
            # 4 token head is diagnostic, not a corpus redistribution.
            "first_four_greek_words": [
                api.F.word.v(w) for w in tokens[:4]
            ],
        }

    summary: Counter[str] = Counter()
    rows: list[dict[str, object]] = []
    examined: list[dict[str, object]] = []

    for relative in OT_ZIPS:
        file = source_root / relative
        if not file.is_file() or file.is_symlink():
            raise ValueError(f"missing immutable sparse Coptic OT ZIP: {relative}")
        corpus = relative.split("/", 1)[0]
        dataset = Path(relative).name.removesuffix("_TT.zip")
        with ZipFile(file) as archive:
            for member in sorted(archive.infolist(), key=lambda item: item.filename):
                if member.is_dir() or not member.filename.lower().endswith(".tt"):
                    continue
                raw = archive.read(member)
                if not is_zechariah_source(raw):
                    continue
                source_id = f"{corpus}/{dataset}:{Path(member.filename).stem}"
                document = parse_tt_record(
                    raw, source_record_id=source_id,
                    source_path=f"{relative}!{member.filename}",
                    upstream_repository="CopticScriptorium/corpora",
                    upstream_commit=COPTIC_PIN, packaging="archive",
                )
                summary["zechariah_records"] += 1
                chapter_literal = document.metadata.get("chapter")
                chapter = (
                    int(chapter_literal)
                    if chapter_literal and chapter_literal.isascii()
                    and chapter_literal.isdecimal()
                    else None
                )
                examined.append({
                    "source_record_id": source_id,
                    "cts": document.metadata.get("document_cts_urn"),
                    "chapter": chapter,
                    "edition": (document.metadata.get("Coptic_edition") or "")[:80],
                    "source_info": (document.metadata.get("source") or "")[:80],
                    "note_mentions_versification": "versif" in
                        (document.metadata.get("note") or "").casefold(),
                })

                for ref in resolve_coptic_lxx_references(document, lookup=lookup):
                    summary[f"status_{ref.status}"] += 1
                    if not focused_verse(chapter, ref.lxx_verse):
                        continue
                    row: dict[str, object] = {
                        "source_record_id": source_id,
                        "source_sha256": document.source_sha256,
                        "source_work_cts": document.metadata.get("document_cts_urn"),
                        "source_chapter": chapter,
                        "source_verse_n": ref.source_verse_n,
                        "source_vid_n": ref.source_vid_n,
                        "source_verse_vid": ref.source_verse_vid,
                        "source_word_count": len(ref.source_word_ordinals),
                        "coptic_head": _short_source(document.words, ref.source_word_ordinals),
                        "reference_status": ref.status,
                        "candidate_lxx_reference": ref.shared_id,
                        "reason": ref.reason,
                    }
                    if chapter is not None and ref.lxx_verse is not None:
                        row["identically_numbered_greek"] = greek_at(chapter, ref.lxx_verse)
                        proposed = propose_bohairic_zechariah_target(
                            corpus, document.metadata.get("document_cts_urn"),
                            chapter, ref.lxx_verse,
                        )
                        if proposed is not None:
                            # Comparison-only candidate; source English renderings
                            # can be misaligned (upstream notes) and are NOT proof.
                            row["hypothetical_shifted_greek"] = greek_at(*proposed)
                            row["hypothesis_status"] = "needs_independent_textual_review"
                            source_slots = set(ref.source_word_ordinals)
                            source_translations = [
                                trans.text for trans in document.translations
                                if source_slots.intersection(trans.word_ordinals)
                            ]
                            row["unverified_translation_head"] = (
                                source_translations[0][:85] if source_translations else None
                            )
                    rows.append(row)

    if not summary["zechariah_records"]:
        raise ValueError("no pinned Zechariah OT work records found in two source ZIPs")
    if not any(row["source_chapter"] == 1 for row in rows):
        raise ValueError("pinned Coptic Zechariah chapter 1 review window missing")
    if not any(row["source_chapter"] == 2 for row in rows):
        raise ValueError("pinned Coptic Zechariah chapter 2 review window missing")
    if not lookup("Zech", 2, 1):
        raise ValueError("pinned LXX Zech 2:1 cannot be located")
    if len(rows) > 70:
        raise ValueError("diagnostic is unexpectedly broad; do not print unbounded text")

    print(json.dumps({
        "source_git": COPTIC_PIN,
        "greek_git": LXX_PIN,
        "diagnostic_only_not_textual_alignment": True,
        "source_scope": examined,
        "counts": dict(sorted(summary.items())),
        "focus": rows,
    }, ensure_ascii=False, sort_keys=True))
    print("PASS pinned source/Greek Zechariah numbering *diagnostic*, no inferred remapping")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: python tests/live_issue95_zechariah.py COPTIC_OT_ZIP_ROOT LXX_TF_DIR"
        )
    run(Path(sys.argv[1]), Path(sys.argv[2]))
