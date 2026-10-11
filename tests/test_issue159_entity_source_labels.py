"""RED #159: independent entity/name label source evidence in native TF."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tf.fabric import Fabric
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.graph import build_graph, validate_graph
from copticscriptorium_tf.writer import write_graph

PIN="3ac067f1709a0012daf39ea8da2fac79980176a5"
KINDS=("entity_head_tok","entity_text","entity_identity","persName_type",
       "placeName_type","placeName_ref","roleName_type","rs_type","org_type")


def parse(body):
    return parse_tt_record(
        ('<meta corpus="entity_tags"><norm_group norm_group="fixture">'+body+
         '</norm_group>').encode("utf-8"),
        source_record_id="fixture/entity:one", source_path="fixture/entity_TT/one.tt",
        upstream_repository="CopticScriptorium/corpora",upstream_commit=PIN,
    )


def w(i, text, *, root=False):
    attrs='new_sent="true" func="root"' if root else 'func="obj" head="#u1"'
    return f'<norm xml:id="u{i}" {attrs} norm="{text}">{text}</norm>'


class SourceEntityLabelContract(unittest.TestCase):
    def test_entity_text_and_head_token_original_wrappers_preserve_two_word_span(self):
        doc=parse(
            '<entity_text entity_text="a b"><entity_head_tok entity_head_tok="#u2">'
            +w(1,"a",root=True)+w(2,"b")+
            '</entity_text></entity_head_tok>'
        )
        self.assertEqual(len(doc.words),2)
        attrs=doc.entity_source_annotations
        self.assertEqual([(a.kind,a.ordinal,a.value,a.word_ordinals) for a in attrs],[
            ("entity_text",1,"a b",(1,2)),
            ("entity_head_tok",2,"#u2",(1,2)),
        ])
        self.assertEqual(doc.words[1].dependency_head_ordinal,1)
        g=build_graph([doc])
        self.assertFalse(validate_graph(g))
        self.assertTrue(all(x.render_mode=="entity_label_span" for x in g.nodes if x.otype in KINDS))
        self.assertFalse(any(x.otype=="entity" for x in g.nodes))

    def test_original_person_and_place_labels_preserve_source_literals(self):
        doc=parse(
            '<persName_type persName_type="monk">'+w(1,"ⲁⲫⲟⲩ",root=True)
            +'</persName_type>'
            '<placeName_ref placeName_ref="paths:places:32">'
            '<placeName_type placeName_type="city_village">'
            +w(2,"ⲡⲉⲙϫⲉ")+'</placeName_ref></placeName_type>'
        )
        self.assertEqual([(a.kind,a.value) for a in doc.entity_source_annotations],[
            ("persName_type","monk"),
            ("placeName_ref","paths:places:32"),
            ("placeName_type","city_village"),
        ])
        with TemporaryDirectory() as td:
            dest=Path(td)/"tf"
            write_graph(build_graph([doc]),dest)
            api=Fabric(locations=[str(dest)],silent="deep").load(
                "value render_mode source_ordinal dependency_head",silent="deep"
            )
            self.assertTrue(api)
            self.assertEqual(api.F.otype.maxSlot,2)
            self.assertEqual(api.F.value.v(api.F.otype.s("placeName_ref")[0]),"paths:places:32")
            self.assertEqual(tuple(api.E.dependency_head.f(2)),(1,))

    def test_source_identity_annotated_inside_norm_and_language_is_position_only(self):
        doc=parse('<norm xml:id="u1" new_sent="true" func="root" norm="abcd">'
                  '<lang lang="Hebrew">'
                  'a<entity_identity entity_identity="Sarah">bc</entity_identity>d'
                  '</lang></norm>')
        self.assertEqual(len(doc.words),1)
        self.assertEqual(len(doc.language_annotations),1)
        a=doc.entity_source_annotations[0]
        self.assertEqual((a.value,a.start_char,a.end_char),("Sarah",1,3))
        self.assertEqual(a.word_ordinals,())
        g=build_graph([doc])
        n=next(n for n in g.nodes if n.otype=="entity_identity")
        self.assertEqual(n.render_mode,"entity_label_anchor")
        self.assertEqual(n.slots,(1,))

    def test_source_type_present_empty_and_missing_or_orphan_rejected(self):
        doc=parse('<org_type org_type="">'+w(1,"a",root=True)+'</org_type>')
        self.assertEqual(doc.entity_source_annotations[0].value,"")
        for kind in KINDS:
            with self.subTest(kind=kind):
                with self.assertRaisesRegex(ValueError,"without opening|closing"):
                    parse(f'</{kind}>'+w(1,"a",root=True))
                with self.assertRaisesRegex(ValueError,"unclosed"):
                    parse(f'<{kind} {kind}="x">'+w(1,"a",root=True))
                with self.assertRaisesRegex(ValueError,"no source value"):
                    parse(f'<{kind}>'+w(1,"a",root=True)+f'</{kind}>')


if __name__=="__main__":
    unittest.main()
