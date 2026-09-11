"""Pinned corpus census for the production issue #13 TT source parser."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from copticscriptorium_tf.parser import parse_source_tree


UPSTREAM_REPOSITORY = "CopticScriptorium/corpora"
UPSTREAM_COMMIT = "3ac067f1709a0012daf39ea8da2fac79980176a5"

# Independent reviewed measurements from issue #3 / merged PR #12.
EXPECTED = {
    "document_count": 2628,
    "word_count": 2394354,
    "orig_count": 1565993,
    "norm_group_count": 1105458,
    "orig_group_count": 736574,
    "sentence_count": 78993,
    "entity_count": 256677,
    "nested_entity_count": 78243,
    "translation_count": 52346,
    "arabic_translation_count": 1598,
    "page_event_count": 3294,
    "column_event_count": 3291,
    "line_event_count": 47933,
    "token_internal_layout_crossing_count": 13015,
}


def build_report(root: Path) -> dict[str, object]:
    documents = parse_source_tree(
        root,
        upstream_repository=UPSTREAM_REPOSITORY,
        upstream_commit=UPSTREAM_COMMIT,
    )

    totals: Counter[str] = Counter()
    packaging: Counter[str] = Counter()
    source_ids: list[str] = []
    source_hashes: list[str] = []
    zero_word_documents: list[str] = []
    zero_sentence_documents: list[str] = []
    zero_word_translations: list[str] = []
    entity_head_outside_locus: list[str] = []

    for document in documents:
        source_ids.append(document.source_record_id)
        source_hashes.append(document.source_sha256)
        packaging[document.packaging] += 1
        totals["document_count"] += 1
        totals["word_count"] += len(document.words)
        totals["orig_count"] += len(document.origs)
        totals["norm_group_count"] += len(document.norm_groups)
        totals["orig_group_count"] += len(document.orig_groups)
        totals["sentence_count"] += len(document.sentences)
        totals["entity_count"] += len(document.entities)
        totals["nested_entity_count"] += sum(
            entity.parent_entity_ordinal is not None for entity in document.entities
        )
        totals["translation_count"] += len(document.translations)
        totals["arabic_translation_count"] += len(document.arabic_translations)

        if not document.words:
            zero_word_documents.append(document.source_record_id)
        if document.words and not document.sentences:
            zero_sentence_documents.append(document.source_record_id)

        word_by_ordinal = {word.ordinal: word for word in document.words}
        for event in document.layout_events:
            totals[f"{event.kind}_event_count"] += 1
            if event.word_ordinal is not None and event.char_offset is not None:
                word = word_by_ordinal[event.word_ordinal]
                if 0 < event.char_offset < len(word.source_text):
                    totals["token_internal_layout_crossing_count"] += 1

        for translation in (*document.translations, *document.arabic_translations):
            if not translation.word_ordinals:
                zero_word_translations.append(
                    f"{document.source_record_id}:{translation.ordinal}"
                )

        for entity in document.entities:
            if entity.head_word_ordinal not in entity.word_ordinals:
                entity_head_outside_locus.append(
                    f"{document.source_record_id}:{entity.ordinal}"
                )

    measured = {key: totals[key] for key in EXPECTED}
    mismatches = {
        key: {"expected": EXPECTED[key], "measured": measured[key]}
        for key in EXPECTED
        if measured[key] != EXPECTED[key]
    }
    return {
        "upstream_repository": UPSTREAM_REPOSITORY,
        "upstream_commit": UPSTREAM_COMMIT,
        "measured": measured,
        "expected": EXPECTED,
        "mismatches": mismatches,
        "packaging": {key: packaging[key] for key in sorted(packaging)},
        "source_record_order_is_deterministic": source_ids
        == sorted(source_ids, key=lambda value: (value.casefold(), value)),
        "source_record_ids_are_unique_casefolded": len(source_ids)
        == len({value.casefold() for value in source_ids}),
        "provenance_hash_count": sum(len(value) == 64 for value in source_hashes),
        "zero_word_documents": zero_word_documents,
        "zero_sentence_documents": zero_sentence_documents,
        "zero_word_translations": zero_word_translations,
        "entity_head_outside_locus": entity_head_outside_locus,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args(argv)

    report = build_report(args.upstream)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if args.validate:
        failures: list[str] = []
        if report["mismatches"]:
            failures.append(f"count mismatches: {report['mismatches']}")
        if not report["source_record_order_is_deterministic"]:
            failures.append("source record order is not deterministic")
        if not report["source_record_ids_are_unique_casefolded"]:
            failures.append("source record IDs collide case-insensitively")
        if report["provenance_hash_count"] != EXPECTED["document_count"]:
            failures.append("not every document has a SHA-256 provenance hash")
        for key in (
            "zero_word_documents",
            "zero_sentence_documents",
            "zero_word_translations",
            "entity_head_outside_locus",
        ):
            if report[key]:
                failures.append(f"{key}: {report[key]}")
        if failures:
            print("\n".join(failures))
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
