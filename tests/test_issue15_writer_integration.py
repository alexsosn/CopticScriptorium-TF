"""Real-TF acceptance tests: RED contract committed ahead of writer implementation."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tf.fabric import Fabric

from copticscriptorium_tf.graph import build_graph
from copticscriptorium_tf.model import (
    DocumentModel, Entity, LayoutEvent, NormGroup, Orig, Sentence, Translation, Word,
)
from copticscriptorium_tf.writer import write_graph


def _doc(record: str, *, expanded: bool) -> DocumentModel:
    corpus, name = record.split(":", 1)
    dataset = f"{corpus}/{corpus}"
    words = (
        Word(1, "w1", "ⲁ", "lemma1", "N", "root", None, 0, "ab"),
        Word(2, "w2", "ⲃ", "lemma2", "V", "dep", "#w1", 1, "cd"),
    ) if expanded else (Word(1, "w1", "ⲅ", "lemma3", "N", "root", None, 0, "ef"),)
    metadata = {
        "title": name,
        "document_cts_urn": "urn:cts:copticLit:fixture.shared",
        "witness": "MS; cf. urn:cts:copticLit:fixture.shared." if expanded else "",
        "license": "evidence-only",
    }
    return DocumentModel(
        source_record_id=f"{dataset}:{name}",
        source_path=f"{corpus}/{corpus}_TT/{name}.tt",
        source_sha256=("a" if expanded else "b") * 64,
        packaging="directory",
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit="3ac067f1709a0012daf39ea8da2fac79980176a5",
        corpus=corpus,
        dataset=dataset,
        record=name,
        scholarly_id="urn:cts:copticLit:fixture.shared",
        metadata=metadata,
        metadata_duplicates={"title": (name, name)} if expanded else {},
        words=words,
        sentences=(Sentence(1, tuple(range(1, len(words) + 1))),),
        origs=(Orig("ab", (1,), 0),) if expanded else (),
        norm_groups=(NormGroup("ab-cd", (0,), (2,), None),) if expanded else (),
        orig_groups=(),
        layout_events=(
            LayoutEvent(1, "line", "L0", None, None, 0),
            LayoutEvent(2, "line", "L1", 1, 1, 0),
            LayoutEvent(3, "line", "L2", None, None, 1),
        ) if expanded else (),
        entities=(Entity(1, None, "person", "Q123", "#w2", 2, (1, 2)),) if expanded else (),
        translations=(Translation(1, "English ONLY", (1, 2)),) if expanded else (),
        arabic_translations=(Translation(1, "ترجمة عربية", (1,)),) if expanded else (),
        source_text="independent fixture source",
    )


def _graph():
    return build_graph((_doc("beta:b", expanded=False), _doc("alpha:a", expanded=True)))


def _reload(path: Path):
    tf = Fabric(locations=[str(path)], silent="deep")
    api = tf.load(
        "source_record_id scholarly_id norm lemma pos metadata_json metadata_duplicates_json "
        "dependency_head entity_head same_scholarly witness",
        silent="deep",
    )
    if api is False or api is None:
        raise AssertionError("fresh Text-Fabric reload failed")
    return api


class WriterIntegrationTests(unittest.TestCase):
    def test_real_warp_roundtrip_sections_and_source_slot_cardinality(self):
        graph = _graph()
        with TemporaryDirectory() as temporary:
            location = write_graph(graph, Path(temporary) / "corpus")
            for required in ("otype.tf", "oslots.tf", "otext.tf"):
                self.assertTrue((location / required).is_file(), required)
            api = _reload(location)
            self.assertEqual(api.F.otype.maxSlot, len(graph.slots))
            self.assertEqual(api.F.otype.slotType, "word")
            self.assertEqual(api.F.otype.maxNode, len(graph.slots) + len(graph.nodes))
            for document in (node for node in graph.nodes if node.otype == "document"):
                self.assertEqual(
                    api.T.nodeFromSection((document.source_record_id,)), document.id
                )
                self.assertEqual(api.F.scholarly_id.v(document.id), document.scholarly_id)
            self.assertEqual(tuple(api.F.norm.v(slot.id) for slot in graph.slots), ("ⲁ", "ⲃ", "ⲅ"))

    def test_explicit_and_default_text_rendering_never_borrow_foreign_anchor_text(self):
        graph = _graph()
        with TemporaryDirectory() as temporary:
            api = _reload(write_graph(graph, Path(temporary) / "corpus"))
            document = next(n for n in graph.nodes if n.otype == "document" and n.corpus == "alpha")
            translation = next(n for n in graph.nodes if n.otype == "translation")
            arabic = next(n for n in graph.nodes if n.otype == "arabic_translation")
            lines = [n for n in graph.nodes if n.otype == "line"]
            self.assertEqual(api.T.text(document.id, fmt="text-orig-full"), "ⲁ ⲃ ")
            self.assertEqual(api.T.text(translation.id), "English ONLY")
            self.assertEqual(api.T.text(arabic.id), "ترجمة عربية")
            self.assertEqual([api.T.text(n.id) for n in lines], ["a", "b", "cd"])
            self.assertNotIn("English ONLY", api.T.text(document.id, fmt="text-orig-full"))
            self.assertNotIn("ab", api.T.text(document.id, fmt="text-orig-full"))

    def test_dependency_entity_and_document_relation_edges_survive_reload(self):
        graph = _graph()
        with TemporaryDirectory() as temporary:
            api = _reload(write_graph(graph, Path(temporary) / "corpus"))
            for edge in graph.edges:
                if edge.kind in {"dependency_head", "entity_head"}:
                    self.assertIn(edge.target, api.E.__getattribute__(edge.kind).f(edge.source))
                elif edge.kind == "same_scholarly":
                    # TF 13.1.0 valued-edge .f(source) returns ((target, value), ...).
                    self.assertIn((edge.target, edge.classification), api.E.same_scholarly.f(edge.source))
                elif edge.kind == "witness":
                    evidence = dict(api.E.witness.f(edge.source))[edge.target]
                    self.assertEqual(json.loads(evidence), {
                        "witness_literal": edge.witness_literal,
                        "target_scholarly_id": edge.target_scholarly_id,
                    })
            entity = next(node for node in graph.nodes if node.otype == "entity")
            head = next(edge.target for edge in graph.edges if edge.kind == "entity_head")
            self.assertIn(head, entity.slots)
            self.assertEqual(api.F.pos.v(graph.slots[1].id), "V")
            physical_docs = [node for node in graph.nodes if node.otype == "document"]
            self.assertEqual(len({api.F.source_record_id.v(d.id) for d in physical_docs}), 2)
            self.assertEqual(len({api.F.scholarly_id.v(d.id) for d in physical_docs}), 1)

    def test_structured_metadata_and_deterministic_file_bytes(self):
        graph = _graph()
        with TemporaryDirectory() as first_dir, TemporaryDirectory() as second_dir:
            one = write_graph(graph, Path(first_dir) / "corpus")
            two = write_graph(graph, Path(second_dir) / "corpus")
            first = {p.name: p.read_bytes() for p in one.glob("*.tf")}
            second = {p.name: p.read_bytes() for p in two.glob("*.tf")}
            self.assertTrue(first)
            self.assertEqual(first, second)
            api = _reload(one)
            document = next(n for n in graph.nodes if n.otype == "document" and n.corpus == "alpha")
            self.assertIn('"license":"evidence-only"', api.F.metadata_json.v(document.id))
            self.assertIn('"title"', api.F.metadata_duplicates_json.v(document.id))

    def test_graph_validation_fails_before_any_final_output_is_published(self):
        graph = _graph()
        translation = next(n for n in graph.nodes if n.otype == "translation")
        damaged = replace(
            graph,
            nodes=tuple(replace(n, slot_ranges=()) if n.id == translation.id else n for n in graph.nodes),
        )
        with TemporaryDirectory() as temporary:
            destination = Path(temporary) / "corpus"
            with self.assertRaisesRegex(ValueError, "(translation|locus|validation)"):
                write_graph(damaged, destination)
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
