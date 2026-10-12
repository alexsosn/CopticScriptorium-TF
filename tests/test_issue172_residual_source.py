"""Issue #172 RED tests for original residual TT markup."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tf.fabric import Fabric
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.graph import build_graph, validate_graph
from copticscriptorium_tf.writer import write_graph

PIN="3ac067f1709a0012daf39ea8da2fac79980176a5"
KINDS=("date_type","german","section_title","quote_ref","quote_type",
       "gap_exent","ignore_note","ed_page","sup","supplied_quantity",
       "supplied_unit","sic","surplus","source_lang","pb","add_place",
       "pb_id","sub","gap_reasaon","gap_reasonn","hi","surplus_reason",
       "cb","del_rend","figDesc","figure","pb_coptic_xml")


def parse(body):
    return parse_tt_record(
        ('<meta corpus="residual"><norm_group norm_group="x">'+body+'</norm_group>').encode(),
        source_record_id="residual/residual:one",
        source_path="residual/residual_TT/one.tt",
        upstream_repository="CopticScriptorium/corpora",upstream_commit=PIN,
    )


def word(i,text,root=False):
    attr='new_sent="true" func="root"' if root else 'func="obj" head="#u1"'
    return f'<norm xml:id="u{i}" {attr} norm="{text}">{text}</norm>'


class SourceResidualContract(unittest.TestCase):
    def test_original_hi_rend_alias_not_forged_hi_value(self):
        doc=parse('<hi rend="red">'+word(1,"a",True)+'</hi>')
        self.assertEqual([(a.kind,a.value,a.ordinal)
                          for a in doc.residual_annotations],[("hi","red",1)])
        graph=build_graph([doc])
        self.assertFalse(validate_graph(graph))
        with TemporaryDirectory() as td:
            dest=Path(td)/"tf"
            write_graph(graph,dest)
            api=Fabric(locations=[str(dest)],silent="deep").load(
                "value render_mode",silent="deep"
            )
            self.assertEqual(api.F.otype.maxSlot,1)
            node=api.F.otype.s("hi")[0]
            self.assertEqual(api.F.value.v(node),"red")
            self.assertEqual(api.F.render_mode.v(node),"residual_span")

    def test_crossed_source_quotes_are_two_source_labels_not_lxx_matches(self):
        doc=parse(
            '<quote_ref quote_ref="Sal.72 , 22.23">'
            '<quote_type quote_type="biblical">'
            +word(1,"a",True)+word(2,"b")+
            '</quote_ref></quote_type>'
        )
        self.assertEqual([(a.kind,a.value,a.word_ordinals)
                          for a in doc.residual_annotations],
            [("quote_ref","Sal.72 , 22.23",(1,2)),
             ("quote_type","biblical",(1,2))])
        self.assertEqual(doc.words[1].dependency_head_ordinal,1)

    def test_midword_figured_seal_is_position_only(self):
        doc=parse(
            '<norm xml:id="u1" new_sent="true" func="root" norm="abcd">'
            'a<figDesc figDesc="seal"><figure figure="figure">b'
            '</figDesc></figure>cd</norm>'
        )
        self.assertEqual([(a.kind,a.start_char,a.end_char)
                          for a in doc.residual_annotations],
                         [("figDesc",1,2),("figure",1,2)])
        g=build_graph([doc])
        self.assertFalse(validate_graph(g))
        self.assertTrue(all(n.render_mode=="residual_anchor"
                            for n in g.nodes if n.otype in ("figDesc","figure")))

    def test_misspelled_gap_and_canonical_gap_unit_stay_distinct(self):
        doc=parse('<gap_exent gap_exent="unknown">'
                  '<gap_unit gap_unit="character">'
                  +word(1,"a",True)+'</gap_exent></gap_unit>')
        self.assertEqual(doc.residual_annotations[0].kind,"gap_exent")
        self.assertEqual(doc.editorial_annotations[0].kind,"gap_unit")

    def test_german_is_source_label_not_coptic_word(self):
        doc=parse('<german german="Nicht berühren!">'
                  +word(1,"a",True)+'</german>')
        self.assertEqual(doc.residual_annotations[0].value,"Nicht berühren!")
        self.assertEqual(len(doc.words),1)

    def test_missing_orphan_unclosed_wrong_alias_and_duplicate_fail(self):
        for kind in KINDS:
            key="rend" if kind=="hi" else kind
            with self.subTest(kind=kind):
                with self.assertRaisesRegex(ValueError,"without opening|closing"):
                    parse(f'</{kind}>'+word(1,"a",True))
                with self.assertRaisesRegex(ValueError,"unclosed"):
                    parse(f'<{kind} {key}="x">'+word(1,"a",True))
                with self.assertRaisesRegex(ValueError,"no source value|attribute"):
                    parse(f'<{kind}>'+word(1,"a",True)+f'</{kind}>')
        with self.assertRaisesRegex(ValueError,"no source value|attribute"):
            parse('<hi hi="forged">'+word(1,"a",True)+'</hi>')
        with self.assertRaisesRegex(ValueError,"duplicate"):
            parse('<hi rend="a" rend="b">'+word(1,"a",True)+'</hi>')


if __name__=="__main__":
    unittest.main()
