"""Issue #66: validated CoNLL-U supplementation reaches native Text-Fabric output.

TT stays canonical. CoNLL-U contributes only separately named ``ud_*`` features
and a separate ``ud_head`` edge, and every non-supplementing outcome is reported.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
import zipfile

from tf.fabric import Fabric


REVISION = "e" * 40
REPOSITORY = "CopticScriptorium/corpora"

# Word 3 has no TT head: only CoNLL-U supplies it.
TT_A = """<meta corpus="alpha" document_cts_urn="urn:cts:copticLit:fixture.a" title="A">
<norm_group norm_group="abc">
<norm xml:id="u1" new_sent="true" func="root" pos="N" lemma="a" norm="a">a</norm>
<norm xml:id="u2" func="dep" head="#u1" pos="V" lemma="b" norm="b">b</norm>
<norm xml:id="u3" func="obj" pos="PRON" lemma="c" norm="c">c</norm>
</norm_group>
"""
CONLLU_A = (
    "# sent_id = alpha-1\n"
    "1\ta\ta-ud\tNOUN\tN\tNumber[psor]=Sing|PronType=Prs\t0\troot\t_\tMorphs=a-a\n"
    "2\tb\tb\tVERB\tV\t_\t1\tnsubj\t_\tCxnElt=2:Demo.Elt\n"
    "3\tc\tc\tPRON\tPRON\t_\t1\tobj\t_\t_\n"
    "\n"
)

TT_SINGLE = """<meta corpus="alpha" document_cts_urn="urn:cts:copticLit:fixture.{name}" title="{name}">
<norm_group norm_group="x"><norm xml:id="u1" new_sent="true" func="root" pos="N" lemma="x" norm="x">x</norm></norm_group>
"""
CONLLU_SINGLE = "1\tx\tx\tNOUN\tN\t_\t0\troot\t_\t_\n"

UD_WORD_FEATURES = (
    "ud_lemma ud_upos ud_xpos ud_deprel ud_head_ordinal "
    "ud_feat_number_psor ud_feat_pron_type ud_misc_morphs ud_misc_cxn_elt"
)


def _write(path: Path, data: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        data = data.encode("utf-8")
    path.write_bytes(data)


def _tt_only_tree(root: Path) -> None:
    _write(root / "alpha" / "alpha_TT" / "a.tt", TT_A)


def _supplemented_tree(root: Path) -> None:
    _tt_only_tree(root)
    _write(root / "alpha" / "alpha_CONLLU" / "a.conllu", CONLLU_A)


def _convert(root: Path, destination: Path):
    from copticscriptorium_tf.converter import convert_source_tree

    return convert_source_tree(
        root,
        destination,
        upstream_repository=REPOSITORY,
        upstream_commit=REVISION,
    )


def _load(path: Path, features: str):
    api = Fabric(locations=[str(path)], silent="deep").load(features, silent="deep")
    if api is False or api is None:
        raise AssertionError("generated Text-Fabric failed clean reload")
    return api


def _document(api, source_record_id: str) -> int:
    for node in api.F.otype.s("document"):
        if api.F.source_record_id.v(node) == source_record_id:
            return node
    raise AssertionError(f"missing document {source_record_id}")


def _words(api, document: int) -> tuple[int, ...]:
    return tuple(api.L.d(document, otype="word"))


class SupplementedOutputTests(unittest.TestCase):
    def test_supplemented_words_gain_separately_named_ud_features(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            _supplemented_tree(root)
            destination = Path(temporary) / "tf"
            _convert(root, destination)

            api = _load(
                destination,
                f"source_record_id lemma pos func dependency_head ud_head "
                f"conllu_status conllu_source_path conllu_source_sha256 {UD_WORD_FEATURES}",
            )
            F, E = api.F, api.E
            document = _document(api, "alpha/alpha:a")
            w1, w2, w3 = _words(api, document)

            self.assertEqual(F.conllu_status.v(document), "supplemented")
            self.assertEqual(
                F.conllu_source_path.v(document), "alpha/alpha_CONLLU/a.conllu"
            )
            self.assertEqual(
                F.conllu_source_sha256.v(document),
                hashlib.sha256(CONLLU_A.encode("utf-8")).hexdigest(),
            )

            self.assertEqual(
                [F.ud_upos.v(w) for w in (w1, w2, w3)], ["NOUN", "VERB", "PRON"]
            )
            self.assertEqual([F.ud_xpos.v(w) for w in (w1, w2, w3)], ["N", "V", "PRON"])
            self.assertEqual(F.ud_lemma.v(w1), "a-ud")
            self.assertEqual(F.ud_deprel.v(w2), "nsubj")
            self.assertEqual([F.ud_head_ordinal.v(w) for w in (w1, w2, w3)], [0, 1, 1])
            self.assertEqual(F.ud_feat_pron_type.v(w1), "Prs")
            self.assertEqual(F.ud_feat_number_psor.v(w1), "Sing")
            self.assertIsNone(F.ud_feat_pron_type.v(w2))
            self.assertEqual(F.ud_misc_morphs.v(w1), "a-a")
            self.assertEqual(F.ud_misc_cxn_elt.v(w2), "2:Demo.Elt")

            # Separate UD head edge, including the head TT does not have.
            self.assertEqual(tuple(E.ud_head.f(w1)), ())
            self.assertEqual(tuple(E.ud_head.f(w2)), (w1,))
            self.assertEqual(tuple(E.ud_head.f(w3)), (w1,))

            # TT values are never overwritten or filled in.
            self.assertEqual(F.lemma.v(w1), "a")
            self.assertEqual(F.func.v(w2), "dep")
            self.assertEqual(tuple(E.dependency_head.f(w2)), (w1,))
            self.assertEqual(tuple(E.dependency_head.f(w3)), ())

    def test_literal_ud_keys_are_recorded_in_feature_metadata(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            _supplemented_tree(root)
            destination = Path(temporary) / "tf"
            _convert(root, destination)

            header = (destination / "ud_feat_number_psor.tf").read_text(encoding="utf-8")
            self.assertIn("@sourceKey=Number[psor]", header)
            header = (destination / "ud_misc_cxn_elt.tf").read_text(encoding="utf-8")
            self.assertIn("@sourceKey=CxnElt", header)

    def test_tt_feature_files_are_identical_with_and_without_conllu(self):
        with TemporaryDirectory() as temporary:
            tt_only_root = Path(temporary) / "tt-only"
            _tt_only_tree(tt_only_root)
            supplemented_root = Path(temporary) / "supplemented"
            _supplemented_tree(supplemented_root)
            tt_only = Path(temporary) / "tf-tt-only"
            supplemented = Path(temporary) / "tf-supplemented"
            _convert(tt_only_root, tt_only)
            _convert(supplemented_root, supplemented)

            compared = 0
            for path in sorted(tt_only.glob("*.tf")):
                if path.stem.startswith("conllu_"):
                    continue
                self.assertEqual(
                    path.read_bytes(),
                    (supplemented / path.name).read_bytes(),
                    f"TT feature {path.name} changed when CoNLL-U was supplied",
                )
                compared += 1
            self.assertGreater(compared, 10)
            self.assertFalse(any(path.stem.startswith("ud_") for path in tt_only.glob("*.tf")))

    def test_tt_only_tree_marks_every_document_missing(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            _tt_only_tree(root)
            destination = Path(temporary) / "tf"
            result = _convert(root, destination)

            api = _load(destination, "source_record_id conllu_status")
            document = _document(api, "alpha/alpha:a")
            self.assertEqual(api.F.conllu_status.v(document), "missing")
            # Features without any value are not serialized at all.
            self.assertFalse((destination / "conllu_source_path.tf").exists())
            self.assertFalse(any(path.stem.startswith("ud_") for path in destination.glob("*.tf")))
            self.assertEqual(result.conllu_supplemented_source_records, 0)
            self.assertEqual(result.conllu_missing_source_records, ("alpha/alpha:a",))


class NonSupplementingOutcomeTests(unittest.TestCase):
    CASES = {
        "placeholder": ("\n", "placeholder"),
        "malformed": ("1\tx\tx\tNOUN\tN\t_\t0\troot\t_\n", "malformed_conllu"),
        "drift": ("1\ty\ty\tNOUN\tN\t_\t0\troot\t_\t_\n", "token_alignment"),
        "badutf8": (b"1\t\xff\tx\tNOUN\tN\t_\t0\troot\t_\t_\n", "invalid_utf8"),
        "enhanced": ("1\tx\tx\tNOUN\tN\t_\t0\troot\t0:root\t_\n", "unsupported_conllu_shape"),
    }

    def _tree(self, root: Path) -> None:
        for name, (raw, _reason) in self.CASES.items():
            _write(root / "alpha" / "alpha_TT" / f"{name}.tt", TT_SINGLE.format(name=name))
            _write(root / "alpha" / "alpha_CONLLU" / f"{name}.conllu", raw)
        _write(root / "alpha" / "alpha_TT" / "missing.tt", TT_SINGLE.format(name="missing"))
        _write(root / "alpha" / "alpha_CONLLU" / "orphan.conllu", CONLLU_SINGLE)

    def test_each_outcome_is_explicit_and_tt_is_converted_unchanged(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            self._tree(root)
            destination = Path(temporary) / "tf"
            result = _convert(root, destination)

            api = _load(
                destination, "source_record_id norm lemma conllu_status conllu_source_path"
            )
            # No document was supplemented, so no UD value exists anywhere.
            self.assertFalse(any(path.stem.startswith("ud_") for path in destination.glob("*.tf")))
            for name, (_raw, reason) in self.CASES.items():
                with self.subTest(name):
                    document = _document(api, f"alpha/alpha:{name}")
                    self.assertEqual(api.F.conllu_status.v(document), reason)
                    self.assertEqual(
                        api.F.conllu_source_path.v(document),
                        f"alpha/alpha_CONLLU/{name}.conllu",
                    )
                    (word,) = _words(api, document)
                    self.assertEqual(api.F.norm.v(word), "x")
                    self.assertEqual(api.F.lemma.v(word), "x")
            missing = _document(api, "alpha/alpha:missing")
            self.assertEqual(api.F.conllu_status.v(missing), "missing")
            self.assertIsNone(api.F.conllu_source_path.v(missing))

            self.assertEqual(result.conllu_supplemented_source_records, 0)
            self.assertEqual(result.conllu_missing_source_records, ("alpha/alpha:missing",))
            self.assertEqual(
                result.conllu_records_without_tt, ("alpha/alpha_CONLLU/orphan.conllu",)
            )
            unavailable = {
                item["source_record_id"]: item for item in result.conllu_unavailable_source_records
            }
            self.assertEqual(
                {key: item["reason"] for key, item in unavailable.items()},
                {f"alpha/alpha:{name}": reason for name, (_raw, reason) in self.CASES.items()},
            )
            self.assertEqual(
                unavailable["alpha/alpha:drift"]["conllu_source_path"],
                "alpha/alpha_CONLLU/drift.conllu",
            )
            self.assertTrue(unavailable["alpha/alpha:drift"]["detail"])

    def test_cli_summary_reports_conllu_outcomes(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            self._tree(root)
            summary = Path(temporary) / "summary.json"
            completed = subprocess.run(
                [
                    sys.executable, "-m", "copticscriptorium_tf.converter",
                    str(root), str(Path(temporary) / "tf"),
                    "--upstream-repository", REPOSITORY,
                    "--upstream-commit", REVISION,
                    "--summary", str(summary),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            data = json.loads(summary.read_text(encoding="utf-8"))
            self.assertEqual(data["conllu_supplemented_source_records"], 0)
            self.assertEqual(data["conllu_missing_source_records"], ["alpha/alpha:missing"])
            self.assertEqual(
                data["conllu_records_without_tt"], ["alpha/alpha_CONLLU/orphan.conllu"]
            )
            self.assertEqual(
                sorted(item["reason"] for item in data["conllu_unavailable_source_records"]),
                sorted(reason for _raw, reason in self.CASES.values()),
            )


class PackagingTests(unittest.TestCase):
    def _ud_files(self, destination: Path) -> dict[str, bytes]:
        return {
            path.name: path.read_bytes()
            for path in sorted(destination.glob("*.tf"))
            if path.stem.startswith("ud_")
        }

    def test_archive_members_supplement_exactly_like_directory_files(self):
        with TemporaryDirectory() as temporary:
            directory_root = Path(temporary) / "directory"
            _supplemented_tree(directory_root)

            nested_root = Path(temporary) / "nested-archive"
            _tt_only_tree(nested_root)
            with zipfile.ZipFile(nested_root / "alpha" / "alpha_CONLLU.zip", "w") as archive:
                archive.writestr("alpha_CONLLU/a.conllu", CONLLU_A.encode("utf-8"))

            flat_root = Path(temporary) / "flat-archive"
            _tt_only_tree(flat_root)
            with zipfile.ZipFile(flat_root / "alpha" / "alpha_CONLLU.zip", "w") as archive:
                archive.writestr("a.conllu", CONLLU_A.encode("utf-8"))

            outputs = {}
            for name, root in (
                ("directory", directory_root),
                ("nested", nested_root),
                ("flat", flat_root),
            ):
                destination = Path(temporary) / f"tf-{name}"
                _convert(root, destination)
                outputs[name] = destination

            expected = self._ud_files(outputs["directory"])
            self.assertTrue(expected)
            self.assertEqual(self._ud_files(outputs["nested"]), expected)
            self.assertEqual(self._ud_files(outputs["flat"]), expected)

            api = _load(outputs["nested"], "source_record_id conllu_source_path conllu_status")
            document = _document(api, "alpha/alpha:a")
            self.assertEqual(api.F.conllu_status.v(document), "supplemented")
            self.assertEqual(
                api.F.conllu_source_path.v(document),
                "alpha/alpha_CONLLU.zip!/alpha_CONLLU/a.conllu",
            )

    def test_case_insensitive_record_identity_pairs_like_tt(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            _tt_only_tree(root)
            _write(root / "alpha" / "alpha_CONLLU" / "A.CONLLU", CONLLU_A)
            destination = Path(temporary) / "tf"
            _convert(root, destination)
            api = _load(destination, "source_record_id conllu_status conllu_source_path")
            document = _document(api, "alpha/alpha:a")
            self.assertEqual(api.F.conllu_status.v(document), "supplemented")
            self.assertEqual(
                api.F.conllu_source_path.v(document), "alpha/alpha_CONLLU/A.CONLLU"
            )


class DiscoveryFailsClosedTests(unittest.TestCase):
    def _assert_rejected(self, build, message: str) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            _tt_only_tree(root)
            build(root)
            destination = Path(temporary) / "tf"
            with self.assertRaisesRegex(ValueError, message):
                _convert(root, destination)
            self.assertFalse(destination.exists())

    def test_nested_directory_member_is_rejected(self):
        self._assert_rejected(
            lambda root: _write(root / "alpha" / "alpha_CONLLU" / "sub" / "a.conllu", CONLLU_A),
            "unsupported CoNLL-U directory member layout",
        )

    def test_unsupported_dataset_depth_is_rejected(self):
        self._assert_rejected(
            lambda root: _write(root / "alpha" / "extra" / "alpha_CONLLU" / "a.conllu", CONLLU_A),
            "unsupported CoNLL-U dataset layout",
        )

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_symlinked_record_is_rejected(self):
        def build(root: Path) -> None:
            target = root.parent / "outside.conllu"
            _write(target, CONLLU_A)
            directory = root / "alpha" / "alpha_CONLLU"
            directory.mkdir(parents=True)
            (directory / "a.conllu").symlink_to(target)

        self._assert_rejected(build, "symlinked CoNLL-U source record is unsupported")

    def test_unsupported_archive_member_layout_is_rejected(self):
        def build(root: Path) -> None:
            with zipfile.ZipFile(root / "alpha" / "alpha_CONLLU.zip", "w") as archive:
                archive.writestr("elsewhere/a.conllu", CONLLU_A.encode("utf-8"))

        self._assert_rejected(build, "unsupported CoNLL-U archive member layout")

    def test_empty_conllu_dataset_is_rejected(self):
        self._assert_rejected(
            lambda root: (root / "alpha" / "alpha_CONLLU").mkdir(parents=True),
            "CoNLL-U dataset contains no supported CoNLL-U records",
        )

    def test_case_insensitive_conllu_collision_is_rejected(self):
        def build(root: Path) -> None:
            _write(root / "alpha" / "alpha_CONLLU" / "a.conllu", CONLLU_A)
            with zipfile.ZipFile(root / "alpha" / "alpha_CONLLU.zip", "w") as archive:
                archive.writestr("A.conllu", CONLLU_A.encode("utf-8"))

        self._assert_rejected(build, "CoNLL-U source-record collision")

    def test_distinct_keys_mapping_to_one_feature_name_are_rejected(self):
        colliding = CONLLU_A.replace("PronType=Prs", "ABc=1|Abc=2")
        self._assert_rejected(
            lambda root: _write(root / "alpha" / "alpha_CONLLU" / "a.conllu", colliding),
            "UD feature-name collision",
        )


class CookbookTests(unittest.TestCase):
    def test_cookbook_queries_the_supplemental_ud_layer(self):
        import importlib.util

        path = Path(__file__).resolve().parents[1] / "examples" / "query_cookbook.py"
        spec = importlib.util.spec_from_file_location("issue66_query_cookbook", path)
        cookbook = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cookbook)

        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            _supplemented_tree(root)
            destination = Path(temporary) / "tf"
            _convert(root, destination)
            api = cookbook.load_generated_tf(destination)
            w1, w2, w3 = _words(api, _document(api, "alpha/alpha:a"))

            self.assertEqual(cookbook.ud_hits(api, ud_upos="PRON"), ((w3,),))
            self.assertEqual(
                cookbook.ud_hits(api, ud_upos="NOUN", ud_feat_number_psor="Sing"), ((w1,),)
            )
            self.assertEqual(
                sorted(cookbook.ud_dependency_pairs(api)), [(w2, w1), (w3, w1)]
            )
            self.assertEqual(cookbook.ud_dependency_pairs(api, deprel="obj"), ((w3, w1),))
            with self.assertRaisesRegex(ValueError, "ud_feat_absent"):
                cookbook.ud_hits(api, ud_feat_absent="x")


class AgoraParityTests(unittest.TestCase):
    def test_agora_adapter_emits_the_same_tf_as_the_direct_converter(self):
        from copticscriptorium_tf.agora import materialize

        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            _supplemented_tree(root)
            direct = Path(temporary) / "direct"
            _convert(root, direct)
            staging = Path(temporary) / "agora"
            staging.mkdir()
            tf_dir = materialize(root, staging, source_revision=REVISION)

            direct_files = {path.name: path.read_bytes() for path in direct.glob("*.tf")}
            agora_files = {path.name: path.read_bytes() for path in tf_dir.glob("*.tf")}
            self.assertIn("ud_upos.tf", direct_files)
            self.assertEqual(agora_files, direct_files)
            summary = json.loads((staging / "conversion-summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["conllu_supplemented_source_records"], 1)


if __name__ == "__main__":
    unittest.main()
