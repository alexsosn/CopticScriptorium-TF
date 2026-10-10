"""Live #17 acceptance: real pinned TT -> network-denied Agora -> native TF.

Run from the CopticScriptorium-TF repository root after installing the project
and checking out merged Agora at .reference/agora. This is intentionally not a
unit test or an offline fixture: it fetches GitHub's pinned upstream TT blob.

It proves representative real-source acquisition and conversion, not complete
full-corpus conversion nor registered-by-ID runtime installation.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from tf.fabric import Fabric

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str((ROOT / ".reference/agora").resolve()))

from scripts.agora_materialize import (  # noqa: E402
    acquire_git_source,
    load_manifest,
    materialize,
    select_materializer,
)

COMMIT = "3ac067f1709a0012daf39ea8da2fac79980176a5"
THOMAS = "thomas-gospel/thomas.gospel_TT/thomas_gospel.tt"
THOMAS_BYTES = 1474064


def main() -> None:
    manifest_path = ROOT / "agora.materializer.json"
    spec = select_materializer(
        load_manifest(manifest_path), "copticscriptorium-text-fabric"
    )
    strategy = next(
        item for item in spec["acquisition"] if item["type"] == "git"
    )
    assert strategy["url"] == "https://github.com/CopticScriptorium/corpora.git"
    assert strategy["ref"] == COMMIT
    assert strategy["sparse_patterns"] == ["/*/*_TT/**", "/*/*_TT.zip"]
    assert spec["execution"]["network"] == "deny"

    # Restrict the live acceptance to one *real* blob, while preserving the
    # same upstream immutable commit, host acquisition and converter runtime.
    # Full 565-blob path/size completeness is a separate passing Agora CI gate.
    selection = {
        **strategy,
        "sparse_patterns": ["/thomas-gospel/thomas.gospel_TT/**"],
    }
    prepared = acquire_git_source(selection, spec)
    try:
        assert prepared.provenance["type"] == "git"
        assert prepared.provenance["resolved_commit"] == COMMIT
        source_record = prepared.path / THOMAS
        assert source_record.is_file()
        assert source_record.stat().st_size == THOMAS_BYTES

        with tempfile.TemporaryDirectory(prefix="issue17-real-thomas-") as td:
            output = Path(td) / "materialized"
            materialize(
                manifest_path=manifest_path,
                materializer_id="copticscriptorium-text-fabric",
                source=prepared.path,
                output=output,
                sandbox="required",
            )
            receipt = json.loads(
                (output / "agora-materialization.json").read_text(encoding="utf-8")
            )
            summary = json.loads(
                (output / "conversion-summary.json").read_text(encoding="utf-8")
            )
            assert receipt["sandbox"] == "bubblewrap"
            # This is an explicit host source override of a verified Git tree,
            # so the *materialization* receipt correctly says user-local.
            assert receipt["source"]["type"] == "user-local"
            assert receipt["source"]["resolved_commit"] == COMMIT
            assert summary["upstream_commit"] == COMMIT
            assert summary["source_records"] == 1

            tf_dir = output / "tf"
            assert all((tf_dir / feature).is_file() for feature in
                       ("otype.tf", "oslots.tf", "otext.tf"))
            api = Fabric(locations=[str(tf_dir)], silent="deep").load(
                "norm lemma pos source_record_id", silent="deep"
            )
            assert api
            assert api.F.otype.maxSlot > 100
            words = api.F.otype.s("word")
            assert words
            assert any(api.F.lemma.v(word) for word in words)
            print(
                "PASS real pinned Gospel of Thomas TT through Agora sandbox "
                f"to native TF: commit={COMMIT}, "
                f"source_records={summary['source_records']}, "
                f"slots={api.F.otype.maxSlot}"
            )
    finally:
        prepared.cleanup()


if __name__ == "__main__":
    main()
