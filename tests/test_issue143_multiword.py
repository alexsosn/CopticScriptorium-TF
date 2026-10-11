"""#143 RED-first TT multiword grouping contract: source span != added token."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tf.fabric import Fabric

from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.graph import build_graph, validate_graph
from copticscriptorium_tf.writer import write_graph

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"


def parse(tt: str):
    return parse_tt_record(
        tt.encode("utf-8"), source_record_id="fixture/fixture:multiword",
        source_path="fixture/fixture_TT/multiword.tt",
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit=PIN,
    )


def word(i: int, text: str, *, head: int = 0):
    headpart = "new_sent=\"true\" func=\"root\"" if head == 0 else f'func="fixed" head="#u{head}"'
    return (
        f'<orig_group orig_group="{text}"><norm_group norm_group="{text}">'
        f'<orig orig="{text}"><norm xml:id="u{i}" {headpart} norm="{text}">'
        f'{text}</norm></orig></norm_group></orig_group>'
    )


def source(inner: str):
    return '<meta corpus="fixture">' + inner


class NativeMultiwordContract(unittest.TestCase):
    def test_cross_line_two_word_group_retains_two_existing_coptic_slots_and_heads(self):
        doc = parse(source(
            '<lb_n lb_n="10"><multiword multiword="ⲉⲓ ⲉⲃⲟⲗ">'
            + word(1, "ⲉⲓ") + '</lb_n><lb_n lb_n="11">'
            + word(2, "ⲉⲃⲟⲗ", head=1) + '</multiword></lb_n>'
        ))
        self.assertEqual(len(doc.words), 2)
        self.assertEqual(len(doc.multiword_annotations), 1)
        a = doc.multiword_annotations[0]
        self.assertEqual((a.kind, a.ordinal, a.value), ("multiword", 1, "ⲉⲓ ⲉⲃⲟⲗ"))
        self.assertEqual(a.word_ordinals, (1, 2))
        self.assertEqual(doc.words[1].dependency_head_ordinal, 1)
        graph = build_graph([doc])
        self.assertFalse(validate_graph(graph))
        mw = next(n for n in graph.nodes if n.otype == "multiword")
        self.assertEqual(mw.slots, (1, 2))
        self.assertEqual(mw.render_mode, "multiword_span")

    def test_literal_value_and_native_tf_reload_preserve_group_identity(self):
        doc = parse(source('<multiword multiword="ⲉⲓ  ⲉⲃⲟⲗ">' +
                           word(1, "ⲉⲓ") + word(2, "ⲉⲃⲟⲗ", head=1) +
                           '</multiword>'))
        with TemporaryDirectory() as td:
            path = Path(td) / "tf"
            graph = build_graph([doc])
            write_graph(graph, path)
            api = Fabric(locations=[str(path)], silent="deep").load(
                "value source_ordinal render_mode source_record_id dependency_head",
                silent="deep",
            )
            self.assertTrue(api)
            self.assertEqual(api.F.otype.maxSlot, 2)
            nodes = api.F.otype.s("multiword")
            self.assertEqual(len(nodes), 1)
            self.assertEqual(api.F.value.v(nodes[0]), "ⲉⲓ  ⲉⲃⲟⲗ")
            self.assertEqual(api.F.source_ordinal.v(nodes[0]), 1)
            self.assertEqual(api.F.render_mode.v(nodes[0]), "multiword_span")
            self.assertEqual(api.E.oslots.s(nodes[0]), (1, 2))
            self.assertEqual(api.E.dependency_head.f(2), (1,))

    def test_crossed_edition_wrappers_are_not_forged_as_token_segments(self):
        doc = parse(source(
            '<ed_line_n ed_line_n="5"><multiword multiword="a b">'
            + word(1, "a") + '</ed_line_n>'
            + word(2, "b", head=1) + '</multiword>'
        ))
        self.assertEqual(len(doc.multiword_annotations), 1)
        self.assertEqual(len(doc.edition_annotations), 1)
        self.assertEqual(doc.edition_annotations[0].word_ordinals, (1,))
        self.assertEqual(doc.multiword_annotations[0].word_ordinals, (1, 2))

    def test_nested_multiword_events_have_distinct_opening_ordinals(self):
        doc = parse(source(
            '<multiword multiword="a b"><multiword multiword="a">'
            + word(1, "a") + '</multiword>'
            + word(2, "b", head=1) + '</multiword>'
        ))
        self.assertEqual([(a.ordinal, a.value, a.word_ordinals)
                          for a in doc.multiword_annotations],
                         [(1, "a b", (1, 2)), (2, "a", (1,))])

    def test_source_value_absence_or_unmatched_closure_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "without opening|closing"):
            parse(source('</multiword>' + word(1, "a")))
        with self.assertRaisesRegex(ValueError, "unclosed"):
            parse(source('<multiword multiword="x">' + word(1, "a")))
        with self.assertRaisesRegex(ValueError, "no source value"):
            parse(source('<multiword>' + word(1, "a") + '</multiword>'))
        doc = parse(source('<multiword multiword="">' + word(1, "a") + '</multiword>'))
        self.assertEqual(doc.multiword_annotations[0].value, "")


if __name__ == "__main__":
    unittest.main()
