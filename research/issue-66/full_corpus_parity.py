"""Issue #66 pinned full-corpus CoNLL-U supplementation parity gate.

Converts the complete pinned source tree with the public converter, reloads the
generated Text-Fabric, and then rereads every CoNLL-U source record with a
separate minimal reader (deliberately not ``copticscriptorium_tf.conllu``). Every
supplemented word's UD values and heads are compared against reloaded TF.

This checks converter behaviour. It does not certify upstream annotations.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import shutil
import sys
from time import monotonic
import zipfile

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from copticscriptorium_tf.converter import convert_source_tree

UPSTREAM_REPOSITORY = "CopticScriptorium/corpora"
UPSTREAM_COMMIT = "3ac067f1709a0012daf39ea8da2fac79980176a5"
# Reviewed #1/#13 measurements for the pinned revision.
EXPECTED_STATUSES = {"supplemented": 2361, "placeholder": 227, "malformed_conllu": 40}
EXPECTED_SUPPLEMENTED_WORDS = 2104966
EXPECTED_TT_ABSENT_HEADS = 52773
FIXED_UD_FEATURES = ("ud_lemma", "ud_upos", "ud_xpos", "ud_deprel")


def _read_source(source_root: Path, source_path: str) -> str:
    if "!/" in source_path:
        archive, member = source_path.split("!/", 1)
        with zipfile.ZipFile(source_root / archive) as handle:
            return handle.read(member).decode("utf-8")
    return (source_root / source_path).read_text(encoding="utf-8")


def _independent_rows(text: str) -> list[dict[str, object]]:
    """Basic-word rows with document-absolute heads, read without the converter."""
    rows: list[dict[str, object]] = []
    offset = 0
    sentence_size = 0
    for line in text.splitlines():
        if not line.strip():
            offset += sentence_size
            sentence_size = 0
            continue
        if line.startswith("#"):
            continue
        columns = line.split("\t")
        if not columns[0].isdigit():
            continue  # multiword-token ranges are not supplemented
        sentence_size += 1
        local_head = int(columns[6])

        def pairs(value: str) -> dict[str, str]:
            if value in ("", "_"):
                return {}
            return dict(item.split("=", 1) for item in value.split("|"))

        rows.append({
            "ud_lemma": None if columns[2] == "_" else columns[2],
            "ud_upos": None if columns[3] == "_" else columns[3],
            "ud_xpos": None if columns[4] == "_" else columns[4],
            "ud_deprel": None if columns[7] == "_" else columns[7],
            "head": 0 if local_head == 0 else offset + local_head,
            "feat": pairs(columns[5]),
            "misc": pairs(columns[9]),
        })
    return rows


def _source_keys(tf_dir: Path, prefix: str) -> dict[str, str]:
    """Map each per-key feature to the literal key recorded in its TF header."""
    result: dict[str, str] = {}
    for path in sorted(tf_dir.glob(f"{prefix}*.tf")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("@"):
                break
            if line.startswith("@sourceKey="):
                result[path.stem] = line[len("@sourceKey="):]
    return result


def run(source_root: Path, work_root: Path) -> dict[str, object]:
    from tf.core.timestamp import DEEP
    from tf.fabric import Fabric

    if work_root.exists():
        shutil.rmtree(work_root)
    work_root.mkdir(parents=True)
    tf_dir = work_root / "tf"
    started = monotonic()
    result = convert_source_tree(
        source_root,
        tf_dir,
        upstream_repository=UPSTREAM_REPOSITORY,
        upstream_commit=UPSTREAM_COMMIT,
    )
    convert_seconds = monotonic() - started

    feat_keys = _source_keys(tf_dir, "ud_feat_")
    misc_keys = _source_keys(tf_dir, "ud_misc_")
    features = [
        "source_record_id", "conllu_status", "conllu_source_path",
        "dependency_head_ordinal", "ud_head_ordinal", "ud_head",
        *FIXED_UD_FEATURES, *feat_keys, *misc_keys,
    ]
    api = Fabric(locations=str(tf_dir), silent=DEEP).load(" ".join(features), silent=DEEP)
    if not api:
        raise RuntimeError("fresh Text-Fabric reload failed")
    F, E, L = api.F, api.E, api.L

    failures: list[str] = []
    statuses: Counter[str] = Counter()
    supplemented_words = 0
    tt_absent_heads = 0
    ud_head_edges = 0

    def fail(message: str) -> None:
        if len(failures) < 50:
            failures.append(message)

    for document in F.otype.s("document"):
        record = F.source_record_id.v(document)
        status = F.conllu_status.v(document)
        statuses[status] += 1
        words = L.d(document, otype="word")
        if status != "supplemented":
            for word in words:
                if F.ud_upos.v(word) is not None or E.ud_head.f(word):
                    fail(f"{record}: non-supplemented document carries UD values")
                    break
            continue

        rows = _independent_rows(_read_source(source_root, F.conllu_source_path.v(document)))
        if len(rows) != len(words):
            fail(f"{record}: {len(rows)} CoNLL-U words versus {len(words)} TF words")
            continue
        first = words[0]
        for word, row in zip(words, rows):
            supplemented_words += 1
            for name in FIXED_UD_FEATURES:
                if getattr(F, name).v(word) != row[name]:
                    fail(f"{record} word {word}: {name} differs")
            if F.ud_head_ordinal.v(word) != row["head"]:
                fail(f"{record} word {word}: ud_head_ordinal differs")
            expected_edge = () if row["head"] == 0 else (first + row["head"] - 1,)
            if tuple(E.ud_head.f(word)) != expected_edge:
                fail(f"{record} word {word}: ud_head edge differs")
            ud_head_edges += len(expected_edge)
            if F.dependency_head_ordinal.v(word) is None:
                tt_absent_heads += 1
            for field, keys in (("feat", feat_keys), ("misc", misc_keys)):
                observed = {
                    key: getattr(F, feature).v(word)
                    for feature, key in keys.items()
                    if getattr(F, feature).v(word) is not None
                }
                if observed != row[field]:
                    fail(f"{record} word {word}: {field} values differ")

    if dict(statuses) != EXPECTED_STATUSES:
        fail(f"statuses: expected {EXPECTED_STATUSES}, measured {dict(statuses)}")
    if supplemented_words != EXPECTED_SUPPLEMENTED_WORDS:
        fail(f"supplemented words: expected {EXPECTED_SUPPLEMENTED_WORDS}, measured {supplemented_words}")
    if tt_absent_heads != EXPECTED_TT_ABSENT_HEADS:
        fail(f"TT-absent heads: expected {EXPECTED_TT_ABSENT_HEADS}, measured {tt_absent_heads}")
    if result.conllu_missing_source_records or result.conllu_records_without_tt:
        fail("unexpected missing or orphan CoNLL-U records on the pinned revision")
    if result.conllu_supplemented_source_records != EXPECTED_STATUSES["supplemented"]:
        fail("summary supplemented count disagrees with TF")

    report = result.to_dict()
    report.update({
        "upstream_repository": UPSTREAM_REPOSITORY,
        "upstream_commit": UPSTREAM_COMMIT,
        "convert_seconds": round(convert_seconds, 3),
        "conllu_statuses": dict(sorted(statuses.items())),
        "supplemented_words": supplemented_words,
        "tt_absent_heads_supplied_by_conllu": tt_absent_heads,
        "ud_head_edges": ud_head_edges,
        "ud_feat_keys": sorted(feat_keys.values()),
        "ud_misc_keys": sorted(misc_keys.values()),
        "failures": failures,
        "purpose": "converter parity regression; not corpus certification",
    })
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", type=Path)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    report = run(args.source_root, args.work_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {key: report[key] for key in (
        "conllu_statuses", "supplemented_words", "tt_absent_heads_supplied_by_conllu",
        "ud_head_edges", "peak_rss_mb", "convert_seconds", "tf_files", "tf_bytes",
    )}
    print(json.dumps(summary, sort_keys=True))
    if report["failures"]:
        print("\n".join(report["failures"]), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
