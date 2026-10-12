"""RED-first original Horner translated-witness source contracts."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tf.fabric import Fabric
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.graph import build_graph, validate_graph
from copticscriptorium_tf.writer import write_graph

PIN="3ac067f1709a0012daf39ea8da2fac79980176a5"

def parse(body):
    return parse_tt_record(
        ('<meta corpus="horner"><norm_group norm_group="x">'+body+'</norm_group>').encode(),
        source_record_id="horner/horner:one", source_path="horner/horner_TT/one.tt",
        upstream_repository="CopticScriptorium/corpora", upstream_commit=PIN,
    )

def word(i,text,root=False):
    dep='new_sent="true" func="root"' if root else 'func="obj" head="#u1"'
    return f'<norm xml:id="u{i}" {dep} norm="{text}">{text}</norm>'

class HornerNativeWitnessTest(unittest.TestCase):
    def test_parallel_existing_translation_and_horner_are_distinct(self):
        primary="IT came to pass, when Jesus had risen from the dead,"
        horner="But it happened after that Jesus rose out of those who (are) dead,"
        doc=parse(f'<translation translation="{primary}">'
                  f'<trans_horner trans_horner="{horner}">'
                  +word(1,"a",True)+word(2,"b")+
                  '</trans_horner></translation>')
        self.assertEqual([(t.text,t.word_ordinals) for t in doc.translations],
                         [(primary,(1,2))])
        self.assertEqual(
            [(a.kind,a.value,a.ordinal,a.word_ordinals) for a in doc.horner_annotations],
            [("trans_horner",horner,1,(1,2))]
        )
        self.assertEqual(doc.words[1].dependency_head_ordinal,1)
        g=build_graph([doc])
        self.assertFalse(validate_graph(g))
        self.assertEqual(len(g.slots),2)
        self.assertEqual(len([n for n in g.nodes if n.otype=="translation"]),1)
        with TemporaryDirectory() as td:
            out=Path(td)/"tf"
            write_graph(g,out)
            api=Fabric(locations=[str(out)],silent="deep").load(
                "value render_mode source_ordinal dependency_head",silent="deep"
            )
            self.assertTrue(api)
            self.assertEqual(api.F.value.v(api.F.otype.s("trans_horner")[0]),horner)
            self.assertEqual(tuple(api.E.dependency_head.f(2)),(1,))

    def test_horner_not_required_to_match_existing_translation_range(self):
        doc=parse('<translation translation="Primary"><trans_horner trans_horner="Horner">'
                  +word(1,"a",True)+'</translation>'
                  +word(2,"b")+'</trans_horner>')
        self.assertEqual(doc.translations[0].word_ordinals,(1,))
        self.assertEqual(doc.horner_annotations[0].word_ordinals,(1,2))

    def test_midword_horner_only_a_source_position(self):
        doc=parse('<norm xml:id="u1" new_sent="true" func="root" norm="abcd">'
                  'a<trans_horner trans_horner="English">bc</trans_horner>d</norm>')
        a=doc.horner_annotations[0]
        self.assertEqual((a.start_char,a.end_char),(1,3))
        node=next(n for n in build_graph([doc]).nodes if n.otype=="trans_horner")
        self.assertEqual((node.render_mode,node.slots),("horner_anchor",(1,)))

    def test_missing_orphan_unclosed_duplicate_original_rejected(self):
        with self.assertRaisesRegex(ValueError,"without opening|closing"):
            parse('</trans_horner>'+word(1,"a",True))
        with self.assertRaisesRegex(ValueError,"unclosed"):
            parse('<trans_horner trans_horner="a">'+word(1,"a",True))
        with self.assertRaisesRegex(ValueError,"no source value|attribute"):
            parse('<trans_horner>'+word(1,"a",True)+'</trans_horner>')
        with self.assertRaisesRegex(ValueError,"duplicate"):
            parse('<trans_horner trans_horner="a" trans_horner="b">'
                  +word(1,"a",True)+'</trans_horner>')

if __name__=="__main__":
    unittest.main()
