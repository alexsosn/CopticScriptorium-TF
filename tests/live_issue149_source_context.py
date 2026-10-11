"""Real pinned Coptic OT source-context batch for Greek edition alternatives (#149).

Only structural counts and keys are printed; TT lexical surfaces, source notes,
Greek words, and translations are never uploaded or printed.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from copticscriptorium_tf.ot_variant_probe import _validate_fixture
from copticscriptorium_tf.ot_variant_source_context import inspect_source_gap_context

FIXTURE = ROOT / "research/issue-149/pinned-ambiguous-gaps.json"
ZIP_RELATIVE = "sahidic.ot/sahidic.ot_TT.zip"
PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"


def main(root: Path) -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    # Validate all seven TT hashes and the independently source-qualified
    # canonical digest of ten marker events before accessing any source.
    validated = _validate_fixture(fixture)
    assert len(validated) == 10
    archive = root / ZIP_RELATIVE
    if not archive.is_file():
        raise RuntimeError("missing sole sparse pinned Coptic OT source ZIP")

    rows: list[dict[str, object]] = []
    with ZipFile(archive) as bundle:
        members: dict[str, list[str]] = {}
        for member in bundle.infolist():
            if member.is_dir() or not member.filename.casefold().endswith(".tt"):
                continue
            basename = Path(member.filename).name
            members.setdefault(basename, []).append(member.filename)
        for record in fixture["records"]:
            rid = record["source_record_id"]
            filename = rid.split(":", 1)[1] + ".tt"
            matches = members.get(filename, [])
            if len(matches) != 1:
                raise RuntimeError(f"record source ZIP member is missing/ambiguous: {rid}")
            raw = bundle.read(matches[0])
            actual_sha = sha256(raw).hexdigest()
            if actual_sha != record["source_sha256"]:
                raise RuntimeError(f"pinned TT byte hash mismatch: {rid}")
            events = tuple((
                event["source_marker_ordinal"],
                event["previous_verse"],
                event["current_verse"],
            ) for event in record["events"])
            context = inspect_source_gap_context(
                raw,
                expected_sha256=record["source_sha256"],
                expected_chapter=record["source_chapter"],
                expected_events=events,
            )
            rows.append({
                "source_record_id": rid,
                "source_sha256": actual_sha,
                "source_cts_work": record["source_cts_work"],
                "original_source_gap_contexts": [{
                    "source_marker_ordinal": gap.source_marker_ordinal,
                    "previous_verse": gap.previous_verse,
                    "current_verse": gap.current_verse,
                    "missing_number_count": gap.missing_number_count,
                    "coptic_words_since_previous_verse_marker": (
                        gap.words_since_prior_verse_marker
                    ),
                    "editorial_greek_name_mentions": list(
                        gap.editorial_greek_name_mentions
                    ),
                    "status": gap.status,
                } for gap in context],
                "source_metadata_keys": list(context[0].source_metadata_keys),
            })
    flat = [item for row in rows for item in row["original_source_gap_contexts"]]
    assert len(rows) == 7 and len(flat) == 10
    assert sum(x["missing_number_count"] for x in flat) == 50
    print(json.dumps({
        "source_repository": "CopticScriptorium/corpora",
        "source_commit": PIN,
        "source_zip": ZIP_RELATIVE,
        "verified_physical_records": len(rows),
        "verified_source_gap_events": len(flat),
        "missing_intermediate_numeric_labels": 50,
        "source_context": rows,
        "interpretation": (
            "TT source byte and numeric marker positions authenticated; "
            "preceding marker-span word counts and editorial-name mentions "
            "are NOT Greek edition selection or bilingual textual equivalence."
        ),
    }, sort_keys=True))
    print("PASS 7 original Coptic TT sources / 10 verse gaps; no Greek edition assigned")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python tests/live_issue149_source_context.py PINNED_CORPUS_ROOT")
    main(Path(sys.argv[1]))
