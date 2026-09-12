import unittest


class LayoutBoundaryPositionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from copticscriptorium_tf.parser import parse_tt_record

        cls.parse_tt_record = staticmethod(parse_tt_record)

    def parse(self, body: str):
        return self.parse_tt_record(
            body.encode("utf-8"),
            source_record_id="demo/demo:one",
            source_path="demo/demo_TT/one.tt",
            upstream_repository="CopticScriptorium/corpora",
            upstream_commit="abc123",
        )

    def test_boundaries_before_between_and_inside_words_preserve_stream_position(self):
        document = self.parse(
            '<meta corpus="demo">\n'
            '<lb_n lb_n="before">\n'
            '<norm_group norm_group="a">'
            '<norm xml:id="u1" new_sent="true" func="root" norm="abcd">'
            'ab<cb_n cb_n="inside">cd'
            '</norm>'
            '</norm_group>\n'
            '<lb_n lb_n="between-a">\n'
            '<pb_xml_id pb_xml_id="between-b">\n'
            '<norm_group norm_group="b">'
            '<norm xml:id="u2" func="dep" head="#u1" norm="ef">ef</norm>'
            '</norm_group>\n'
        )

        self.assertEqual(
            [
                (
                    event.kind,
                    event.value,
                    event.word_ordinal,
                    event.char_offset,
                    event.after_word_ordinal,
                )
                for event in document.layout_events
            ],
            [
                ("line", "before", None, None, 0),
                ("column", "inside", 1, 2, 0),
                ("line", "between-a", None, None, 1),
                ("page", "between-b", None, None, 1),
            ],
        )

    def test_internal_boundary_position_is_before_completion_of_current_word(self):
        document = self.parse(
            '<meta corpus="demo">\n'
            '<norm_group norm_group="a">'
            '<norm xml:id="u1" new_sent="true" func="root" norm="ab">'
            'a<lb_n lb_n="x">b'
            '</norm>'
            '</norm_group>\n'
        )
        event = document.layout_events[0]
        self.assertEqual(event.word_ordinal, 1)
        self.assertEqual(event.char_offset, 1)
        self.assertEqual(event.after_word_ordinal, 0)


if __name__ == "__main__":
    unittest.main()
