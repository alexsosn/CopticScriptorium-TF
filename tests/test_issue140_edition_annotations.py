"""#140 RED-first source-faithful edition pagination + native TF contract."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tf.fabric import Fabric

from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.graph import build_graph, validate_graph
from copticscriptorium_tf.writer import write_graph

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
KINDS = ("ed_line_n", "ed_lb_n", "ed_page_n", "ed_pg_n")
META = '<meta corpus="edition">'


def parse(source: str):
    return parse_tt_record(
        source.encode("utf-8"),
        source_record_id="edition/edition:test",
        source_path="edition/edition_TT/test.tt",
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit=PIN,
    )


def tt(body: str):
    return META + '<norm_group norm_group="fixture">' + body + '</norm_group>'


def word(n: int, text: str, *, root: bool = False):
    dep = 'func="root"' if root else f'func="obj" head="#u1"'
    first = ' new_sent="true"' if root else ""
    return (
        f'<norm xml:id="u{n}" {dep}{first} norm="{text}">'
        + text + '</norm>'
    )


class EditionTagConservationTests(unittest.TestCase):
    def test_source_edition_page_spans_two_original_words_not_manuscript_page(self):
        doc = parse(tt(
            '<ed_page_n ed_page_n="5"><ed_line_n ed_line_n="12">'
            + word(1, "abc", root=True) + word(2, "def")
            + '</ed_line_n></ed_page_n>'
        ))
        self.assertEqual([a.kind for a in doc.edition_annotations],
                         ["ed_page_n", "ed_line_n"])
        self.assertEqual([a.ordinal for a in doc.edition_annotations], [1, 2])
        self.assertEqual([a.value for a in doc.edition_annotations], ["5", "12"])
        self.assertTrue(all(a.word_ordinals == (1, 2) for a in doc.edition_annotations))
        g = build_graph([doc])
        self.assertFalse(validate_graph(g))
        self.assertEqual([n.render_mode for n in g.nodes if n.otype == "ed_page_n"],
                         ["edition_span"])
        self.assertEqual(doc.words[1].dependency_head_ordinal, 1)
        self.assertFalse(any(n.otype == "page" for n in g.nodes))

    def test_intra_token_editorial_line_gets_char_anchor_not_fake_word_span(self):
        doc = parse(tt(
            '<norm xml:id="u1" new_sent="true" func="root" norm="abc">'
            'a<ed_lb_n ed_lb_n="7">b</ed_lb_n>c</norm>'
        ))
        self.assertEqual(len(doc.words), 1)
        a = doc.edition_annotations[0]
        self.assertEqual((a.start_char, a.end_char), (1, 2))
        self.assertEqual(a.word_ordinals, ())
        g = build_graph([doc])
        n = next(n for n in g.nodes if n.otype == "ed_lb_n")
        self.assertEqual(n.slots, (1,))
        self.assertEqual(n.render_mode, "edition_anchor")
        self.assertEqual((n.start_char, n.end_char), (1, 2))

    def test_crossed_edition_closures_have_independent_tracks(self):
        doc = parse(tt(
            '<ed_line_n ed_line_n="1">'
            '<ed_page_n ed_page_n="p">'
            + word(1, "a", root=True)
            + '</ed_line_n>'
            + word(2, "b")
            + '</ed_page_n>'
        ))
        self.assertEqual([(a.kind, a.ordinal, a.word_ordinals)
                          for a in doc.edition_annotations],
                         [("ed_line_n", 1, (1,)), ("ed_page_n", 2, (1, 2))])

    def test_ed_pg_n_leading_zero_and_present_empty_lit_are_not_normalized(self):
        doc = parse(tt(
            '<ed_pg_n ed_pg_n="0001">' + word(1, "a", root=True)
            + '</ed_pg_n><ed_line_n ed_line_n="">'
            + word(2, "b") + '</ed_line_n>'
        ))
        g = build_graph([doc])
        with TemporaryDirectory() as root:
            path = Path(root) / "tf"
            write_graph(g, path)
            api = Fabric(locations=[str(path)], silent="deep").load(
                "value render_mode source_ordinal", silent="deep",
            )
            self.assertTrue(api)
            self.assertEqual(api.F.otype.maxSlot, 2)
            page = api.F.otype.s("ed_pg_n")
            line = api.F.otype.s("ed_line_n")
            self.assertEqual(api.F.value.v(page[0]), "0001")
            self.assertEqual(api.F.value.v(line[0]), "")
            self.assertEqual(api.F.render_mode.v(page[0]), "edition_span")

    def test_orphan_unclosed_absent_and_missing_source_word_are_fail_closed(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                with self.assertRaisesRegex(ValueError, "without opening|closing"):
                    parse(tt(f'</{kind}>' + word(1, "a", root=True)))
                with self.assertRaisesRegex(ValueError, "unclosed"):
                    parse(tt(f'<{kind} {kind}="x">' + word(1, "a", root=True)))
                with self.assertRaisesRegex(ValueError, "no source value"):
                    parse(tt(f'<{kind}>' + word(1, "a", root=True)
                             + f'</{kind}>'))


if __name__ == "__main__":
    unittest.main()
