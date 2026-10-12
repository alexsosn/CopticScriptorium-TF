"""Issue 162 RED-first original TT document/witness marker conservation."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tf.fabric import Fabric
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.graph import build_graph, validate_graph
from copticscriptorium_tf.writer import write_graph

PIN="3ac067f1709a0012daf39ea8da2fac79980176a5"
KINDS=("pb_coptic_id","p_n","p","p_source","pb_n","lb_nb")


def parse(body):
    return parse_tt_record(
        ('<meta corpus="doc_marker"><norm_group norm_group="x">'+body+'</norm_group>').encode(),
        source_record_id="fixture/fixture:docmarker",
        source_path="fixture/fixture_TT/docmarker.tt",
        upstream_repository="CopticScriptorium/corpora",upstream_commit=PIN,
    )


def word(i, text, root=False):
    attrs='new_sent="true" func="root"' if root else 'func="obj" head="#u1"'
    return f'<norm xml:id="u{i}" {attrs} norm="{text}">{text}</norm>'


class OriginalPageParagraphMarkerContract(unittest.TestCase):
    def test_literal_source_combining_marks_and_roman_number_are_retained(self):
        doc=parse(
            '<pb_coptic_id pb_coptic_id="ⲧ̅ⲛ̅ⲃ̅.ⲁ.">'
            '<p_n p_n="I.1">'
            +word(1,"a",root=True)+word(2,"b")
            +'</p_n></pb_coptic_id>'
        )
        ann=doc.document_source_annotations
        self.assertEqual([(a.kind,a.ordinal,a.value,a.word_ordinals) for a in ann],[
            ("pb_coptic_id",1,"ⲧ̅ⲛ̅ⲃ̅.ⲁ.",(1,2)),
            ("p_n",2,"I.1",(1,2)),
        ])
        self.assertEqual(doc.words[1].dependency_head_ordinal,1)
        graph=build_graph([doc])
        self.assertFalse(validate_graph(graph))
        self.assertEqual(len(graph.slots),2)
        self.assertTrue(all(n.render_mode=="document_span" for n in graph.nodes if n.otype in KINDS))

    def test_crossed_provenance_paragraph_and_line_page_reference(self):
        doc=parse(
            '<p_source p_source="PATHS"><p p="p">'
            '<lb_nb lb_nb="1">'+word(1,"a",root=True)
            +'</p_source></p>'
            '<pb_n pb_n="23">'+word(2,"b")+'</pb_n></lb_nb>'
        )
        self.assertEqual([
            (a.kind,a.ordinal,a.word_ordinals)
            for a in doc.document_source_annotations
        ],[
            ("p_source",1,(1,)),
            ("p",2,(1,)),
            ("lb_nb",3,(1,2)),
            ("pb_n",4,(2,)),
        ])

    def test_source_annotation_midword_is_an_anchor_not_whole_word(self):
        doc=parse(
            '<norm xml:id="u1" new_sent="true" func="root" norm="abcd">'
            'a<pb_n pb_n="20">bc</pb_n>d</norm>'
        )
        a=doc.document_source_annotations[0]
        self.assertEqual((a.start_char,a.end_char),(1,3))
        self.assertEqual(a.word_ordinals,())
        g=build_graph([doc])
        n=next(n for n in g.nodes if n.otype=="pb_n")
        self.assertEqual((n.render_mode,n.slots),("document_anchor",(1,)))

    def test_native_tf_reload_preserves_original_literals_and_tt_word_heads(self):
        doc=parse('<p_source p_source="PATHS">'+word(1,"a",root=True)
                  +word(2,"b")+'</p_source>')
        with TemporaryDirectory() as td:
            dest=Path(td)/"tf"
            write_graph(build_graph([doc]),dest)
            api=Fabric(locations=[str(dest)],silent="deep").load(
                "value render_mode source_ordinal dependency_head",silent="deep"
            )
            self.assertTrue(api)
            self.assertEqual(api.F.otype.maxSlot,2)
            self.assertEqual(api.F.value.v(api.F.otype.s("p_source")[0]),"PATHS")
            self.assertEqual(tuple(api.E.dependency_head.f(2)),(1,))

    def test_bad_source_closing_unclosed_and_missing_literal_fail_closed(self):
        for tag in KINDS:
            with self.subTest(tag=tag):
                with self.assertRaisesRegex(ValueError,"without opening|closing"):
                    parse(f'</{tag}>'+word(1,"a",root=True))
                with self.assertRaisesRegex(ValueError,"unclosed"):
                    parse(f'<{tag} {tag}="x">'+word(1,"a",root=True))
                with self.assertRaisesRegex(ValueError,"no source value"):
                    parse(f'<{tag}>'+word(1,"a",root=True)+f'</{tag}>')


if __name__=="__main__":
    unittest.main()
