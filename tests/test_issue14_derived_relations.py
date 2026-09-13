from __future__ import annotations

from dataclasses import replace
import unittest

from copticscriptorium_tf.graph import build_graph, derive_document_relations
from copticscriptorium_tf.model import DocumentModel, Sentence, Word


def word(ordinal: int, *, lemma: str = "same", head: int = 0) -> Word:
    return Word(
        ordinal=ordinal,
        source_id=f"w{ordinal}",
        norm="ⲁ",
        lemma=lemma,
        pos="N",
        func="root" if head == 0 else "dep",
        head_literal=None if head == 0 else f"#w{head}",
        dependency_head_ordinal=head,
        source_text="ⲁ",
    )


def document(
    source_record_id: str,
    scholarly_id: str,
    *,
    raw_hash: str,
    lemma: str = "same",
    witness: str | None = None,
) -> DocumentModel:
    prefix, record = source_record_id.split(":", 1)
    corpus, dataset = prefix.split("/", 1)
    metadata = {"document_cts_urn": scholarly_id, "title": record}
    if witness is not None:
        metadata["witness"] = witness
    words = (word(1, lemma=lemma),)
    return DocumentModel(
        source_record_id=source_record_id,
        source_path=f"{corpus}/{dataset}_TT/{record}.tt",
        source_sha256=raw_hash,
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
        sentences=(Sentence(1, (1,)),),
        origs=(),
        norm_groups=(),
        orig_groups=(),
        layout_events=(),
        entities=(),
        translations=(),
        arabic_translations=(),
        source_text="fixture",
    )


class DerivedDocumentRelationTests(unittest.TestCase):
    def test_same_scholarly_relation_is_measured_without_collapsing_documents(self) -> None:
        left = document(
            "source/source:a",
            "urn:cts:copticLit:demo.same",
            raw_hash="1" * 64,
        )
        right = document(
            "tree/tree:b",
            "urn:cts:copticLit:demo.same",
            raw_hash="1" * 64,
        )

        relations = derive_document_relations([right, left])
        self.assertEqual(len(relations), 1)
        relation = relations[0]
        self.assertEqual(relation.kind, "same_scholarly")
        self.assertEqual(relation.classification, "byte_identical")
        self.assertEqual((relation.source_record_id, relation.target_record_id), (left.source_record_id, right.source_record_id))

        graph = build_graph([right, left])
        documents = [node for node in graph.nodes if node.otype == "document"]
        self.assertEqual(len(documents), 2)
        self.assertEqual([edge.kind for edge in graph.edges if edge.kind == "same_scholarly"], ["same_scholarly"])

    def test_documented_overlap_uses_reviewed_family_and_measured_classification(self) -> None:
        left = document(
            "sahidica.mark/sahidica.mark:Mark_01",
            "urn:cts:copticLit:mark.separate",
            raw_hash="1" * 64,
            lemma="analysis-a",
        )
        right = document(
            "sahidica.nt/sahidica.nt:41_Mark_01",
            "urn:cts:copticLit:nt.aggregate",
            raw_hash="2" * 64,
            lemma="analysis-b",
        )

        relations = derive_document_relations([right, left])
        self.assertEqual(len(relations), 1)
        relation = relations[0]
        self.assertEqual(relation.kind, "documented_overlap")
        self.assertEqual(relation.family, "book_aggregate")
        self.assertEqual(relation.classification, "alternate_analysis")

    def test_witness_literal_is_preserved_and_targets_every_physical_copy_of_scholarly_identity(self) -> None:
        target_a = document(
            "target/source:a",
            "urn:cts:copticLit:target.work",
            raw_hash="1" * 64,
        )
        target_b = document(
            "target/tree:b",
            "urn:cts:copticLit:target.work",
            raw_hash="1" * 64,
        )
        source = document(
            "witness/source:c",
            "urn:cts:copticLit:source.work",
            raw_hash="3" * 64,
            witness="MS A; cf. urn:cts:copticLit:target.work.",
        )

        relations = derive_document_relations([target_b, source, target_a])
        witness_relations = [relation for relation in relations if relation.kind == "witness"]
        self.assertEqual(
            [(relation.source_record_id, relation.target_record_id) for relation in witness_relations],
            [(source.source_record_id, target_a.source_record_id), (source.source_record_id, target_b.source_record_id)],
        )
        self.assertTrue(all(relation.witness_literal == source.metadata["witness"] for relation in witness_relations))
        self.assertTrue(all(relation.target_scholarly_id == target_a.scholarly_id for relation in witness_relations))

    def test_unresolved_extracted_witness_target_fails_closed(self) -> None:
        source = document(
            "witness/source:c",
            "urn:cts:copticLit:source.work",
            raw_hash="3" * 64,
            witness="urn:cts:copticLit:missing.work",
        )
        with self.assertRaisesRegex(ValueError, "unresolved witness"):
            derive_document_relations([source])


if __name__ == "__main__":
    unittest.main()
