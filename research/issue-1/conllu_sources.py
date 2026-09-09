"""Shared source iterator for directory- and archive-packaged CoNLL-U records."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator
import zipfile


def _direct_records(root: Path) -> Iterator[dict[str, Any]]:
    for directory in sorted(
        (path for path in root.rglob("*_CONLLU") if path.is_dir()),
        key=lambda path: path.as_posix(),
    ):
        relative_dir = directory.relative_to(root)
        parts = relative_dir.parts
        if len(parts) != 2 or not parts[1].endswith("_CONLLU"):
            continue
        corpus = parts[0]
        dataset_name = parts[1][:-7]
        dataset = f"{corpus}/{dataset_name}"
        for path in sorted(directory.rglob("*.conllu"), key=lambda item: item.as_posix()):
            relative_record = path.relative_to(directory).as_posix()
            yield {
                "dataset": dataset,
                "record": relative_record[:-7],
                "source": path.relative_to(root).as_posix(),
                "packaging": "directory",
                "text": path.read_text(encoding="utf-8"),
            }


def _archive_records(root: Path) -> Iterator[dict[str, Any]]:
    for archive_path in sorted(root.rglob("*_CONLLU.zip"), key=lambda path: path.as_posix()):
        relative = archive_path.relative_to(root)
        parts = relative.parts
        if len(parts) != 2 or not parts[1].endswith("_CONLLU.zip"):
            continue
        corpus = parts[0]
        dataset_name = parts[1][:-11]
        dataset = f"{corpus}/{dataset_name}"
        expected_prefix = f"{dataset_name}_CONLLU/"
        found = False
        with zipfile.ZipFile(archive_path) as archive:
            for member in sorted(archive.namelist()):
                if member.endswith("/") or not member.lower().endswith(".conllu"):
                    continue
                found = True
                if "/" not in member:
                    logical = member
                elif member.startswith(expected_prefix):
                    logical = member[len(expected_prefix):]
                    if not logical or "/" in logical:
                        raise ValueError(
                            f"unsupported CoNLL-U archive member layout in {relative.as_posix()}: {member!r}"
                        )
                else:
                    raise ValueError(
                        f"unsupported CoNLL-U archive member layout in {relative.as_posix()}: "
                        f"{member!r} is neither root-level nor under {expected_prefix!r}"
                    )
                yield {
                    "dataset": dataset,
                    "record": logical[:-7],
                    "source": f"{relative.as_posix()}!/{member}",
                    "packaging": "archive",
                    "text": archive.read(member).decode("utf-8"),
                }
        if not found:
            raise ValueError(f"CoNLL-U archive contains no .conllu members: {relative.as_posix()}")


def iter_conllu_records(root: Path | str) -> Iterator[dict[str, Any]]:
    """Yield every supported CoNLL-U source record with stable logical identity."""

    root_path = Path(root)
    yield from _direct_records(root_path)
    yield from _archive_records(root_path)
