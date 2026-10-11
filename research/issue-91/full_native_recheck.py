"""Check complete regenerated Coptic TF against every pinned SBL source occurrence.

Run *after* the existing issue-16 full conversion smoke. Does not save,
publish, or archive Greek/Coptic corpus text. Returns counts and SHA256 only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from copticscriptorium_tf.sbl_validation import (
    PINNED_COMMIT, compare_source_to_tf,
)


def verify_upstream(root: Path) -> None:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    )
    if result.stdout.strip() != PINNED_COMMIT:
        raise ValueError("incorrect pinned Coptic source commit")
    # Reject accidental changes to TT source files while preserving harmless
    # untracked build logs in the separate work directory.
    dirty = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--",
         ":(glob)*/*_TT/**", ":(glob)*/*_TT.zip"],
        capture_output=True, text=True, check=True,
    )
    if dirty.stdout.strip():
        raise ValueError("pinned Coptic source TT checkout is dirty")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", type=Path)
    parser.add_argument("--tf-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    verify_upstream(args.source_root)
    result = compare_source_to_tf(args.source_root, args.tf_dir)
    result["source_revision_verified"] = True
    payload = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
