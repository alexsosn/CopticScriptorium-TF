"""Pinned real-source Text-Fabric web-app smoke for issue #58.

This is a converter/browser regression on a bounded upstream slice. It does not
certify upstream Coptic Scriptorium annotations or corpus completeness.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import zipfile

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from copticscriptorium_tf.graph import build_graph
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.writer import write_graph
from tf.app import use
from tf.browser.web import setup as setup_browser
from tf.fabric import Fabric


UPSTREAM = "CopticScriptorium/corpora"
COMMIT = "3ac067f1709a0012daf39ea8da2fac79980176a5"
DIRECT = ("Mark_01.tt", "Mark_02.tt")
ARCHIVE_RECORD = "41_Mark_01.tt"


def _documents(root: Path):
    documents = []
    for filename in DIRECT:
        relative = Path("sahidica.mark/sahidica.mark_TT") / filename
        documents.append(
            parse_tt_record(
                (root / relative).read_bytes(),
                source_record_id=f"sahidica.mark/sahidica.mark:{filename[:-3]}",
                source_path=relative.as_posix(),
                upstream_repository=UPSTREAM,
                upstream_commit=COMMIT,
                packaging="directory",
            )
        )

    archive_relative = Path("sahidica.nt/sahidica.nt_TT.zip")
    with zipfile.ZipFile(root / archive_relative) as archive:
        matches = [
            member
            for member in archive.namelist()
            if member.rsplit("/", 1)[-1] == ARCHIVE_RECORD
        ]
        if len(matches) != 1:
            raise AssertionError(
                f"expected one {ARCHIVE_RECORD} member, found {matches!r}"
            )
        member = matches[0]
        documents.append(
            parse_tt_record(
                archive.read(member),
                source_record_id="sahidica.nt/sahidica.nt:41_Mark_01",
                source_path=f"{archive_relative.as_posix()}!/{member}",
                upstream_repository=UPSTREAM,
                upstream_commit=COMMIT,
                packaging="archive",
            )
        )
    return tuple(documents)


def run(root: Path, app_dir: Path) -> dict[str, object]:
    documents = _documents(root)
    source_words = sum(len(document.words) for document in documents)
    if source_words < 1000:
        raise AssertionError(f"real-source slice unexpectedly small: {source_words}")

    # The bounded slice intentionally lacks external witness targets. Relation
    # derivation is therefore disabled here exactly as in the issue #15 writer
    # slice; relation semantics are covered by focused complete fixtures.
    graph = build_graph(documents, document_relations=())

    with TemporaryDirectory() as temporary:
        location = write_graph(graph, Path(temporary) / "tf")
        app = use(
            f"app:{app_dir}",
            locations=[str(location)],
            modules=["."],
            silent="deep",
        )
        if app is None or app.api is None:
            raise AssertionError("real generated TF did not load through local app")
        api = app.api

        archive_id = "sahidica.nt/sahidica.nt:41_Mark_01"
        archive_node = api.T.nodeFromSection((archive_id,))
        if archive_node is None:
            raise AssertionError(f"physical section did not resolve: {archive_id}")

        normalized = api.T.text(archive_node, fmt="text-orig-full")
        diplomatic = api.T.text(archive_node, fmt="text-diplomatic-full")
        if not normalized.strip() or not diplomatic.strip():
            raise AssertionError("real normalized/diplomatic browser text is empty")
        if normalized == diplomatic:
            raise AssertionError("real diplomatic view collapsed to normalized text")

        results = app.search("word", silent="deep", limit=5)
        if len(results) != 5 or any(len(result) != 1 for result in results):
            raise AssertionError(f"unexpected representative search results: {results!r}")

        if not any(api.F.lemma.v(result[0]) for result in results):
            # The first five words are expected to carry lexical annotation in
            # this pinned fixture; detect accidental feature-loading regressions.
            raise AssertionError("representative real search did not expose lemmas")

        browser = setup_browser(
            False,
            f"app:{app_dir}",
            f"--locations={location}",
            "--modules=.",
        )
        if browser is None:
            raise AssertionError("real generated TF did not construct the browser app")
        if "/query" not in {rule.rule for rule in browser.url_map.iter_rules()}:
            raise AssertionError("real generated TF browser lacks /query route")
        query_response = browser.test_client().get("/query")
        if query_response.status_code != 200:
            raise AssertionError(
                f"real generated TF /query returned {query_response.status_code}"
            )

        vanilla = Fabric(locations=[str(location)], silent="deep").load(
            "source_record_id lemma pos dependency_head",
            silent="deep",
        )
        if not vanilla:
            raise AssertionError("generated TF no longer loads independently of the app")

        return {
            "source_records": len(documents),
            "source_words": source_words,
            "tf_slots": api.F.otype.maxSlot,
            "tf_nodes": api.F.otype.maxNode,
            "physical_section": archive_id,
            "normalized_chars": len(normalized),
            "diplomatic_chars": len(diplomatic),
            "representative_search_results": len(results),
            "browser_query_status": query_response.status_code,
            "app_path": str(app_dir),
            "relations_policy": (
                "omitted from bounded slice because external witness targets are absent"
            ),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = run(args.upstream, args.app.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
