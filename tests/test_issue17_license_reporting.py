"""Issue #8 local-only license metadata reporting carried into issue #17.

A missing or blank source license is surfaced, without pretending to validate
nonempty upstream terms or assigning a blanket license to derived TF data.
"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from copticscriptorium_tf.converter import convert_source_tree


def _source(root: Path) -> None:
    directory = root / "alpha" / "alpha_TT"
    directory.mkdir(parents=True)
    for name, license_attribute in (
        ("empty", ' license=" "'),
        ("missing", ""),
        ("present", ' license="CC-BY-4.0"'),
    ):
        (directory / f"{name}.tt").write_text(
            f'<meta corpus="alpha" title="{name}"{license_attribute}>'
            '<norm_group norm_group="a"><norm xml:id="u1" '
            'new_sent="true" norm="a" lemma="a" pos="N" func="root">a</norm></norm_group>',
            encoding="utf-8",
        )


class LocalLicenseEvidenceTests(unittest.TestCase):
    def test_converter_reports_only_missing_or_blank_license_source_ids(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            _source(source)
            result = convert_source_tree(
                source, root / "direct", upstream_repository="CopticScriptorium/corpora",
                upstream_commit="a" * 40,
            )
            self.assertEqual(
                result.to_dict()["missing_license_metadata_source_records"],
                ["alpha/alpha:empty", "alpha/alpha:missing"],
            )
            self.assertEqual(result.source_records, 3)

    def test_agora_summary_surfaces_same_ids_without_license_verdict(self) -> None:
        from copticscriptorium_tf.agora import main

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            _source(source)
            output = root / "agora"
            output.mkdir()
            self.assertEqual(main([str(source), str(output), "--source-revision", ""]), 0)
            summary = json.loads((output / "conversion-summary.json").read_text(encoding="utf-8"))
            self.assertEqual(
                summary["missing_license_metadata_source_records"],
                ["alpha/alpha:empty", "alpha/alpha:missing"],
            )
            self.assertEqual(summary["upstream_commit"], "unversioned-local")
            self.assertNotIn("license_verdict", summary)
            self.assertNotIn("aggregate_license", summary)


if __name__ == "__main__":
    unittest.main()
