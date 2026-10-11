"""#153 RED-first native Coptic editorial source annotation contracts."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from tf.fabric import Fabric

from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.graph import build_graph, validate_graph
from copticscriptorium_tf.writer import write_graph

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
KINDS = (
    "hi_rend", "note", "gap_reason", "supplied_reason", "note_note", "gap_unit",
    "supplied_source", "gap_quantity", "gap_extent", "supplied_evidence",
    "unclear_reason", "unclear",
)


def parse(body):
    return parse_tt_record(
        ('<meta corpus="editorial"><norm_group norm_group="fixture">'+body+'</norm_group>').encode("utf-8"),
        source_record_id="editorial/editorial:test",
        source_path="editorial/editorial_TT/test.tt",
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit=PIN,
    )


def word(i,text,root=False):
    dep='new_sent="true" func="root"' if root else 'func="obj" head="#u1"'
    return f'<norm xml:id="u{i}" {dep} norm="{text}">{text}</norm>'


class EditorialSourceAnnotations(unittest.TestCase):
    def test_intra_norm_hi_rend_is_character_source_anchor_and_word_not_split(self):
        doc=parse('<norm xml:id="u1" new_sent="true" func="root" norm="abcd">'
                  'a<hi_rend hi_rend="red">bc</hi_rend>d</norm>')
        self.assertEqual(len(doc.words),1)
        a=doc.editorial_annotations[0]
        self.assertEqual((a.kind,a.value,a.ordinal),("hi_rend","red",1))
        self.assertEqual((a.start_char,a.end_char),(1,3))
        self.assertEqual(a.word_ordinals,())
        g=build_graph([doc])
        self.assertFalse(validate_graph(g))
        n=next(n for n in g.nodes if n.otype=="hi_rend")
        self.assertEqual(n.slots,(1,))
        self.assertEqual(n.render_mode,"editorial_anchor")

    def test_source_note_covers_two_words_even_when_crossing_norm_groups(self):
        doc=parse('<note note="tearing and water damage">'
                  +word(1,"a",True)+word(2,"b")+'</note>')
        a=doc.editorial_annotations[0]
        self.assertEqual((a.kind,a.value,a.word_ordinals),
                         ("note","tearing and water damage",(1,2)))
        self.assertEqual(doc.words[1].dependency_head_ordinal,1)
        g=build_graph([doc])
        self.assertFalse(validate_graph(g))
        n=next(n for n in g.nodes if n.otype=="note")
        self.assertEqual(n.render_mode,"editorial_span")
        self.assertEqual(n.slots,(1,2))

    def test_crossed_editorial_gap_source_stacks_preserve_opening_order(self):
        doc=parse(
            '<gap_reason gap_reason="lost">'
            '<gap_quantity gap_quantity="2">'
            '<gap_unit gap_unit="character">'
            +word(1,"a",True)
            +'</gap_reason></gap_quantity>'
            +word(2,"b")+'</gap_unit>'
        )
        self.assertEqual(
            [(x.kind,x.ordinal,x.word_ordinals) for x in doc.editorial_annotations],
            [("gap_reason",1,(1,)),("gap_quantity",2,(1,)),("gap_unit",3,(1,2))]
        )

    def test_original_source_entities_empty_and_native_reload(self):
        doc=parse(
            '<note note="a &amp; b">'+word(1,"a",True)+'</note>'
            '<supplied_source supplied_source="">'+word(2,"b")+'</supplied_source>'
        )
        self.assertEqual(
            [(x.kind,x.value) for x in doc.editorial_annotations],
            [("note","a & b"),("supplied_source","")]
        )
        g=build_graph([doc])
        with TemporaryDirectory() as td:
            path=Path(td)/"tf"
            write_graph(g,path)
            api=Fabric(locations=[str(path)],silent="deep").load(
                "value render_mode source_ordinal dependency_head",silent="deep"
            )
            self.assertTrue(api)
            self.assertEqual(api.F.otype.maxSlot,2)
            self.assertEqual(api.F.value.v(api.F.otype.s("note")[0]),"a & b")
            self.assertEqual(api.F.value.v(api.F.otype.s("supplied_source")[0]),"")
            self.assertEqual(tuple(api.E.dependency_head.f(2)),(1,))

    def test_orphan_unclosed_missing_source_value_fail_closed_all_twelve(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                with self.assertRaisesRegex(ValueError,"without opening|closing"):
                    parse(f'</{kind}>'+word(1,"a",True))
                with self.assertRaisesRegex(ValueError,"unclosed"):
                    parse(f'<{kind} {kind}="x">'+word(1,"a",True))
                with self.assertRaisesRegex(ValueError,"no source value"):
                    parse(f'<{kind}>'+word(1,"a",True)+f'</{kind}>')

if __name__=="__main__":
    unittest.main()
