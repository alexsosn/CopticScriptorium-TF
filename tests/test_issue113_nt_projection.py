"""RED: attach Coptic-owned NT address wefts to real native SBL annotation nodes."""
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from tf.fabric import Fabric
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.graph import build_graph
from copticscriptorium_tf.writer import write_graph
from copticscriptorium_tf.nt_modules import (
    NtModuleError, project_nt_modules,
)

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
REC = "sahidica.mark/sahidica.mark:Mark_02"
TT = (
    '<meta book="Mark" corpus="sahidica.mark" chapter="2" '
    'document_cts_urn="urn:cts:copticLit:nt.mark.sahidica_ed:2" '
    'Greek_source="Greek text from the SBL Greek New Testament">'
    '<verse_n verse_n="1"><sbl_greek sbl_greek="α· ">'
    '<verse_vid verse_vid="41N 2:1">'
    '<vid_n vid_n="urn:cts:copticLit:nt.mark.sahidica_ed:2.1">'
    '<norm_group norm_group="ⲁ"><norm xml:id="u1" norm="ⲁ" '
    'new_sent="true" func="root">ⲁ</norm></norm_group>'
    '</sbl_greek></vid_n></verse_vid></verse_n>'
)


def doc():
    return parse_tt_record(TT.encode("utf-8"), source_record_id=REC,
        source_path="sahidica.mark/sahidica.mark_TT/Mark_02.tt",
        upstream_repository="CopticScriptorium/corpora", upstream_commit=PIN)


def greek(correct=True):
    return SimpleNamespace(
        T=SimpleNamespace(
            nodeFromSection=lambda ref: 999 if ref == ("Mark", 2, 1) else None,
            sectionFromNode=lambda node: ("Mark", 2, 1 if correct else 2),
        ),
        F=SimpleNamespace(otype=SimpleNamespace(v=lambda node: "verse")),
    )


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.td = TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.root = Path(self.td.name)
        self.document = doc()
        self.coptic_tf = self.root / "coptic-tf"
        write_graph(build_graph([self.document]), self.coptic_tf)
        self.api = Fabric(locations=[str(self.coptic_tf)], silent="deep").load(
            "source_record_id source_ordinal value sbl_verse_n "
            "source_sha256 source_word_ordinal norm render_mode", silent="deep",
        )
        self.assertTrue(self.api)
        self.greek_tf = self.root/"greek-tf"
        self.greek_tf.mkdir()
        for name in ("otype", "oslots", "book", "chapter", "verse"):
            (self.greek_tf / (name+".tf")).write_text(f"test {name}")

    def project(self, documents=None, other_greek=None):
        with patch("copticscriptorium_tf.nt_modules.validate_greek_release", return_value=None):
            return project_nt_modules(
                [self.document] if documents is None else documents,
                coptic_api=self.api, greek_api=greek() if other_greek is None else other_greek,
                coptic_tf_dir=self.coptic_tf, greek_tf_dir=self.greek_tf,
                destination=self.root/"wefts",
            )

    def test_real_sbl_node_gets_reference_not_coptic_word_slot(self):
        result = self.project()
        self.assertEqual(result["reference_candidate"], 1)
        self.assertEqual(result["coptic_annotated_sbl_nodes"], 1)
        self.assertEqual(result["greek_target_verse_nodes"], 1)
        self.assertTrue((self.root/"wefts"/"coptic"/"coptic_nt_ref_id.tf").is_file())
        coptic = Fabric(
            locations=[str(self.coptic_tf),str(self.root/"wefts"/"coptic")],
            silent="deep",
        ).load("coptic_nt_ref_id coptic_nt_ref_status",silent="deep")
        self.assertTrue(coptic)
        node, = coptic.F.otype.s("sbl_greek")
        self.assertIn(":Mark:2:1",coptic.F.coptic_nt_ref_id.v(node))
        self.assertEqual(coptic.F.coptic_nt_ref_status.v(node),"reference_candidate")
        self.assertIsNone(coptic.F.coptic_nt_ref_id.v(1))

    def test_changed_native_sbl_literal_blocks_projection(self):
        altered = replace(self.document, sbl_annotations=(
            replace(self.document.sbl_annotations[0],value="different"),))
        with self.assertRaisesRegex(NtModuleError, "source value"):
            self.project(documents=[altered])
        self.assertFalse((self.root/"wefts").exists())

    def test_fake_greek_node_reverse_section_blocks_projection(self):
        with self.assertRaisesRegex(NtModuleError, "Greek target"):
            self.project(other_greek=greek(correct=False))

    def test_parent_sbl_nodes_not_covered_by_sources_block_projection(self):
        altered = replace(self.document, sbl_annotations=())
        with self.assertRaisesRegex(NtModuleError,"unpaired"):
            self.project(documents=[altered])


if __name__=="__main__":
    unittest.main()
