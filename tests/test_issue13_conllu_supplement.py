import unittest

from copticscriptorium_tf.parser import parse_tt_record


TT = b'''<meta corpus="demo" document_cts_urn="urn:cts:demo:one">
<norm_group norm_group="ab">
<norm xml:id="u1" new_sent="true" func="root" pos="N" lemma="a" norm="a">a</norm>
<norm xml:id="u2" func="obj" head="#u1" pos="N" lemma="b" norm="b">b</norm>
</norm_group>
'''


def document():
    return parse_tt_record(
        TT,
        source_record_id="demo/demo:one",
        source_path="demo/demo_TT/one.tt",
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit="abc123",
    )


class ConlluSupplementContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from copticscriptorium_tf.conllu import SupplementUnavailable, parse_conllu_supplement

        cls.SupplementUnavailable = SupplementUnavailable
        cls.parse_supplement = staticmethod(parse_conllu_supplement)

    def test_valid_supplement_is_separate_and_preserves_tt_values(self):
        doc = document()
        raw = b'''# sent_id = s1
1\ta\ta\tNOUN\tXPOS_A\tCase=Nom\t0\troot\t_\tMorphs=a|Cxn=Demo
2\tb\tb\tNOUN\tXPOS_B\t_\t1\tobj\t_\tOrig=b
'''
        supplement = self.parse_supplement(doc, raw, source_path="demo/demo_CONLLU/one.conllu")

        self.assertEqual(supplement.source_path, "demo/demo_CONLLU/one.conllu")
        self.assertEqual(len(supplement.words), 2)
        self.assertEqual(supplement.words[0].ordinal, 1)
        self.assertEqual(supplement.words[0].feats, {"Case": "Nom"})
        self.assertEqual(supplement.words[0].misc["Cxn"], "Demo")
        self.assertEqual(supplement.words[0].head_ordinal, 0)
        self.assertEqual(supplement.words[1].head_ordinal, 1)
        self.assertEqual(supplement.words[1].deprel, "obj")
        self.assertEqual(doc.words[1].func, "obj")
        self.assertEqual(doc.words[1].pos, "N")
        self.assertFalse(hasattr(supplement.words[0], "tf_node"))

    def test_entity_escaped_form_aligns_semantically_but_literal_is_preserved(self):
        doc = parse_tt_record(
            b'<meta corpus="demo"><norm_group norm_group="x"><norm xml:id="u1" new_sent="true" func="root" norm="<">x</norm></norm_group>',
            source_record_id="demo/demo:one",
            source_path="demo/demo_TT/one.tt",
            upstream_repository="repo",
            upstream_commit="sha",
        )
        supplement = self.parse_supplement(
            doc,
            b'1\t&lt;\t_\tX\tX\t_\t0\troot\t_\t_\n',
            source_path="demo/demo_CONLLU/one.conllu",
        )
        self.assertEqual(supplement.words[0].form_literal, "&lt;")
        self.assertEqual(supplement.words[0].form, "<")

    def test_placeholder_is_explicitly_non_supplementing(self):
        with self.assertRaises(self.SupplementUnavailable) as caught:
            self.parse_supplement(document(), b"\n", source_path="placeholder.conllu")
        self.assertEqual(caught.exception.reason, "placeholder")

    def test_malformed_structure_is_explicitly_non_supplementing(self):
        malformed = b'1\ta\ta\tNOUN\tN\t_\t0\troot\t_\n'
        with self.assertRaises(self.SupplementUnavailable) as caught:
            self.parse_supplement(document(), malformed, source_path="bad.conllu")
        self.assertEqual(caught.exception.reason, "malformed_conllu")

    def test_token_count_and_norm_drift_fail_alignment(self):
        one_token = b'1\ta\ta\tNOUN\tN\t_\t0\troot\t_\t_\n'
        with self.assertRaises(self.SupplementUnavailable) as caught:
            self.parse_supplement(document(), one_token, source_path="short.conllu")
        self.assertEqual(caught.exception.reason, "token_alignment")

        wrong_norm = b'''1\ta\ta\tNOUN\tN\t_\t0\troot\t_\t_
2\tc\tc\tNOUN\tN\t_\t1\tobj\t_\t_
'''
        with self.assertRaises(self.SupplementUnavailable) as caught:
            self.parse_supplement(document(), wrong_norm, source_path="drift.conllu")
        self.assertEqual(caught.exception.reason, "token_alignment")

    def test_sentence_local_heads_are_normalized_to_document_ordinals(self):
        doc = parse_tt_record(
            b'''<meta corpus="demo">
<norm_group norm_group="x">
<norm xml:id="u1" new_sent="true" func="root" norm="a">a</norm>
<norm xml:id="u2" func="dep" head="#u1" norm="b">b</norm>
<norm xml:id="u3" new_sent="true" func="root" norm="c">c</norm>
<norm xml:id="u4" func="dep" head="#u3" norm="d">d</norm>
</norm_group>
''',
            source_record_id="demo/demo:one",
            source_path="demo/demo_TT/one.tt",
            upstream_repository="repo",
            upstream_commit="sha",
        )
        raw = b'''# sent_id = s1
1\ta\t_\tX\tX\t_\t0\troot\t_\t_
2\tb\t_\tX\tX\t_\t1\tdep\t_\t_

# sent_id = s2
1\tc\t_\tX\tX\t_\t0\troot\t_\t_
2\td\t_\tX\tX\t_\t1\tdep\t_\t_
'''
        supplement = self.parse_supplement(doc, raw, source_path="two-sentences.conllu")
        self.assertEqual([word.head_ordinal for word in supplement.words], [0, 1, 0, 3])


if __name__ == "__main__":
    unittest.main()
