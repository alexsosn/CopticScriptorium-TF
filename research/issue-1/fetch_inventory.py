"""Fetch a complete Coptic Scriptorium Git-tree census and run issue #1 inventory.

The transport avoids one giant ``recursive=1`` request at repository root.  Instead it
loads the root tree non-recursively and requests each top-level subtree recursively,
rejecting any truncated response.  This makes source coverage explicit and testable.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.request import Request, urlopen


JsonFetcher = Callable[[str], dict[str, Any]]
API_ROOT = "https://api.github.com"


def assemble_complete_tree(
    root_payload: dict[str, Any],
    subtree_payloads: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Combine a non-recursive root tree with recursive top-level subtrees."""

    if root_payload.get("truncated"):
        raise ValueError("root Git tree response is truncated")
    root_entries = root_payload.get("tree")
    if not isinstance(root_entries, list):
        raise ValueError("root Git tree response has no tree list")

    combined: list[dict[str, Any]] = []

    for entry in sorted(root_entries, key=lambda item: str(item.get("path", ""))):
        path = entry.get("path")
        entry_type = entry.get("type")
        if not isinstance(path, str):
            raise ValueError("root Git tree entry has no string path")

        combined.append(dict(entry))
        if entry_type != "tree":
            continue

        subtree = subtree_payloads.get(path)
        if subtree is None:
            raise ValueError(f"missing subtree payload for {path}")
        if subtree.get("truncated"):
            raise ValueError(f"subtree {path} Git tree response is truncated")
        subtree_entries = subtree.get("tree")
        if not isinstance(subtree_entries, list):
            raise ValueError(f"subtree {path} Git tree response has no tree list")

        for child in subtree_entries:
            child_path = child.get("path")
            if not isinstance(child_path, str):
                raise ValueError(f"subtree {path} contains an entry without a string path")
            prefixed = dict(child)
            prefixed["path"] = f"{path}/{child_path}"
            combined.append(prefixed)

    combined.sort(key=lambda item: str(item.get("path", "")))
    return {
        "sha": str(root_payload.get("sha", "")),
        "truncated": False,
        "tree": combined,
    }


def collect_complete_tree(
    repository: str,
    commit: str,
    *,
    fetch_json: JsonFetcher,
) -> dict[str, Any]:
    """Fetch one complete repository tree at an immutable commit."""

    if repository.count("/") != 1:
        raise ValueError("repository must be in owner/name form")

    base = f"/repos/{repository}"
    commit_payload = fetch_json(f"{base}/git/commits/{commit}")
    tree_info = commit_payload.get("tree")
    if not isinstance(tree_info, dict) or not tree_info.get("sha"):
        raise ValueError("commit response does not contain a root tree SHA")
    root_sha = str(tree_info["sha"])

    root_payload = fetch_json(f"{base}/git/trees/{root_sha}")
    root_entries = root_payload.get("tree")
    if not isinstance(root_entries, list):
        raise ValueError("root Git tree response has no tree list")

    subtrees: dict[str, dict[str, Any]] = {}
    for entry in sorted(root_entries, key=lambda item: str(item.get("path", ""))):
        if entry.get("type") != "tree":
            continue
        path = entry.get("path")
        sha = entry.get("sha")
        if not isinstance(path, str) or not sha:
            raise ValueError("top-level tree entry is missing path or SHA")
        subtrees[path] = fetch_json(f"{base}/git/trees/{sha}?recursive=1")

    return assemble_complete_tree(root_payload, subtrees)


def github_fetch_json(path: str) -> dict[str, Any]:
    """Fetch JSON from one GitHub API relative path using optional ``GITHUB_TOKEN``."""

    if not path.startswith("/"):
        raise ValueError("GitHub API path must be absolute")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "CopticScriptorium-TF-source-inventory",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(f"{API_ROOT}{path}", headers=headers)
    try:
        with urlopen(request, timeout=60) as response:
            payload = json.load(response)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {exc.code} for {path}: {detail}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError(f"GitHub API response for {path} is not a JSON object")
    return payload


def _load_inventory_module():
    module_path = Path(__file__).with_name("inventory.py")
    spec = importlib.util.spec_from_file_location("issue1_inventory", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load inventory module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default="CopticScriptorium/corpora")
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, required=True, help="inventory JSON output")
    parser.add_argument(
        "--tree-output",
        type=Path,
        help="optional complete assembled Git-tree JSON for audit/debugging",
    )
    args = parser.parse_args(argv)

    complete_tree = collect_complete_tree(
        args.repository,
        args.commit,
        fetch_json=github_fetch_json,
    )
    inventory = _load_inventory_module()
    report = inventory.analyze_tree(complete_tree)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(inventory.render_report_json(report), encoding="utf-8")

    if args.tree_output is not None:
        args.tree_output.parent.mkdir(parents=True, exist_ok=True)
        args.tree_output.write_text(
            json.dumps(complete_tree, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    summary = {
        "repository": args.repository,
        "commit": args.commit,
        "tree_sha": report["tree_sha"],
        "top_level_corpora": len(report["top_level_corpora"]),
        "datasets": len(report["datasets"]),
        "zero_byte_blobs": len(report["zero_byte_blobs"]),
        "meta_json": report["meta_json"],
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
