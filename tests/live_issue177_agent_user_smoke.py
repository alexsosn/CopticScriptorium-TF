"""Issue #177: autonomous agent's installed-user journey over pinned real TT.

No implementation modules imported: operate only the README CLI, browser
launcher and normal Text-Fabric interface. Report metadata/counts only.
"""
from __future__ import annotations

from hashlib import sha256
from html.parser import HTMLParser
from importlib.resources import files as resource_files
from threading import Thread
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from tf.browser.web import setup as setup_browser
from werkzeug.serving import make_server
import json
from pathlib import Path
import re
import subprocess
import sys
import unicodedata

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


def _safe_coptic_lemma_query(value: str) -> str | None:
    """Allow one original Coptic-script lemma literal, without TF meta syntax.

    No normalization, transliteration or guessed forms: reject whitespace,
    punctuation, digits and regex/query syntax; combining marks are retained.
    """
    if not value:
        return None
    if not all(ch.isalpha() or unicodedata.category(ch).startswith("M") for ch in value):
        return None
    if not any("\u2c80" <= ch <= "\u2cff" or "\u03e2" <= ch <= "\u03ef" for ch in value):
        return None
    return f"word lemma={value}"


class _ContextAnchorParser(HTMLParser):
    """Inspect only Text-Fabric's original search-result context anchors."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.sections: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        values = dict(attrs)
        if "pq" not in (values.get("class") or "").split():
            return
        if values.get("href") != "#" or not values.get("sec0"):
            raise ValueError("browser result context anchor is malformed")
        self.sections.append(values["sec0"])


def _first_context_section(html: str, expected_documents: set[str]) -> str:
    """Extract an actual physical document from a TF context action, not href."""
    anchors = _ContextAnchorParser()
    anchors.feed(html)
    anchors.close()
    if not anchors.sections:
        raise ValueError("browser has no real source-context result link")
    if not set(anchors.sections) <= expected_documents:
        raise ValueError("browser context links disagree with original TF sections")
    return anchors.sections[0]


def browser_http_smoke(
    tf_root: Path, expected_words: int, *,
    filtered_query: str, filtered_expected: int,
    lemma_query: str, lemma_expected: int,
    expected_documents: set[str],
) -> dict[str, object]:
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
    routes = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/query" in routes and "/passage" in routes, (
        "installed browser lacks real researcher search/passage endpoint"
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

        # Exercise the actual public browser twice: a baseline 'word' query
        # and one constrained native POS query from the pinned original text.
        results = {}
        passage_section = None
        for query, expected, key in (
            ("word", expected_words, "http_browser_result_count"),
            (filtered_query, filtered_expected, "http_browser_filtered_result_count"),
            (lemma_query, lemma_expected, "http_browser_lemma_result_count"),
        ):
            encoded = urlencode({
                "query": query, "batch": "5", "condenseType": "document",
            }).encode("utf-8")
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
                "browser rejected source-attested researcher query"
            )
            assert payload.get("nResults") == expected, (
                "browser result count disagrees with the same native TF query"
            )
            table = payload.get("table")
            assert isinstance(table, str) and "<" in table, (
                "browser reported count but failed to render result markup"
            )
            if query != "word":
                assert "href=" in table, (
                    "browser returned constrained hits but no navigable result links"
                )
            if query == lemma_query:
                passage_section = _first_context_section(table, expected_documents)
            results[key] = payload["nResults"]

        assert passage_section is not None, (
            "source-attested Coptic lemma query has no section context"
        )
        # The result's href="#" is a JavaScript action: request the actual
        # upstream Text-Fabric passage endpoint using its source sec0 label.
        encoded = urlencode({"sec0": passage_section, "query": lemma_query}).encode("utf-8")
        request = Request(
            address + "/passage",
            data=encoded,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urlopen(request, timeout=90) as response:
            passage_payload = json.loads(response.read(12_000_000))
            assert response.status == 200, "browser passage request returned non-200"
        assert isinstance(passage_payload, dict), "browser passage was not JSON"
        passage_html = passage_payload.get("table")
        assert isinstance(passage_html, str) and "<" in passage_html, (
            "source-selected document has no rendered passage"
        )

        return {
            "http_browser_home": "pass",
            "http_browser_passage": "pass",
            "http_browser_passage_section_sha256": sha256(
                passage_section.encode("utf-8")
            ).hexdigest(),
            "http_browser_search": "pass",
            "http_browser_query": "word",
            "http_browser_filtered_query": filtered_query,
            "http_browser_lemma_query_sha256": sha256(lemma_query.encode("utf-8")).hexdigest(),
            "http_browser_loopback_only": True,
            **results,
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

    # Choose an actual original POS value, not a guessed Coptic lemma or
    # synthetic fixture. Keep only a simple, unambiguous TF query literal.
    source_pos = next((
        value for w in words
        if (value := api.F.pos.v(w))
        and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", value)
    ), None)
    assert source_pos is not None, "real corpus has no queryable simple POS"
    pos_query = f"word pos={source_pos}"
    native_pos_hits = tuple(api.S.search(pos_query, silent="deep"))
    assert native_pos_hits, "native TF researcher POS search returned no hits"
    assert all(len(hit) == 1 for hit in native_pos_hits)
    assert {hit[0] for hit in native_pos_hits} == set(api.F.pos.s(source_pos)), (
        "TF search and indexed word POS disagree on the installed real source"
    )

    # A researcher also needs to search actual Coptic Unicode lexical forms.
    # Only use a source-attested, syntax-safe Coptic lemma. Keep its literal
    # private to the in-process query; report only a hash and aggregate counts.
    lemma_query = next((
        query for w in words
        if (value := api.F.lemma.v(w))
        if (query := _safe_coptic_lemma_query(value)) is not None
    ), None)
    assert lemma_query is not None, "real corpus has no safe Coptic-script lemma"
    source_lemma = lemma_query.split("=", 1)[1]
    native_lemma_hits = tuple(api.S.search(lemma_query, silent="deep"))
    assert native_lemma_hits, "native TF Unicode lemma search returned no hits"
    assert all(len(hit) == 1 for hit in native_lemma_hits)
    assert {hit[0] for hit in native_lemma_hits} == set(api.F.lemma.s(source_lemma)), (
        "TF Search and inverse original Coptic lemma index disagree"
    )

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
    http_result = browser_http_smoke(
        root, api.F.otype.maxSlot,
        filtered_query=pos_query, filtered_expected=len(native_pos_hits),
        lemma_query=lemma_query, lemma_expected=len(native_lemma_hits),
        expected_documents=set(by_id),
    )

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
        "native_pos_query": pos_query,
        "native_pos_query_hits": len(native_pos_hits),
        "native_lemma_query_sha256": sha256(lemma_query.encode("utf-8")).hexdigest(),
        "native_lemma_query_hits": len(native_lemma_hits),
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
