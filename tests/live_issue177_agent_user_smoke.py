"""Issue #177: autonomous agent's installed-user journey over pinned real TT.

No implementation modules imported: operate only the README CLI, browser
launcher and normal Text-Fabric interface. Report metadata/counts only.
"""
from __future__ import annotations

from hashlib import sha256
from importlib.resources import files as resource_files
from threading import Thread
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from tf.browser.web import setup as setup_browser
from werkzeug.serving import make_server
import json
from pathlib import Path
import subprocess
import sys

from tf.fabric import Fabric

PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
UPSTREAM = "CopticScriptorium/corpora"
THOMAS = "thomas-gospel/thomas.gospel_TT/thomas_gospel.tt"
PISTIS = "pistis-sophia/pistis.sophia_TT/pistis.sophia_book_1_part1.tt"
THOMAS_ID = "thomas-gospel/thomas.gospel:thomas_gospel"
PISTIS_ID = "pistis-sophia/pistis.sophia:pistis.sophia_book_1_part1"
# CONLLU supplementation is intentionally absent: this tests the public TT
# source-only installation path, not the previously verified augmented corpus.


def run(argv: list[str], *, workdir: Path, expected: int = 0) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        argv, cwd=workdir, capture_output=True, text=True,
        check=False, timeout=420,
    )
    if expected == 0 and proc.returncode != 0:
        raise RuntimeError(
            "installed public command failed, exit="
            + str(proc.returncode) + ": " + Path(argv[0]).name
            + "; stderr_sha256=" + sha256(proc.stderr.encode("utf-8", "replace")).hexdigest()[:16]
        )
    if expected != 0 and proc.returncode == 0:
        raise AssertionError("invalid user input unexpectedly succeeded")
    return proc


def browser_http_smoke(tf_root: Path, expected_words: int) -> dict[str, object]:
    """Use the installed TF browser over real loopback HTTP, no converter imports.

    The response is examined privately; only status and counts are returned.
    """
    installed_app = resource_files("copticscriptorium_tf").joinpath("tf_app")
    assert installed_app.joinpath("config.yaml").is_file(), (
        "the installed wheel omitted the actual browser application"
    )
    app = setup_browser(
        False,
        f"app:{installed_app}",
        f"--locations={tf_root}",
        "--modules=.",
    )
    assert app is not None, "standard TF browser app initialization failed"
    assert "/query" in {rule.rule for rule in app.url_map.iter_rules()}, (
        "installed app has no researcher /query endpoint"
    )
    server = make_server("127.0.0.1", 0, app)
    service = Thread(target=server.serve_forever, daemon=True)
    service.start()
    address = f"http://127.0.0.1:{server.server_port}"
    try:
        # Load the page that would be presented to the local researcher.
        with urlopen(address + "/", timeout=45) as response:
            page = response.read(2_000_000)
            assert response.status == 200, "local TF page returned non-200"
            assert "text/html" in response.headers.get("Content-Type", ""), (
                "local TF home page was not rendered as HTML"
            )
        assert b"<html" in page.lower(), "browser homepage has no HTML skeleton"

        # Submit through the actual TF browser query handler. The source page
        # and Coptic word text must not be printed, persisted or uploaded.
        encoded = urlencode({"query": "word", "batch": "5", "condenseType": "document"}).encode("ascii")
        request = Request(
            address + "/query",
            data=encoded,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urlopen(request, timeout=90) as response:
            payload = json.loads(response.read(2_000_000))
            assert response.status == 200, "browser query returned non-200"
        assert isinstance(payload, dict), "browser query did not return JSON"
        assert payload.get("status") is True, (
            "browser rejected valid user query, without exposing response text"
        )
        assert payload.get("nResults") == expected_words, (
            "TF browser query count disagrees with independent native word slots"
        )
        assert isinstance(payload.get("table"), str) and "<" in payload["table"], (
            "browser has a count but did not render native result markup"
        )
        return {
            "http_browser_home": "pass",
            "http_browser_search": "pass",
            "http_browser_result_count": payload["nResults"],
            "http_browser_query": "word",
            "http_browser_loopback_only": True,
        }
    finally:
        server.shutdown()
        service.join(timeout=15)
        server.server_close()
        assert not service.is_alive(), "browser server did not shut down"


def main(source: Path, bin_dir: Path, scratch: Path) -> None:
    source = source.resolve(strict=True)
    bin_dir = bin_dir.resolve(strict=True)
    scratch = scratch.resolve()
    scratch.mkdir(parents=True, exist_ok=False)
    files = {THOMAS: source / THOMAS, PISTIS: source / PISTIS}
    for path in files.values():
        assert path.is_file(), path
    assert files[THOMAS].stat().st_size == 1474064, "pinned real Thomas bytes drift"
    original_sha = {
        THOMAS_ID: sha256(files[THOMAS].read_bytes()).hexdigest(),
        PISTIS_ID: sha256(files[PISTIS].read_bytes()).hexdigest(),
    }
    root = scratch / "output-tf"
    summary = scratch / "conversion-summary.json"
    cli = str(bin_dir / "copticscriptorium-tf")
    browser = str(bin_dir / "copticscriptorium-tf-web")

    # The installed commands are invoked outside the repository checkout;
    # this is the same public path described in README.md.
    run([cli, "--help"], workdir=scratch)
    run([
        cli, str(source), str(root),
        "--upstream-repository", UPSTREAM,
        "--upstream-commit", PIN,
        "--summary", str(summary),
    ], workdir=scratch)
    result = json.loads(summary.read_text(encoding="utf-8"))
    # Converter summaries intentionally contain operational metrics only:
    # the immutable source commit is verified by the checkout and the CLI
    # argument; actual native document source digests are checked below.
    assert result["slots"] > 6521
    assert result["source_records"] == 2, result["source_records"]
    for kind in ("otype.tf", "oslots.tf", "otext.tf"):
        assert (root / kind).is_file(), kind
    assert not list(root.glob("*.json"))
    assert not list(root.glob("*.xml"))

    # Researcher-facing plain native TF, no source parser/graph module imported.
    api = Fabric(locations=[str(root)], silent="deep").load(
        "norm lemma pos source_record_id source_word_ordinal source_sha256 "
        "own_text value render_mode dependency_head", silent="deep"
    )
    assert api, "installed native TF failed to reload"
    assert api.F.otype.maxSlot > 6521
    doc_nodes = api.F.otype.s("document")
    assert len(doc_nodes) == 2
    by_id = {api.F.source_record_id.v(d): d for d in doc_nodes}
    assert set(by_id) == {THOMAS_ID, PISTIS_ID}, set(by_id)
    for source_id, doc in by_id.items():
        assert api.T.nodeFromSection((source_id,)) == doc
        assert api.F.source_sha256.v(doc) == original_sha[source_id]
        # The public formatter reconstructs Coptic words, without extra
        # fabricated slots for original TT annotation wrapper events.
        assert api.T.text(doc, fmt="text-orig-full").strip()

    words = api.F.otype.s("word")
    sample = next((w for w in words if api.F.lemma.v(w) and api.F.pos.v(w)), None)
    assert sample is not None, "installed corpus has no queryable lemma/POS"
    lemma = api.F.lemma.v(sample)
    lemma_hits = tuple(api.F.lemma.s(lemma))
    assert sample in lemma_hits and lemma_hits
    assert any(api.E.dependency_head.f(w) for w in words), "native syntax was lost"

    horner = api.F.otype.s("trans_horner")
    assert len(horner) == 162, len(horner)
    assert all(api.F.source_record_id.v(n) == PISTIS_ID for n in horner)
    assert all(api.F.render_mode.v(n) == "horner_span" for n in horner)
    assert all(api.F.value.v(n) and tuple(api.E.oslots.s(n)) for n in horner)
    translation = tuple(
        n for n in api.F.otype.s("translation")
        if api.F.source_record_id.v(n) == PISTIS_ID
    )
    assert translation
    assert api.F.value.v(horner[0]) != api.T.text(translation[0]), (
        "two distinct original English translation witnesses collapsed"
    )

    run([browser, str(root), "--check"], workdir=scratch)
    http_result = browser_http_smoke(root, api.F.otype.maxSlot)

    # Negative real installed CLI journey: no phantom native corpus published.
    empty = scratch / "empty-original-tree"
    empty.mkdir()
    denied = scratch / "bad-output-tf"
    bad = run([
        cli, str(empty), str(denied), "--upstream-repository", UPSTREAM,
        "--upstream-commit", PIN,
    ], workdir=scratch, expected=1)
    assert "no supported TT source records" in bad.stderr, (
        "unhelpful error for empty source tree; return code=" + str(bad.returncode)
    )
    assert not denied.exists(), "misleading partial TF published on failure"

    # Never log original Coptic text or English translation literals.
    print(json.dumps({
        "status": "PASS installed-user real-source CLI/TF/browser/negative smoke",
        "pinned_source_commit": PIN,
        "source_record_count": result["source_records"],
        "canonical_word_slots": api.F.otype.maxSlot,
        "coptic_document_sections": len(by_id),
        "source_sha256_parity": True,
        "horner_source_witness_nodes": len(horner),
        "separate_original_english_translation_nodes": len(translation),
        "lemma_inverse_hits": len(lemma_hits),
        "native_dependency_query": True,
        "normalized_text_format": "text-orig-full",
        "browser_check": "pass",
        **http_result,
        "missing_tt_error": "actionable_no_partial_output",
        "mode": "TT-only; original CONLLU absent",
    }, sort_keys=True))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: live_issue177_agent_user_smoke.py PINNED_TT_SOURCE WHEEL_BIN TEMP_OUTPUT")
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
