"""Pinned real-source smoke for the issue #59 executable query cookbook.

This checks cookbook behavior against a bounded upstream TT directory/ZIP slice.
It is converter/documentation regression evidence, not scholarly certification.
"""
from __future__ import annotations

import argparse
import importlib.util
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


UPSTREAM = "CopticScriptorium/corpora"
COMMIT = "3ac067f1709a0012daf39ea8da2fac79980176a5"
DIRECT = ("Mark_01.tt", "Mark_02.tt")
ARCHIVE_RECORD = "41_Mark_01.tt"


def _load_cookbook():
    path = ROOT / "examples" / "query_cookbook.py"
    spec = importlib.util.spec_from_file_location("query_cookbook_real_smoke", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import cookbook from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
        members = [
            member
            for member in archive.namelist()
            if member.rsplit("/", 1)[-1] == ARCHIVE_RECORD
        ]
        if len(members) != 1:
            raise AssertionError(
                f"expected one {ARCHIVE_RECORD} archive member, found {members!r}"
            )
        member = members[0]
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


def run(root: Path) -> dict[str, object]:
    documents = _documents(root)
    graph = build_graph(documents, document_relations=())
    if len(graph.slots) < 1000:
        raise AssertionError(f"real-source slice unexpectedly small: {len(graph.slots)}")

    lexical = next(
        (slot for slot in graph.slots if slot.lemma and slot.source_id),
        None,
    )
    if lexical is None:
        raise AssertionError("pinned real slice contains no word with lemma/source_id")

    morph = next(
        (
            slot
            for slot in graph.slots
            if slot.pos and slot.func and slot.source_id
        ),
        None,
    )
    if morph is None:
        raise AssertionError("pinned real slice contains no POS/function annotation")

    dependency = next(
        (edge for edge in graph.edges if edge.kind == "dependency_head"),
        None,
    )
    if dependency is None:
        raise AssertionError("pinned real slice contains no dependency edge")

    archive_record = "sahidica.nt/sahidica.nt:41_Mark_01"

    cookbook = _load_cookbook()
    with TemporaryDirectory() as temporary:
        location = write_graph(graph, Path(temporary) / "tf")
        api = cookbook.load_generated_tf(location)

        lemma_rows = cookbook.lemma_hits(api, lexical.lemma)
        lemma_nodes = {row[0] for row in lemma_rows}
        if lexical.id not in lemma_nodes:
            raise AssertionError(
                f"real lemma lookup lost source word {lexical.source_id!r}"
            )

        morph_rows = cookbook.morphology_hits(
            api,
            pos=morph.pos,
            func=morph.func,
        )
        if morph.id not in {row[0] for row in morph_rows}:
            raise AssertionError(
                f"real morphology lookup lost source word {morph.source_id!r}"
            )

        dependency_rows = set(cookbook.dependency_pairs(api))
        expected_dependency = (dependency.source, dependency.target)
        if expected_dependency not in dependency_rows:
            raise AssertionError(
                f"real dependency query lost edge {expected_dependency!r}"
            )

        archive_node = api.T.nodeFromSection((archive_record,))
        if archive_node is None:
            raise AssertionError(f"physical section did not resolve: {archive_record}")

        rendered = cookbook.render_document(api, archive_node)
        normalized = rendered["normalized"]
        diplomatic = rendered["diplomatic"]
        if not normalized or not diplomatic or normalized == diplomatic:
            raise AssertionError("real normalized/diplomatic cookbook rendering failed")

        provenance = cookbook.trace_provenance(api, lexical.id)
        if provenance["source_record_id"] != lexical.source_record_id:
            raise AssertionError("real provenance resolved the wrong physical record")
        if provenance["upstream_repository"] != UPSTREAM:
            raise AssertionError("real provenance lost upstream repository")
        if provenance["upstream_commit"] != COMMIT:
            raise AssertionError("real provenance lost pinned upstream commit")
        if not provenance["source_sha256"]:
            raise AssertionError("real provenance lost source SHA-256")

        docs = cookbook.document_hits(api, corpus="sahidica.mark")
        if not docs:
            raise AssertionError("real corpus filter returned no sahidica.mark documents")

        translations = cookbook.translation_texts(api)
        if set(translations) != {"translation", "arabic_translation"}:
            raise AssertionError("translation recipe returned unexpected result shape")

        return {
            "source_records": len(documents),
            "source_words": len(graph.slots),
            "lemma": lexical.lemma,
            "lemma_hits": len(lemma_rows),
            "morphology_hits": len(morph_rows),
            "dependency_pairs": len(dependency_rows),
            "physical_section": archive_record,
            "normalized_chars": len(normalized),
            "diplomatic_chars": len(diplomatic),
            "provenance_source_record_id": provenance["source_record_id"],
            "translation_nodes": {
                key: len(value) for key, value in translations.items()
            },
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = run(args.upstream)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
