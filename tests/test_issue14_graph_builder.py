from __future__ import annotations

from dataclasses import replace
import unittest

from copticscriptorium_tf.graph import (
    DocumentRelation,
    build_graph,
    graph_fingerprint,
    validate_graph,
)
from copticscriptorium_tf.model import (
    DocumentModel,
    Entity,
    LayoutEvent,
    NormGroup,
    Orig,
    OrigGroup,
    Sentence,
    Translation,
    Word,
)


def _word(ordinal: int, text: str, *, head: int | None = None, func: str | None = None) -> Word:
    return Word(
        ordinal=ordinal,
        source_id=f"w{ordinal}",
        norm=text.upper(),
        lemma=f"lemma-{ordinal}",
        pos="N",
        func=func,
        head_literal=(f"#w{head}" if head and head > 0 else None),
        dependency_head_ordinal=head,
        source_text=text,
    )


def _doc(
    source_record_id: str,
    *,
    scholarly_id: str | None = "urn:cts:copticLit:test.work",
    words: tuple[Word, ...] | None = None,
    sentences: tuple[Sentence, ...] | None = None,
    origs: tuple[Orig, ...] = (),
    norm_groups: tuple[NormGroup, ...] = (),
    orig_groups: tuple[OrigGroup, ...] = (),
    layout_events: tuple[LayoutEvent, ...] = (),
    entities: tuple[Entity, ...] = (),
    translations: tuple[Translation, ...] = (),
    arabic_translations: tuple[Translation, ...] = (),
) -> DocumentModel:
    if words is None:
        words = (_word(1, "a", head=0, func="root"),)
    if sentences is None:
        sentences = (Sentence(1, tuple(word.ordinal for word in words)),)
    prefix, record = source_record_id.split(":", 1)
    corpus, dataset = prefix.split("/", 1)
    metadata = {"title": record}
    if scholarly_id:
        metadata["document_cts_urn"] = scholarly_id
    return DocumentModel(
        source_record_id=source_record_id,
        source_path=f"{corpus}/{dataset}_TT/{record}.tt",
        source_sha256="a" * 64,
        packaging="directory",
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit="3ac067f1709a0012daf39ea8da2fac79980176a5",
        corpus=corpus,
        dataset=dataset,
        record=record,
        scholarly_id=scholarly_id,
        metadata=metadata,
        metadata_duplicates={},
        words=words,
        sentences=sentences,
        origs=origs,
        norm_groups=norm_groups,
        orig_groups=orig_groups,
        layout_events=layout_events,
        entities=entities,
        translations=translations,
        arabic_translations=arabic_translations,
        source_text="fixture",
    )


class GraphBuilderTests(unittest.TestCase):
    def test_one_source_word_is_one_slot_and_group_shapes_are_preserved(self) -> None:
        words = (
            _word(1, "a", head=0, func="root"),
            _word(2, "b", head=1, func="dep"),
            _word(3, "c", head=1, func="dep"),
            _word(4, "d", head=3, func="dep"),
        )
        document = _doc(
            "alpha/sample:doc",
            words=words,
            origs=(Orig("A", (1,), 0), Orig("B", (2,), 0)),
            norm_groups=(
                NormGroup("AB", (0, 1), (), 0),
                NormGroup("CD", (), (3, 4), None),
            ),
            orig_groups=(OrigGroup("AB", (0,)),),
        )

        graph = build_graph([document])

        self.assertEqual([slot.id for slot in graph.slots], [1, 2, 3, 4])
        self.assertEqual([slot.source_word_ordinal for slot in graph.slots], [1, 2, 3, 4])
        self.assertTrue(all(slot.kind == "word" for slot in graph.slots))
        self.assertEqual(graph.section_types, ("document",))
        self.assertEqual(validate_graph(graph), ())

        documents = [node for node in graph.nodes if node.otype == "document"]
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0].slots, (1, 2, 3, 4))
        self.assertEqual(documents[0].section_address, ("alpha/sample:doc",))

        orig_groups = [node for node in graph.nodes if node.otype == "orig_group"]
        norm_groups = [node for node in graph.nodes if node.otype == "norm_group"]
        origs = [node for node in graph.nodes if node.otype == "orig"]
        self.assertEqual(len(orig_groups), 1)
        self.assertEqual(len(norm_groups), 2)
        self.assertEqual(len(origs), 2)
        self.assertEqual(norm_groups[0].parent_node_id, orig_groups[0].id)
        self.assertEqual(origs[0].parent_node_id, norm_groups[0].id)
        self.assertEqual(origs[1].parent_node_id, norm_groups[0].id)
        self.assertEqual(norm_groups[1].parent_node_id, None)
        self.assertEqual(norm_groups[1].direct_word_slots, (3, 4))
        self.assertEqual(origs[0].slots, (1,))
        self.assertEqual(origs[1].slots, (2,))

        previous_end = len(graph.slots)
        for node_range in graph.node_ranges:
            self.assertEqual(node_range.start, previous_end + 1)
            self.assertEqual(node_range.end - node_range.start + 1, node_range.count)
            previous_end = node_range.end

    def test_input_order_and_repeated_scholarly_identity_do_not_change_graph(self) -> None:
        first = _doc("zeta/sample:copy-b", scholarly_id="urn:cts:copticLit:same.work")
        second = _doc("alpha/sample:copy-a", scholarly_id="urn:cts:copticLit:same.work")

        graph_a = build_graph([first, second])
        graph_b = build_graph([second, first])

        self.assertEqual(graph_fingerprint(graph_a), graph_fingerprint(graph_b))
        documents = [node for node in graph_a.nodes if node.otype == "document"]
        self.assertEqual(
            [node.source_record_id for node in documents],
            ["alpha/sample:copy-a", "zeta/sample:copy-b"],
        )
        self.assertEqual(len({node.id for node in documents}), 2)
        self.assertEqual(len({node.section_address for node in documents}), 2)
        self.assertEqual({node.scholarly_id for node in documents}, {"urn:cts:copticLit:same.work"})

    def test_dependency_and_entity_edges_are_document_local_and_nested_entities_survive(self) -> None:
        words = (
            _word(1, "a", head=0, func="root"),
            _word(2, "b", head=1, func="dep"),
            _word(3, "c", head=2, func="dep"),
        )
        entities = (
            Entity(1, None, "person", "Q1", "#w2", 2, (1, 2, 3)),
            Entity(2, 1, "place", "Q2", "#w2", 2, (2,)),
        )
        graph = build_graph([_doc("alpha/sample:entities", words=words, entities=entities)])

        entity_nodes = [node for node in graph.nodes if node.otype == "entity"]
        self.assertEqual(len(entity_nodes), 2)
        self.assertEqual(entity_nodes[1].parent_node_id, entity_nodes[0].id)
        entity_heads = [edge for edge in graph.edges if edge.kind == "entity_head"]
        self.assertEqual(len(entity_heads), 2)
        self.assertTrue(all(edge.target in set(entity_nodes[i].slots) for i, edge in enumerate(entity_heads)))
        dependencies = [edge for edge in graph.edges if edge.kind == "dependency_head"]
        self.assertEqual([(edge.source, edge.target) for edge in dependencies], [(2, 1), (3, 2)])
        self.assertEqual(validate_graph(graph), ())

    def test_invalid_dependency_entity_and_zero_word_translation_fail_closed(self) -> None:
        bad_dependency = _doc(
            "alpha/sample:bad-dep",
            words=(replace(_word(1, "a", head=0, func="root"), dependency_head_ordinal=99),),
        )
        with self.assertRaisesRegex(ValueError, "dependency"):
            build_graph([bad_dependency])

        bad_entity = _doc(
            "alpha/sample:bad-entity",
            words=(_word(1, "a", head=0, func="root"), _word(2, "b", head=1, func="dep")),
            entities=(Entity(1, None, "person", None, "#w2", 2, (1,)),),
        )
        with self.assertRaisesRegex(ValueError, "entity head"):
            build_graph([bad_entity])

        bad_translation = _doc(
            "alpha/sample:bad-translation",
            translations=(Translation(1, "orphan", ()),),
        )
        with self.assertRaisesRegex(ValueError, "translation.*word locus"):
            build_graph([bad_translation])

    def test_translations_keep_own_text_and_measured_word_loci(self) -> None:
        words = (_word(1, "a", head=0, func="root"), _word(2, "b", head=1, func="dep"))
        graph = build_graph(
            [
                _doc(
                    "alpha/sample:translations",
                    words=words,
                    translations=(Translation(1, "English text", (1, 2)),),
                    arabic_translations=(Translation(1, "نص", (2,)),),
                )
            ]
        )
        english = [node for node in graph.nodes if node.otype == "translation"][0]
        arabic = [node for node in graph.nodes if node.otype == "arabic_translation"][0]
        self.assertEqual((english.text, english.slots, english.render_mode), ("English text", (1, 2), "own_text"))
        self.assertEqual((arabic.text, arabic.slots, arabic.render_mode), ("نص", (2,), "own_text"))

    def test_layout_boundaries_preserve_order_internal_offsets_and_interword_positions(self) -> None:
        words = (_word(1, "abcd", head=0, func="root"), _word(2, "ef", head=1, func="dep"))
        events = (
            LayoutEvent(1, "line", "L0", None, None, 0),
            LayoutEvent(2, "line", "L1", 1, 1, 0),
            LayoutEvent(3, "line", "L2", 1, 3, 0),
            LayoutEvent(4, "line", "L3", None, None, 1),
        )
        graph = build_graph([_doc("alpha/sample:layout", words=words, layout_events=events)])
        lines = [node for node in graph.nodes if node.otype == "line"]

        self.assertEqual([node.label for node in lines], ["L0", "L1", "L2", "L3"])
        self.assertEqual([node.text for node in lines], ["a", "bc", "d", "ef"])
        self.assertEqual([node.slots for node in lines], [(1,), (1,), (1,), (2,)])
        self.assertEqual((lines[1].start_char, lines[1].end_char), (1, 3))
        self.assertEqual(lines[3].start_after_word_ordinal, 1)
        self.assertTrue(all(node.render_mode == "own_text" for node in lines))
        self.assertEqual(validate_graph(graph), ())

    def test_explicit_document_relations_survive_without_deduplication(self) -> None:
        source = _doc("alpha/sample:a", scholarly_id="urn:cts:copticLit:same.work")
        target = _doc("beta/sample:b", scholarly_id="urn:cts:copticLit:same.work")
        graph = build_graph(
            [target, source],
            document_relations=(
                DocumentRelation(
                    "same_scholarly",
                    "alpha/sample:a",
                    "beta/sample:b",
                    classification="alternate_analysis",
                ),
                DocumentRelation(
                    "documented_overlap",
                    "alpha/sample:a",
                    "beta/sample:b",
                    classification="textual_divergence",
                    family="fixture-family",
                ),
                DocumentRelation(
                    "witness",
                    "alpha/sample:a",
                    "beta/sample:b",
                    witness_literal="urn:cts:copticLit:same.work",
                    target_scholarly_id="urn:cts:copticLit:same.work",
                ),
            ),
        )
        documents = [node for node in graph.nodes if node.otype == "document"]
        self.assertEqual(len(documents), 2)
        self.assertEqual(
            [edge.kind for edge in graph.edges if edge.kind in {"same_scholarly", "documented_overlap", "witness"}],
            ["documented_overlap", "same_scholarly", "witness"],
        )
        self.assertEqual(validate_graph(graph), ())


if __name__ == "__main__":
    unittest.main()
