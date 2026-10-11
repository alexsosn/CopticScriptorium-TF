"""RED issue 146: TT chapter and edition reference annotations are source evidence."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tf.fabric import Fabric
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.graph import build_graph, validate_graph
from copticscriptorium_tf.writer import write_graph

PIN="3ac067f1709a0012daf39ea8da2fac79980176a5"
KINDS=("chapter_n","marcion_chapter_n","marcion_verse_n",
       "petermann_chapter_n","petermann_verse_n")

def parse(src):
    return parse_tt_record(
        ('<meta corpus="fixture"><norm_group norm_group="test">'+src+'</norm_group>').encode(),
        source_record_id="fixture/fixture:ref",
        source_path="fixture/fixture_TT/ref.tt",
        upstream_repository="CopticScriptorium/corpora", upstream_commit=PIN,
    )

def word(i,s,root=False):
    dep='new_sent="true" func="root"' if root else 'func="dep" head="#u1"'
    return f'<norm xml:id="u{i}" {dep} norm="{s}">{s}</norm>'

class ReferenceWrapperContract(unittest.TestCase):
    def test_parallel_source_reference_systems_without_forged_equivalence(self):
        src=('<chapter_n chapter_n="148_postscript">'
             '<petermann_chapter_n petermann_chapter_n="145">'
             '<marcion_chapter_n marcion_chapter_n="390">'
             '<marcion_verse_n marcion_verse_n="21">'
             '<petermann_verse_n petermann_verse_n="1">'
             +word(1,"a",True)+word(2,"b")
             +'</marcion_verse_n></petermann_verse_n>'
             '</marcion_chapter_n></petermann_chapter_n></chapter_n>')
        doc=parse(src)
        ann=doc.reference_annotations
        self.assertEqual([a.kind for a in ann],[
            "chapter_n","petermann_chapter_n","marcion_chapter_n",
            "marcion_verse_n","petermann_verse_n"])
        self.assertEqual([a.ordinal for a in ann],[1,2,3,4,5])
        self.assertEqual([a.value for a in ann],["148_postscript","145","390","21","1"])
        self.assertTrue(all(a.word_ordinals==(1,2) for a in ann))
        self.assertEqual(doc.words[1].dependency_head_ordinal,1)
        g=build_graph([doc])
        self.assertFalse(validate_graph(g))
        self.assertTrue(all(n.render_mode=="reference_span" for n in g.nodes if n.otype in KINDS))

    def test_zero_empty_and_original_native_values(self):
        doc=parse('<chapter_n chapter_n="0">'+word(1,"a",True)
                  +'</chapter_n><marcion_chapter_n marcion_chapter_n="">'
                  +word(2,"b")+'</marcion_chapter_n>')
        g=build_graph([doc])
        with TemporaryDirectory() as t:
            path=Path(t)/"tf"
            write_graph(g,path)
            api=Fabric(locations=[str(path)],silent="deep").load(
                "value render_mode dependency_head",silent="deep")
            self.assertTrue(api)
            self.assertEqual(api.F.otype.maxSlot,2)
            self.assertEqual(api.F.value.v(api.F.otype.s("chapter_n")[0]),"0")
            self.assertEqual(api.F.value.v(api.F.otype.s("marcion_chapter_n")[0]),"")
            self.assertEqual(tuple(api.E.dependency_head.f(2)),(1,))

    def test_midword_source_position_is_anchor_not_full_word(self):
        doc=parse('<norm xml:id="u1" new_sent="true" func="root" norm="abcd">'
                  'a<marcion_verse_n marcion_verse_n="22">bc</marcion_verse_n>d</norm>')
        a=doc.reference_annotations[0]
        self.assertEqual((a.start_char,a.end_char),(1,3))
        self.assertEqual(a.word_ordinals,())
        g=build_graph([doc])
        n=next(n for n in g.nodes if n.otype=="marcion_verse_n")
        self.assertEqual(n.slots,(1,))
        self.assertEqual(n.render_mode,"reference_anchor")

    def test_parallel_crossed_close_and_existing_coptic_verse_remain_separate(self):
        doc=parse('<verse_n verse_n="1">'
                  '<petermann_verse_n petermann_verse_n="1">'
                  '<marcion_verse_n marcion_verse_n="21">'+word(1,"a",True)
                  +'</petermann_verse_n>'+word(2,"b")
                  +'</marcion_verse_n></verse_n>')
        self.assertEqual([(a.kind,a.ordinal,a.word_ordinals)
                          for a in doc.reference_annotations],[
            ("petermann_verse_n",1,(1,)),
            ("marcion_verse_n",2,(1,2))])
        self.assertEqual([w.verse_n for w in doc.words],["1","1"])

    def test_missing_orphan_unclosed_reference_annotation_is_rejected(self):
        for tag in KINDS:
            with self.subTest(tag=tag):
                with self.assertRaisesRegex(ValueError,"without opening|closing"):
                    parse(f'</{tag}>'+word(1,"a",True))
                with self.assertRaisesRegex(ValueError,"unclosed"):
                    parse(f'<{tag} {tag}="1">'+word(1,"a",True))
                with self.assertRaisesRegex(ValueError,"no source value"):
                    parse(f'<{tag}>'+word(1,"a",True)+f'</{tag}>')

if __name__=="__main__":
    unittest.main()
