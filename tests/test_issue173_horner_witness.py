"""RED-first #173: Horner English witness remains distinct from source translation."""
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
        ('<meta corpus="pistis-sophia"><norm_group norm_group="x">'+body+
         '</norm_group>').encode("utf-8"),
        source_record_id="pistis-sophia/pistis.sophia:part1",
        source_path="pistis-sophia/pistis.sophia_TT/part1.tt",
        upstream_repository="CopticScriptorium/corpora",upstream_commit=PIN,
    )


def word(i,text,root=False):
    dep='new_sent="true" func="root"' if root else 'func="obj" head="#u1"'
    return f'<norm xml:id="u{i}" {dep} norm="{text}">{text}</norm>'


class HornerOriginalTranslationContract(unittest.TestCase):
    def test_two_distinct_english_translation_witnesses_same_coptic_words(self):
        doc=parse(
            '<translation translation="IT came to pass, when Jesus had risen from the dead,">'
            '<trans_horner trans_horner="But it happened after that Jesus rose out of those who (are) dead,">'
            +word(1,"ⲁⲥ",True)+word(2,"ϣⲱⲡⲉ")+
            '</trans_horner></translation>'
        )
        self.assertEqual(len(doc.words),2)
        self.assertEqual(doc.translations[0].text,
                         "IT came to pass, when Jesus had risen from the dead,")
        a=doc.horner_translation_annotations[0]
        self.assertEqual((a.kind,a.ordinal,a.value,a.word_ordinals),
                         ("trans_horner",1,
                          "But it happened after that Jesus rose out of those who (are) dead,",
                          (1,2)))
        self.assertEqual(doc.words[1].dependency_head_ordinal,1)
        graph=build_graph([doc])
        self.assertFalse(validate_graph(graph))
        with TemporaryDirectory() as td:
            dest=Path(td)/"tf"
            write_graph(graph,dest)
            api=Fabric(locations=[str(dest)],silent="deep").load(
                "value render_mode source_ordinal",silent="deep"
            )
            self.assertTrue(api)
            self.assertEqual(api.F.otype.maxSlot,2)
            n=api.F.otype.s("trans_horner")[0]
            self.assertEqual(api.F.value.v(n),a.value)
            self.assertEqual(api.F.render_mode.v(n),"horner_span")
            self.assertEqual(tuple(api.E.oslots.s(n)),(1,2))
            self.assertEqual(len(api.F.otype.s("translation")),1)

    def test_original_horner_opens_before_translation_without_xml_parent(self):
        doc=parse(
            '<trans_horner trans_horner="...">'
            '<translation translation="A different English reading">'
            +word(1,"a",True)+'</trans_horner></translation>'
        )
        self.assertEqual(doc.horner_translation_annotations[0].value,"...")
        self.assertEqual(doc.translations[0].text,"A different English reading")
        self.assertFalse(validate_graph(build_graph([doc])))

    def test_midword_source_position_not_forged_whole_word(self):
        doc=parse(
            '<norm xml:id="u1" new_sent="true" func="root" norm="abcd">'
            'a<trans_horner trans_horner="Horner">bc</trans_horner>d</norm>'
        )
        a=doc.horner_translation_annotations[0]
        self.assertEqual((a.start_char,a.end_char,a.word_ordinals),(1,3,()))
        n=next(n for n in build_graph([doc]).nodes if n.otype=="trans_horner")
        self.assertEqual((n.render_mode,n.slots),("horner_anchor",(1,)))

    def test_missing_duplicate_wrong_key_or_orphan_unclosed_fails_closed(self):
        for raw in (
            '</trans_horner>'+word(1,"a",True),
            '<trans_horner trans_horner="x">'+word(1,"a",True),
            '<trans_horner>'+word(1,"a",True)+'</trans_horner>',
            '<trans_horner horner="x">'+word(1,"a",True)+'</trans_horner>',
            '<trans_horner trans_horner="x" trans_horner="y">'+word(1,"a",True)+'</trans_horner>',
        ):
            with self.subTest(source=raw),self.assertRaises(ValueError):
                parse(raw)


if __name__=="__main__":
    unittest.main()
