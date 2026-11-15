"""Real six-source Bohairic Psalm0 ↔ native Rahlfs Greek1/2 word-order audit."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from zipfile import ZipFile

from tf.fabric import Fabric

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.lxx_module import verify_lxx_parent_feature_blobs
from copticscriptorium_tf.psalm_boundary_crosscheck import (
    SELECTED_SOURCE_SHA, SOURCE_PIN, LXX_PIN,
    PsalmBoundaryReview, inspect_selected_psalm,
)

SOURCE_ZIP = Path("bohairic.ot/bohairic.ot_TT.zip")


def run(source_root: Path, lxx_parent: Path, output: Path) -> None:
    if output.exists():
        raise ValueError("refusing to overwrite Psalm primary evidence report")
    verify_lxx_parent_feature_blobs(lxx_parent)
    greek = Fabric(locations=[str(lxx_parent)], silent="deep").load(
        "book chapter verse subverse word orig_order", silent="deep"
    )
    if not greek or greek.F.otype.maxSlot != 623693 or len(
        greek.F.otype.s("verse")
    ) != 30371:
        raise ValueError("real pinned LXX TF parent profile mismatch")

    observed_order: dict[tuple[int, int], tuple[str, ...]] = {}
    def greek_words(chapter: int, verse: int) -> tuple[str, ...]:
        key = (chapter, verse)
        if key not in observed_order:
            node = greek.T.nodeFromSection(("Ps", chapter, verse))
            if node is None or greek.F.otype.v(node) != "verse":
                raise ValueError("LXX Psalm Greek verse section missing or not a verse")
            native_words = greek.L.d(node, otype="word")
            if not native_words or len(native_words) != len(set(native_words)):
                raise ValueError("LXX Greek section has no unique word nodes")
            if tuple(native_words) != tuple(sorted(native_words)):
                raise ValueError("LXX Greek native node order not increasing")
            for slot in native_words:
                if greek.F.otype.v(slot) != "word":
                    raise ValueError("LXX Greek section returned wrong native token")
            forms = tuple(greek.F.word.v(w) for w in native_words)
            if any(not isinstance(form, str) or not form.strip() for form in forms):
                raise ValueError("LXX Greek word feature missing from native slots")
            observed_order[key] = forms
        return observed_order[key]

    audit = PsalmBoundaryReview()
    with ZipFile(source_root / SOURCE_ZIP) as archive:
        members: dict[str, object] = {}
        for member in archive.infolist():
            name = Path(member.filename).name
            if name in members:
                raise ValueError("duplicate physical TT archive filename")
            members[name] = member
        for chapter in sorted(SELECTED_SOURCE_SHA):
            basename = f"19_Psalmi_{chapter:03d}.tt"
            if basename not in members:
                raise ValueError("missing pinned Bohairic Psalm source")
            member = members[basename]
            document = parse_tt_record(
                archive.read(member),
                source_record_id=f"bohairic.ot/bohairic.ot:19_Psalmi_{chapter:03d}",
                source_path=f"{SOURCE_ZIP}!{member.filename}",
                upstream_repository="CopticScriptorium/corpora",
                upstream_commit=SOURCE_PIN,
                packaging="archive",
            )
            evidence = inspect_selected_psalm(document, greek_words=greek_words)
            audit.add(evidence)
            del document
    report = audit.report()
    if report["cases"] != 6 or {row["chapter"] for row in report["records"]} != set(
        SELECTED_SOURCE_SHA
    ):
        raise ValueError("incomplete or duplicate six-Psalm boundary source controls")
    expected = {
        "source_editorial_placeholder": 1,
        "within_first_greek_verse_candidate": 1,
        "cross_greek_verse_boundary_candidate": 1,
        "needs_primary_collation": 3,
    }
    if report["statuses"] != expected:
        raise ValueError(
            f"original Coptic/Greek lexical anchor hypotheses changed: {report['statuses']}"
        )
    if any(row["greek_verse_one_word_count"] < 2
           or row["greek_verse_two_word_count"] < 2
           for row in report["records"]):
        raise ValueError("real Greek first/second Psalm verse word profile invalid")
    report["greek_tf_parent_verified"] = True
    report["original_greek_book_verse_word_nodes"] = len(observed_order)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "cases": report["cases"],
        "statuses": report["statuses"],
        "total_coptic_zero_words": report["total_coptic_zero_words"],
        "greek_verse_count": len(observed_order),
        "case_shapes": [
            {
                "chapter": row["chapter"],
                "source0": row["source_zero_word_count"],
                "source1": row["source_one_word_count"],
                "greek1": row["greek_verse_one_word_count"],
                "greek2": row["greek_verse_two_word_count"],
                "status": row["status"],
                "evidence": row["evidence"],
            }
            for row in report["records"]
        ],
        "interpretation": "Source-language lexical anchor hypotheses, not translation equivalence",
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: python tests/live_issue201_psalm_boundary.py "
            "PINNED_COPTIC_ROOT PINNED_LXX_TF OUTPUT_JSON"
        )
    run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
