import unittest


class FailClosedSgmlContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from copticscriptorium_tf.parser import parse_tt_record

        cls.parse_tt_record = staticmethod(parse_tt_record)

    def parse(self, text: str):
        return self.parse_tt_record(
            text.encode("utf-8"),
            source_record_id="demo/demo:one",
            source_path="demo/demo_TT/one.tt",
            upstream_repository="CopticScriptorium/corpora",
            upstream_commit="abc123",
        )

    @staticmethod
    def body() -> str:
        return (
            '<norm_group norm_group="x">'
            '<norm xml:id="u1" new_sent="true" func="root" norm="x">x</norm>'
            '</norm_group>'
        )

    def test_non_whitespace_prefix_before_metadata_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "start with metadata"):
            self.parse("garbage<meta corpus=\"demo\">" + self.body())

    def test_bom_and_whitespace_before_metadata_are_allowed(self):
        doc = self.parse("\ufeff  \n<meta corpus=\"demo\">" + self.body())
        self.assertEqual(len(doc.words), 1)

    def test_crossing_linguistic_group_closes_fail_closed(self):
        with self.subTest("orig_group closes before child norm_group"):
            with self.assertRaisesRegex(ValueError, "linguistic.*order"):
                self.parse(
                    '<meta corpus="demo">'
                    '<orig_group orig_group="x">'
                    '<norm_group norm_group="x">'
                    '<norm xml:id="u1" new_sent="true" func="root" norm="x">x</norm>'
                    '</orig_group>'
                    '</norm_group>'
                )

        with self.subTest("norm_group closes before child orig"):
            with self.assertRaisesRegex(ValueError, "linguistic.*order"):
                self.parse(
                    '<meta corpus="demo">'
                    '<norm_group norm_group="x">'
                    '<orig orig="x">'
                    '<norm xml:id="u1" new_sent="true" func="root" norm="x">x</norm>'
                    '</norm_group>'
                    '</orig>'
                )


if __name__ == "__main__":
    unittest.main()
