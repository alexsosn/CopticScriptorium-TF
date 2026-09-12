import unittest

from copticscriptorium_tf.parser import parse_tt_record


class NestedEntityContractTests(unittest.TestCase):
    def test_nested_entities_keep_source_order_and_parent_relation(self):
        doc = parse_tt_record(
            b'''<meta corpus="demo">
<norm_group norm_group="x">
<entity entity="person" head_tok="#u1" identity="Outer">
<norm xml:id="u1" new_sent="true" func="root" norm="a">a
<entity entity="title" head_tok="#u1" identity="Inner">x</entity>
</norm>
<norm xml:id="u2" func="dep" head="#u1" norm="b">b</norm>
</entity>
</norm_group>
''',
            source_record_id="demo/demo:one",
            source_path="demo/demo_TT/one.tt",
            upstream_repository="repo",
            upstream_commit="sha",
        )

        self.assertEqual([entity.ordinal for entity in doc.entities], [1, 2])
        self.assertEqual([entity.identity for entity in doc.entities], ["Outer", "Inner"])
        self.assertEqual(doc.entities[0].parent_entity_ordinal, None)
        self.assertEqual(doc.entities[1].parent_entity_ordinal, 1)
        self.assertEqual(doc.entities[0].word_ordinals, (1, 2))
        self.assertEqual(doc.entities[1].word_ordinals, (1,))
        self.assertEqual(doc.entities[0].head_word_ordinal, 1)
        self.assertEqual(doc.entities[1].head_word_ordinal, 1)


if __name__ == "__main__":
    unittest.main()
