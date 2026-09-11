import tempfile
from pathlib import Path
import unittest
import zipfile


class SourceParserContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from copticscriptorium_tf.parser import parse_source_tree, parse_tt_record

        cls.parse_source_tree = staticmethod(parse_source_tree)
        cls.parse_tt_record = staticmethod(parse_tt_record)

    def parse(self, text: str):
        return self.parse_tt_record(
            text.encode("utf-8"),
            source_record_id="demo/demo:one",
            source_path="demo/demo_TT/one.tt",
            upstream_repository="CopticScriptorium/corpora",
            upstream_commit="abc123",
        )

    def test_parses_groups_words_sentences_and_local_dependencies_without_tf_ids(self):
        doc = self.parse(
            '<meta corpus="demo" document_cts_urn="urn:cts:demo:one" title="Demo">\n'
            '<orig_group orig_group="ⲀⲂ">\n'
            '<norm_group norm_group="ⲁⲃ">\n'
            '<orig orig="Ⲁ">\n'
            '<norm xml:id="u1" new_sent="true" func="root" pos="N" lemma="ⲁ" norm="ⲁ">Ⲁ</norm>\n'
            '</orig>\n'
            '<orig orig="Ⲃ">\n'
            '<norm xml:id="u2" func="dep" head="#u1" pos="N" lemma="ⲃ" norm="ⲃ">Ⲃ</norm>\n'
            '</orig>\n'
            '</norm_group>\n'
            '</orig_group>\n'
        )

        self.assertEqual(doc.source_record_id, "demo/demo:one")
        self.assertEqual(doc.corpus, "demo")
        self.assertEqual(doc.dataset, "demo")
        self.assertEqual(doc.scholarly_id, "urn:cts:demo:one")
        self.assertEqual([w.source_id for w in doc.words], ["u1", "u2"])
        self.assertEqual([w.norm for w in doc.words], ["ⲁ", "ⲃ"])
        self.assertEqual(doc.words[0].dependency_head_ordinal, 0)
        self.assertEqual(doc.words[1].dependency_head_ordinal, 1)
        self.assertEqual([s.word_ordinals for s in doc.sentences], [(1, 2)])
        self.assertEqual(len(doc.orig_groups), 1)
        self.assertEqual(len(doc.norm_groups), 1)
        self.assertEqual(len(doc.origs), 2)
        self.assertEqual(doc.norm_groups[0].orig_indices, (0, 1))
        self.assertEqual(doc.origs[0].word_ordinals, (1,))
        self.assertEqual(doc.origs[1].word_ordinals, (2,))
        self.assertFalse(hasattr(doc.words[0], "tf_node"))
        self.assertFalse(hasattr(doc, "tf_node"))

    def test_preserves_direct_norm_under_group_no_orig_and_multi_orig_shapes(self):
        doc = self.parse(
            '<meta corpus="demo">\n'
            '<norm_group norm_group="direct">\n'
            '<norm xml:id="u1" new_sent="true" func="root" pos="N" lemma="x" norm="x">x</norm>\n'
            '</norm_group>\n'
            '<norm_group norm_group="multi">\n'
            '<orig orig="a"><norm xml:id="u2" func="dep" head="#u1" pos="N" lemma="a" norm="a">a</norm></orig>\n'
            '<orig orig="b"><norm xml:id="u3" func="dep" head="#u1" pos="N" lemma="b" norm="b">b</norm></orig>\n'
            '</norm_group>\n'
        )

        self.assertEqual(doc.norm_groups[0].orig_indices, ())
        self.assertEqual(doc.norm_groups[0].direct_word_ordinals, (1,))
        self.assertEqual(doc.norm_groups[1].orig_indices, (0, 1))
        self.assertEqual(doc.origs[0].word_ordinals, (2,))
        self.assertEqual(doc.origs[1].word_ordinals, (3,))

    def test_layout_crossing_inside_word_records_exact_offset_without_splitting_word(self):
        doc = self.parse(
            '<meta corpus="demo">\n'
            '<norm_group norm_group="x"><orig orig="abcd">\n'
            '<norm xml:id="u1" new_sent="true" func="root" pos="N" lemma="x" norm="abcd">\n'
            'ab<lb_n lb_n="2">c<pb_xml_id pb_xml_id="p2">d\n'
            '</norm></orig></norm_group>\n'
        )

        self.assertEqual(len(doc.words), 1)
        self.assertEqual(
            [(e.kind, e.value, e.word_ordinal, e.char_offset) for e in doc.layout_events],
            [("line", "2", 1, 2), ("page", "p2", 1, 3)],
        )

    def test_entity_opened_inside_current_word_inherits_word_and_head_must_resolve_inside_locus(self):
        doc = self.parse(
            '<meta corpus="demo">\n'
            '<norm_group norm_group="x"><orig orig="ab">\n'
            '<norm xml:id="u1" new_sent="true" func="root" pos="N" lemma="a" norm="a">a'
            '<entity entity="person" head_tok="#u1" identity="Person">x</entity>'
            '</norm>\n'
            '<norm xml:id="u2" func="dep" head="#u1" pos="N" lemma="b" norm="b">b</norm>\n'
            '</orig></norm_group>\n'
        )

        self.assertEqual(len(doc.entities), 1)
        self.assertEqual(doc.entities[0].word_ordinals, (1,))
        self.assertEqual(doc.entities[0].head_word_ordinal, 1)
        self.assertEqual(doc.entities[0].identity, "Person")

        with self.assertRaisesRegex(ValueError, "entity head.*outside"):
            self.parse(
                '<meta corpus="demo">\n'
                '<norm_group norm_group="x"><orig orig="ab">\n'
                '<entity entity="person" head_tok="#u2">'
                '<norm xml:id="u1" new_sent="true" func="root" pos="N" lemma="a" norm="a">a</norm>'
                '</entity>'
                '<norm xml:id="u2" func="dep" head="#u1" pos="N" lemma="b" norm="b">b</norm>'
                '</orig></norm_group>\n'
            )

    def test_translation_and_arabic_translation_inherit_current_word_and_keep_own_text(self):
        doc = self.parse(
            '<meta corpus="demo">\n'
            '<norm_group norm_group="x"><orig orig="ab">\n'
            '<translation translation="Before">\n'
            '<norm xml:id="u1" new_sent="true" func="root" pos="N" lemma="a" norm="a">a'
            '<arabic arabic="داخل">x</arabic>'
            '<translation translation="Inside">x</translation>'
            '</norm>\n'
            '<norm xml:id="u2" func="dep" head="#u1" pos="N" lemma="b" norm="b">b</norm>\n'
            '</translation>\n'
            '</orig></norm_group>\n'
        )

        self.assertEqual([(t.text, t.word_ordinals) for t in doc.translations], [("Inside", (1,)), ("Before", (1, 2))])
        self.assertEqual([(t.text, t.word_ordinals) for t in doc.arabic_translations], [("داخل", (1,))])

    def test_unresolved_dependency_and_entity_head_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "dependency head.*u9"):
            self.parse(
                '<meta corpus="demo"><norm_group norm_group="x"><norm xml:id="u1" new_sent="true" func="dep" head="#u9" pos="N" lemma="x" norm="x">x</norm></norm_group>'
            )
        with self.assertRaisesRegex(ValueError, "entity head.*u9"):
            self.parse(
                '<meta corpus="demo"><norm_group norm_group="x"><entity entity="person" head_tok="#u9"><norm xml:id="u1" new_sent="true" func="root" pos="N" lemma="x" norm="x">x</norm></entity></norm_group>'
            )

    def test_duplicate_metadata_evidence_and_missing_optional_values_are_preserved(self):
        doc = self.parse(
            '<meta corpus="demo" places="A" places="B">\n'
            '<norm_group norm_group="x"><norm xml:id="u1" new_sent="true" func="root" norm="x">x</norm></norm_group>\n'
        )
        self.assertIsNone(doc.scholarly_id)
        self.assertIsNone(doc.words[0].lemma)
        self.assertEqual(doc.metadata["places"], "A")
        self.assertEqual(doc.metadata_duplicates["places"], ("A", "B"))

    def test_source_tree_reads_direct_and_archive_records_with_strict_utf8_provenance_and_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            direct = root / "z" / "z_TT"
            direct.mkdir(parents=True)
            direct_text = '<meta corpus="z"><norm_group norm_group="x"><norm xml:id="u1" new_sent="true" func="root" norm="z">z</norm></norm_group>\n'
            (direct / "two.tt").write_text(direct_text, encoding="utf-8")

            corpus = root / "a"
            corpus.mkdir()
            archive_text = '<meta corpus="a"><norm_group norm_group="x"><norm xml:id="u1" new_sent="true" func="root" norm="a">a</norm></norm_group>\n'
            with zipfile.ZipFile(corpus / "a_TT.zip", "w") as archive:
                archive.writestr("a_TT/one.tt", archive_text.encode("utf-8"))

            docs = self.parse_source_tree(
                root,
                upstream_repository="CopticScriptorium/corpora",
                upstream_commit="abc123",
            )
            self.assertEqual([d.source_record_id for d in docs], ["a/a:one", "z/z:two"])
            self.assertEqual([d.packaging for d in docs], ["archive", "directory"])
            self.assertTrue(all(len(d.source_sha256) == 64 for d in docs))
            self.assertTrue(all(d.upstream_commit == "abc123" for d in docs))

            (direct / "bad.tt").write_bytes(b"\xff")
            with self.assertRaises(UnicodeDecodeError):
                self.parse_source_tree(
                    root,
                    upstream_repository="CopticScriptorium/corpora",
                    upstream_commit="abc123",
                )

    def test_unsupported_archive_member_layout_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "a"
            corpus.mkdir()
            with zipfile.ZipFile(corpus / "a_TT.zip", "w") as archive:
                archive.writestr("unexpected/nested/one.tt", b'<meta corpus="a">')
            with self.assertRaisesRegex(ValueError, "archive member layout"):
                self.parse_source_tree(root, upstream_repository="repo", upstream_commit="sha")


if __name__ == "__main__":
    unittest.main()
