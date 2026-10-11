"""RED #156: original multi-attribute TT evidence must survive TF conversion."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from tf.fabric import Fabric
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.graph import build_graph, validate_graph
from copticscriptorium_tf.writer import write_graph

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"


def parse(body):
    return parse_tt_record(
        ('<meta corpus="attributes"><norm_group norm_group="a">'+body+'</norm_group>').encode(),
        source_record_id="attrs/attrs:one", source_path="attrs/attrs_TT/one.tt",
        upstream_repository="CopticScriptorium/corpora", upstream_commit=PIN,
    )


def w(i, text, root=False):
    attr = 'new_sent="true" func="root"' if root else 'func="obj" head="#u1"'
    return f'<norm xml:id="u{i}" {attr} norm="{text}">{text}</norm>'


class MultiattributeSourceContracts(unittest.TestCase):
    def test_preserve_every_gap_optional_source_attribute_and_original_word(self):
        doc=parse('<gap gap="gap" reason="lost" extent="2" unit="character">'
                  +w(1,"[...] ",True)+'</gap>')
        self.assertEqual(len(doc.words),1)
        a=doc.intervention_annotations[0]
        self.assertEqual((a.kind,a.ordinal),("gap",1))
        self.assertEqual(dict(a.source_attributes),
                         {"extent":"2","gap":"gap","reason":"lost","unit":"character"})
        self.assertEqual(a.word_ordinals,(1,))
        graph=build_graph([doc])
        self.assertFalse(validate_graph(graph))
        node=next(n for n in graph.nodes if n.otype=="gap")
        self.assertEqual(dict(node.source_attributes),dict(a.source_attributes))
        self.assertEqual(node.render_mode,"intervention_span")

    def test_abbr_uses_original_type_without_nonexistent_abbr_key(self):
        doc=parse('<abbr type="nomina_sacra">'+w(1,"ⲡⲛⲁ",True)+'</abbr>')
        a=doc.intervention_annotations[0]
        self.assertEqual((a.kind,a.ordinal),("abbr",1))
        self.assertEqual(dict(a.source_attributes),{"type":"nomina_sacra"})
        graph=build_graph([doc])
        with TemporaryDirectory() as td:
            dest=Path(td)/"tf"
            write_graph(graph,dest)
            api=Fabric(locations=[str(dest)],silent="deep").load(
                "source_attr_abbr_type value source_ordinal",silent="deep"
            )
            self.assertTrue(api)
            n=api.F.otype.s("abbr")[0]
            self.assertEqual(api.F.source_attr_abbr_type.v(n),"nomina_sacra")
            self.assertEqual(api.F.otype.maxSlot,1)

    def test_supplied_extras_remain_individual_native_features(self):
        doc=parse('<supplied supplied="supplied" source="transcriber" reason="lacuna">'
                  +w(1,"a",True)+'</supplied>')
        with TemporaryDirectory() as td:
            dest=Path(td)/"tf"
            write_graph(build_graph([doc]),dest)
            api=Fabric(locations=[str(dest)],silent="deep").load(
                "source_attr_supplied_supplied source_attr_supplied_source "
                "source_attr_supplied_reason",silent="deep"
            )
            self.assertTrue(api)
            node=api.F.otype.s("supplied")[0]
            self.assertEqual(api.F.source_attr_supplied_supplied.v(node),"supplied")
            self.assertEqual(api.F.source_attr_supplied_source.v(node),"transcriber")
            self.assertEqual(api.F.source_attr_supplied_reason.v(node),"lacuna")

    def test_optional_missing_key_is_not_forged_empty_string(self):
        doc=parse('<gap extent="2">'+w(1,"a",True)+'</gap>'
                  '<gap reason="">'+w(2,"b")+'</gap>')
        with TemporaryDirectory() as td:
            dest=Path(td)/"tf"
            write_graph(build_graph([doc]),dest)
            api=Fabric(locations=[str(dest)],silent="deep").load(
                "source_attr_gap_extent source_attr_gap_reason",silent="deep"
            )
            self.assertTrue(api)
            n1,n2=api.F.otype.s("gap")
            self.assertEqual(api.F.source_attr_gap_extent.v(n1),"2")
            self.assertIsNone(api.F.source_attr_gap_extent.v(n2))
            self.assertIsNone(api.F.source_attr_gap_reason.v(n1))
            self.assertEqual(api.F.source_attr_gap_reason.v(n2),"")

    def test_midword_partial_is_anchor_not_forged_whole_word(self):
        doc=parse('<norm xml:id="u1" new_sent="true" func="root" norm="abcd">'
                  'a<supplied supplied="supplied" reason="lost">bc</supplied>d</norm>')
        a=doc.intervention_annotations[0]
        self.assertEqual((a.start_char,a.end_char),(1,3))
        self.assertEqual(a.word_ordinals,())
        n=next(n for n in build_graph([doc]).nodes if n.otype=="supplied")
        self.assertEqual(n.render_mode,"intervention_anchor")
        self.assertEqual(n.slots,(1,))

    def test_invalid_extra_source_keys_duplicates_unclosed_and_orphan_fail_closed(self):
        for kind, attrs in [
            ("gap",'reason="x" reason="y"'),
            ("supplied",'mystery="x"'),
            ("abbr",'abbr="fake"'),
        ]:
            with self.subTest(kind=kind,attrs=attrs),self.assertRaisesRegex(ValueError,"attribute|unknown|source"):
                parse(f'<{kind} {attrs}>'+w(1,"a",True)+f'</{kind}>')
        for tag in ("gap","supplied","abbr"):
            with self.subTest(tag=tag):
                with self.assertRaisesRegex(ValueError,"without opening|closing"):
                    parse(f'</{tag}>'+w(1,"a",True))
                with self.assertRaisesRegex(ValueError,"unclosed"):
                    key="type" if tag=="abbr" else tag
                    parse(f'<{tag} {key}="x">'+w(1,"a",True))
                with self.assertRaisesRegex(ValueError,"no source|attribute"):
                    parse(f'<{tag}>'+w(1,"a",True)+f'</{tag}>')


if __name__=="__main__":
    unittest.main()
