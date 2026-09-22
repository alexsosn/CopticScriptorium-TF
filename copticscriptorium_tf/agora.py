"""Thin offline adapter for Agora's explicitly approved materializer host.

Agora provides an existing, empty private output directory and controls source
acquisition, sandboxing, runtime approval, and final artifact publication. The
converter itself requires a nonexistent destination, so its native TF dataset
lives in the ``tf`` child of the output directory.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

from .converter import convert_source_tree

_UPSTREAM_REPOSITORY = "CopticScriptorium/corpora"
_LOCAL_UNVERSIONED = "unversioned-local"
_GIT_REVISION_RE = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")


def materialize(source: Path, output: Path, *, source_revision: str) -> Path:
    """Convert into Agora's private staging root; return its relative TF child.

    ``source_revision`` is populated by Agora when the input is a Git checkout.
    For a user-local directory without Git metadata, its absence is explicit;
    Agora separately records the local tree hash, and TF retains per-record hashes.
    """
    if output.is_symlink() or not output.is_dir():
        raise ValueError("Agora output must be an existing, non-symlink directory")
    if any(output.iterdir()):
        raise ValueError("Agora output directory must be empty before conversion")
    if source_revision and _GIT_REVISION_RE.fullmatch(source_revision) is None:
        raise ValueError("Agora source revision must be a full Git commit hash or empty")

    revision = source_revision or _LOCAL_UNVERSIONED
    result = convert_source_tree(
        source,
        output / "tf",
        upstream_repository=_UPSTREAM_REPOSITORY,
        upstream_commit=revision,
    )
    summary = result.to_dict()
    # Agora renames its staging root after successful validation. Never publish
    # the ephemeral sandbox's absolute output pathname into the run report.
    summary["output_path"] = "tf"
    summary["upstream_repository"] = _UPSTREAM_REPOSITORY
    summary["upstream_commit"] = revision
    (output / "conversion-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return output / "tf"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert Coptic Scriptorium sources inside Agora's private output workspace."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args(argv)
    try:
        materialize(args.source, args.output, source_revision=args.source_revision)
    except Exception as exc:
        print(f"Agora Coptic materialization failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
