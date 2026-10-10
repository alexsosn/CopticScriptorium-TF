"""Bilateral additive native TF reference-candidate modules for Coptic ↔ LXX.

The shared reference is a candidate address, not a claim of textual or lexical
equivalence. Parent node numbers stay local to their respective TF warp.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1, sha256
from contextlib import ExitStack
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable

from ._atomic import publish_path_no_clobber
from .lxx_reference import resolve_coptic_lxx_references
from .model import DocumentModel

LXX_PIN = "f32a98eddf7eb239aa73ab863d70381e416d5076"
COPTIC_PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"

# Corresponding pinned source-blob identities from CATSS-TF's CenterBLC
# v1.0.1 LXX profile. Never trust a count-compatible wrong Greek edition.
LXX_FEATURE_GIT_BLOBS = {
    "otype": "2e6480116dfda09f20e8de7c5b9feefa76322a96",
    "oslots": "e95696a6a49f1149f8f6e850f7dfb40a26509931",
    "book": "0bfae94bb312cb7ecd33b102babb9400c554d8be",
    "chapter": "ec64b6bf72a6282e9da5064ca2e895171190208e",
    "verse": "ff8766352d7aff530c6eec4f66366adcc691740e",
    "subverse": "cecfaf2d1ddc4fd1e93958abd674a7e60e676ae5",
}


@dataclass(frozen=True, slots=True)
class LxxModuleSummary:
    coptic_candidate_words: int
    lxx_candidate_verses: int
    coptic_status_words: int
    source_documents: int


def verify_lxx_parent_feature_blobs(directory: Path) -> None:
    """Require exact mapping-critical CenterBLC/LXX v1.0.1 TF file bytes."""
    for feature, expected in sorted(LXX_FEATURE_GIT_BLOBS.items()):
        path = directory / f"{feature}.tf"
        if not path.is_file():
            raise ValueError(f"missing pinned LXX feature file {path.name}")
        digest = sha1()
        digest.update(f"blob {path.stat().st_size}\0".encode("ascii"))
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        actual = digest.hexdigest()
        if actual != expected:
            raise ValueError(
                f"pinned LXX feature {feature} Git blob mismatch: expected {expected}, got {actual}"
            )


def fingerprint_coptic_parent(directory: Path) -> str:
    """Fingerprint the generated Coptic warp and source-word identity features.

    The upstream Coptic source Git revision is NOT a commit of the generated
    Text-Fabric parent. Publish this fingerprint so a consumer can verify the
    actual compatible parent data, rather than trusting a mislabelled commit.
    """
    digest = sha256()
    required = (
        "otype", "oslots", "source_record_id", "source_word_ordinal",
        "source_sha256",
    )
    # A module's Coptic correspondence depends on source verse semantics,
    # not merely unchanged word node IDs. Include all source reference
    # literals and precisely positioned marker-event features when present.
    optional = (
        "verse_n", "vid_n", "verse_vid", "value", "event_ordinal",
        "start_word_ordinal", "start_char", "start_after_word_ordinal",
        "end_word_ordinal", "end_char", "end_after_word_ordinal",
    )
    for feature in (*required, *optional):
        path = directory / f"{feature}.tf"
        if not path.is_file():
            if feature in required:
                raise ValueError(f"missing generated Coptic parent TF feature {feature}")
            digest.update(f"{feature}\\0missing\\0".encode("ascii"))
            continue
        digest.update(f"{feature}\\0{path.stat().st_size}\\0".encode("ascii"))
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def verify_coptic_module_parent(module_directory: Path, parent_directory: Path) -> None:
    """Fail closed when a native Coptic reference module has the wrong warp.

    Text-Fabric feature overlays use the existing parent node numbering. A
    source-Git revision alone does not identify the generated TF parent warp.
    """
    module_directory = Path(module_directory)
    modules = sorted(path for path in module_directory.glob("*.tf") if path.is_file())
    if not modules:
        raise ValueError("missing Coptic native reference module TF features")
    actual = fingerprint_coptic_parent(Path(parent_directory))
    expected: str | None = None
    for feature in modules:
        headers: dict[str, str] = {}
        with feature.open(encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    break
                if line.startswith("@") and "=" in line:
                    key, value = line.rstrip("\n").split("=", 1)
                    headers[key] = value
        if headers.get("@parentRepo") != "CopticScriptorium-TF/generated":
            raise ValueError(f"invalid Coptic module parent identity in {feature.name}")
        observed = headers.get("@parentFingerprintSha256")
        if not observed or len(observed) != 64:
            raise ValueError(f"missing Coptic module parent fingerprint in {feature.name}")
        if expected is None:
            expected = observed
        elif observed != expected:
            raise ValueError("conflicting Coptic module parent fingerprints")
    if expected != actual:
        raise ValueError("Coptic module parent fingerprint mismatch")


def _write_feature(
    directory: Path, feature: str, data: dict[int, str], *,
    parent_repo: str, parent_commit: str | None,
    parent_fingerprint: str | None = None,
) -> None:
    if not feature.startswith("coptic_lxx_"):
        raise ValueError("cross-corpus feature must be in coptic_lxx namespace")
    if not data:
        return
    headers = [
        "@node",
        "@valueType=str",
        "@description=Source-evidenced Coptic/LXX reference candidates; not verified textual equivalence",
        "@writtenBy=CopticScriptorium-TF",
        "@referencePolicy=reference_candidate_unverified_versification",
        "@copticSourceCommit=" + COPTIC_PIN,
        "@lxxReleaseCommit=" + LXX_PIN,
        "@parentRepo=" + parent_repo,
    ]
    if parent_commit:
        headers.append("@parentCommit=" + parent_commit)
    if parent_fingerprint:
        headers.append("@parentFingerprintSha256=" + parent_fingerprint)
    headers.append("")
    for node, value in sorted(data.items()):
        if not isinstance(node, int) or isinstance(node, bool) or node <= 0:
            raise ValueError("native TF module node identifiers must be positive ints")
        if not isinstance(value, str) or not value:
            raise ValueError("native TF module feature values must be nonempty strings")
        escaped = value.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n")
        headers.append(f"{node}\t{escaped}")
    (directory / f"{feature}.tf").write_text(
        "\n".join(headers) + "\n", encoding="utf-8"
    )


def _verify_source_parent_record(
    coptic_api: object, word_node: int, source_record_id: str, source_sha256: str,
) -> None:
    """Source bytes must match the actual Coptic parent document, not only IDs.

    Both legacy and streaming projections must join the same original TT
    witness. Its declared upstream Git commit/word offsets alone are not
    sufficient for secure source provenance.
    """
    if not hasattr(coptic_api.F, "source_sha256"):
        raise ValueError("Coptic parent API must load source_sha256")
    if (not isinstance(source_sha256, str) or len(source_sha256) != 64
            or any(character not in "0123456789abcdef"
                   for character in source_sha256)):
        raise ValueError("invalid source SHA-256 on input record")
    parents = tuple(coptic_api.L.u(word_node, otype="document"))
    if len(parents) != 1:
        raise ValueError("Coptic word has no unique parent document")
    parent_node = parents[0]
    if coptic_api.F.source_record_id.v(parent_node) != source_record_id:
        raise ValueError("parent document source record identity mismatch")
    if coptic_api.F.source_sha256.v(parent_node) != source_sha256:
        raise ValueError(
            f"source SHA-256 mismatch between TT input and Coptic TF parent: "
            f"{source_record_id}"
        )


def materialize_lxx_reference_modules(
    *,
    documents: Iterable[DocumentModel],
    coptic_api: object,
    lxx_api: object,
    output_root: Path,
    lxx_parent_commit: str,
    coptic_source_commit: str,
    coptic_parent_tf: Path | None = None,
    lxx_parent_tf: Path | None = None,
    verify_parent_feature_hashes: bool = True,
) -> LxxModuleSummary:
    """Materialize native Coptic-word and LXX-verse reference ID modules.

    The caller provides fully loaded TF APIs for the generated Coptic parent
    warp and actual pinned CenterBLC/LXX parent. No foreign node IDs are
    written into the Coptic module or vice versa.
    """
    if lxx_parent_commit != LXX_PIN:
        raise ValueError("pinned LXX parent commit mismatch")
    if coptic_source_commit != COPTIC_PIN:
        raise ValueError("pinned Coptic source revision mismatch")
    if verify_parent_feature_hashes:
        if lxx_parent_tf is None:
            raise ValueError("missing pinned LXX TF path for Git blob verification")
        verify_lxx_parent_feature_blobs(lxx_parent_tf)

    if coptic_parent_tf is None:
        raise ValueError("missing generated Coptic parent TF path")
    coptic_parent_fingerprint = fingerprint_coptic_parent(Path(coptic_parent_tf))

    if coptic_api is None or lxx_api is None:
        raise ValueError("both parent TF APIs must be loaded")
    lxx_otype = lxx_api.F.otype
    if (
        lxx_otype.maxSlot != 623693 or lxx_otype.maxNode != 685732
        or len(lxx_otype.s("verse")) != 30371
    ):
        raise ValueError("pinned LXX parent node profile mismatch")

    all_coptic_words = tuple(coptic_api.F.otype.s("word"))
    indexed: dict[tuple[str, int], int] = {}
    for node in all_coptic_words:
        key = (
            coptic_api.F.source_record_id.v(node),
            coptic_api.F.source_word_ordinal.v(node),
        )
        if key in indexed:
            raise ValueError(f"duplicate Coptic TF source word identity: {key}")
        indexed[key] = node

    source_docs = tuple(documents)
    if not source_docs or len({d.source_record_id for d in source_docs}) != len(source_docs):
        raise ValueError("need unique nonempty Coptic documents")
    if any(d.upstream_commit != COPTIC_PIN for d in source_docs):
        raise ValueError("source documents do not carry the pinned Coptic revision")

    for document in source_docs:
        first_word = indexed.get((document.source_record_id, 1))
        if first_word is None:
            raise ValueError("missing Coptic parent TF first word for source document")
        _verify_source_parent_record(
            coptic_api, first_word, document.source_record_id, document.source_sha256,
        )

    source_values: dict[str, dict[int, str]] = {
        "coptic_lxx_ref_id": {},
        "coptic_lxx_ref_status": {},
        "coptic_lxx_ref_evidence": {},
        "coptic_lxx_ref_reason": {},
    }
    target_ids: dict[int, str] = {}
    seen_coptic: set[int] = set()

    def lxx_lookup(book: str, chapter: int, verse: int) -> int | None:
        node = lxx_api.T.nodeFromSection((book, chapter, verse))
        if node is None:
            return None
        if lxx_otype.v(node) != "verse":
            raise ValueError("Greek parent verse address resolved to non-verse node")
        return node

    for doc in source_docs:
        for mapping in resolve_coptic_lxx_references(doc, lookup=lxx_lookup):
            if mapping.lxx_node is not None:
                assert mapping.shared_id is not None
                old = target_ids.setdefault(mapping.lxx_node, mapping.shared_id)
                if old != mapping.shared_id:
                    raise ValueError("conflicting shared IDs for one Greek verse")
            for ordinal in mapping.source_word_ordinals:
                word_node = indexed.get((doc.source_record_id, ordinal))
                if word_node is None:
                    raise ValueError(
                        f"missing Coptic parent TF word: {(doc.source_record_id, ordinal)}"
                    )
                if word_node in seen_coptic:
                    raise ValueError(f"Coptic word assigned to multiple mappings: {word_node}")
                seen_coptic.add(word_node)
                source_values["coptic_lxx_ref_status"][word_node] = mapping.status
                source_values["coptic_lxx_ref_evidence"][word_node] = mapping.evidence
                source_values["coptic_lxx_ref_reason"][word_node] = mapping.reason
                if mapping.shared_id is not None:
                    source_values["coptic_lxx_ref_id"][word_node] = mapping.shared_id

    expected_coptic_words = sum(len(d.words) for d in source_docs)
    if len(seen_coptic) != expected_coptic_words:
        raise ValueError(
            f"incomplete source-word projection: {len(seen_coptic)} / {expected_coptic_words}"
        )

    output_root = Path(output_root)
    if output_root.exists():
        raise ValueError(f"destination already exists: {output_root}")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".coptic-lxx-", dir=output_root.parent) as staging:
        root = Path(staging) / "payload"
        coptic_module = root / "coptic"
        lxx_module = root / "lxx"
        coptic_module.mkdir(parents=True)
        lxx_module.mkdir(parents=True)
        for feature, values in source_values.items():
            _write_feature(
                coptic_module, feature, values,
                parent_repo="CopticScriptorium-TF/generated",
                parent_commit=None, parent_fingerprint=coptic_parent_fingerprint,
            )
        _write_feature(
            lxx_module, "coptic_lxx_ref_id", target_ids,
            parent_repo="CenterBLC/LXX", parent_commit=LXX_PIN,
        )
        root.rename(output_root)

    return LxxModuleSummary(
        coptic_candidate_words=len(source_values["coptic_lxx_ref_id"]),
        lxx_candidate_verses=len(target_ids),
        coptic_status_words=len(source_values["coptic_lxx_ref_status"]),
        source_documents=len(source_docs),
    )


def _stream_tf_header(handle, *, parent_repo: str, parent_commit: str | None,
                      fingerprint: str | None = None) -> None:
    """Same plain native TF header as _write_feature; no map allocation."""
    header = [
        "@node", "@valueType=str",
        "@description=Source-evidenced Coptic/LXX reference candidates; not verified textual equivalence",
        "@writtenBy=CopticScriptorium-TF",
        "@referencePolicy=reference_candidate_unverified_versification",
        "@copticSourceCommit=" + COPTIC_PIN,
        "@lxxReleaseCommit=" + LXX_PIN,
        "@parentRepo=" + parent_repo,
    ]
    if parent_commit:
        header.append("@parentCommit=" + parent_commit)
    if fingerprint:
        header.append("@parentFingerprintSha256=" + fingerprint)
    handle.write("\n".join((*header, "")) + "\n")


def _stream_tf_row(handle, node: int, value: str) -> None:
    if not isinstance(node, int) or isinstance(node, bool) or node <= 0:
        raise ValueError("invalid native TF node ID")
    if not isinstance(value, str) or not value:
        raise ValueError("invalid empty native TF scalar")
    escaped = value.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n")
    handle.write(f"{node}\t{escaped}\n")


def materialize_lxx_reference_modules_streaming(
    *, documents: Iterable[DocumentModel], coptic_api: object, lxx_api: object,
    output_root: Path, lxx_parent_commit: str, coptic_source_commit: str,
    coptic_parent_tf: Path | None = None, lxx_parent_tf: Path | None = None,
    verify_parent_feature_hashes: bool = True,
) -> LxxModuleSummary:
    """Stream one-pass unsorted source records into immutable bilateral TF wefts.

    Store only interval facts in an ephemeral SQLite index, then scan the Coptic
    parent word nodes in numeric order and immediately emit TF feature lines.
    SQLite staging is deleted; it is never a persistent corpus sidecar.
    """
    if lxx_parent_commit != LXX_PIN:
        raise ValueError("pinned LXX parent commit mismatch")
    if coptic_source_commit != COPTIC_PIN:
        raise ValueError("pinned Coptic source revision mismatch")
    if verify_parent_feature_hashes:
        if lxx_parent_tf is None:
            raise ValueError("missing pinned LXX TF path for Git blob verification")
        verify_lxx_parent_feature_blobs(Path(lxx_parent_tf))
    if coptic_parent_tf is None or coptic_api is None or lxx_api is None:
        raise ValueError("missing generated Coptic parent TF path or loaded APIs")
    fp = fingerprint_coptic_parent(Path(coptic_parent_tf))
    if not hasattr(coptic_api.F, "source_sha256"):
        raise ValueError("Coptic parent API must load source_sha256 for source identity verification")
    greek_otype = lxx_api.F.otype
    if (greek_otype.maxSlot, greek_otype.maxNode, len(greek_otype.s("verse"))) != (
        623693, 685732, 30371
    ):
        raise ValueError("pinned LXX parent node profile mismatch")
    root = Path(output_root)
    if root.exists() or root.is_symlink():
        raise ValueError(f"destination already exists: {root}")
    root.parent.mkdir(parents=True, exist_ok=True)

    def lookup(book: str, chapter: int, verse: int) -> int | None:
        node = lxx_api.T.nodeFromSection((book, chapter, verse))
        if node is not None and greek_otype.v(node) != "verse":
            raise ValueError("Greek parent verse address resolved to non-verse node")
        return node

    with TemporaryDirectory(prefix=".coptic-lxx-", dir=root.parent) as temp:
        db = sqlite3.connect(Path(temp) / "index.sqlite")
        try:
            db.executescript("""
                CREATE TABLE docs(record TEXT PRIMARY KEY, folded TEXT UNIQUE, words INT, sha TEXT);
                CREATE TABLE spans(record TEXT, start INT, stop INT, status TEXT,
                                   evidence TEXT, reason TEXT, ref TEXT,
                                   PRIMARY KEY(record,start));
            """)
            greek_refs: dict[int, str] = {}
            n_docs = n_words = 0
            for document in documents:
                if (document.upstream_repository != "CopticScriptorium/corpora"
                        or document.upstream_commit != COPTIC_PIN):
                    raise ValueError("source documents do not carry the pinned Coptic revision")
                if any(w.ordinal != i for i, w in enumerate(document.words, 1)):
                    raise ValueError("noncontiguous source ordinals")
                if (not isinstance(document.source_sha256, str)
                        or len(document.source_sha256) != 64
                        or any(char not in "0123456789abcdef"
                               for char in document.source_sha256)):
                    raise ValueError("invalid source SHA-256 on input record")
                try:
                    db.execute("INSERT INTO docs VALUES (?,?,?,?)", (
                        document.source_record_id, document.source_record_id.casefold(),
                        len(document.words), document.source_sha256))
                except sqlite3.IntegrityError as exc:
                    raise ValueError("duplicate or casefold-colliding source record") from exc
                n_docs += 1
                n_words += len(document.words)
                previous = 0
                for m in resolve_coptic_lxx_references(document, lookup=lookup):
                    ords = m.source_word_ordinals
                    if (not ords or ords[0] != previous + 1
                            or ords != tuple(range(ords[0], ords[-1] + 1))):
                        raise ValueError("noncontiguous or overlapping source verse span")
                    previous = ords[-1]
                    if m.status == "reference_candidate":
                        if m.shared_id is None or m.lxx_node is None:
                            raise ValueError("candidate lacks Greek reference")
                        prior = greek_refs.setdefault(m.lxx_node, m.shared_id)
                        if prior != m.shared_id:
                            raise ValueError("conflicting Greek reference identity")
                    elif m.shared_id is not None or m.lxx_node is not None:
                        raise ValueError("noncandidate claims Greek reference")
                    db.execute("INSERT INTO spans VALUES (?,?,?,?,?,?,?)", (
                        document.source_record_id, ords[0], ords[-1], m.status,
                        m.evidence, m.reason, m.shared_id))
                if previous != len(document.words):
                    raise ValueError("incomplete source word/reference partition")
            if not n_docs:
                raise ValueError("need unique nonempty Coptic documents")
            if n_words != coptic_api.F.otype.maxSlot:
                raise ValueError("source word count does not match Coptic parent")
            db.commit()
            payload = Path(temp) / "payload"
            coptic_path = payload / "coptic"
            greek_path = payload / "lxx"
            coptic_path.mkdir(parents=True)
            greek_path.mkdir(parents=True)
            feature_names = (
                "coptic_lxx_ref_id", "coptic_lxx_ref_status",
                "coptic_lxx_ref_evidence", "coptic_lxx_ref_reason",
            )
            current_record = None
            last_ordinal = expected_doc_words = last_node = 0
            seen_docs: set[str] = set()
            spans = iter(())
            active = None
            status_words = candidate_words = 0
            with ExitStack() as stack:
                handles = {
                    feature: stack.enter_context(
                        (coptic_path / f"{feature}.tf").open("w", encoding="utf-8")
                    ) for feature in feature_names
                }
                for handle in handles.values():
                    _stream_tf_header(
                        handle, parent_repo="CopticScriptorium-TF/generated",
                        parent_commit=None, fingerprint=fp)
                for node in coptic_api.F.otype.s("word"):
                    if node <= last_node:
                        raise ValueError("Coptic parent slots are not strictly increasing")
                    last_node = node
                    record = coptic_api.F.source_record_id.v(node)
                    ordinal = coptic_api.F.source_word_ordinal.v(node)
                    if record != current_record:
                        if current_record is not None and last_ordinal != expected_doc_words:
                            raise ValueError("incomplete Coptic parent word span")
                        if record in seen_docs:
                            raise ValueError("noncontiguous Coptic TF document word span")
                        row = db.execute(
                            "SELECT words, sha FROM docs WHERE record=?", (record,)
                        ).fetchone()
                        if row is None:
                            raise ValueError("missing source document in Coptic parent")
                        _verify_source_parent_record(coptic_api, node, record, row[1])
                        seen_docs.add(record)
                        current_record = record
                        expected_doc_words = row[0]
                        last_ordinal = 0
                        spans = iter(db.execute(
                            "SELECT start,stop,status,evidence,reason,ref "
                            "FROM spans WHERE record=? ORDER BY start",
                            (record,)).fetchall())
                        active = next(spans, None)
                    if ordinal != last_ordinal + 1:
                        raise ValueError("parent source ordinal gap or duplicate")
                    if active is None:
                        raise ValueError("source reference interval missing")
                    if ordinal > active[1]:
                        active = next(spans, None)
                    if active is None or not (active[0] <= ordinal <= active[1]):
                        raise ValueError("source reference interval mismatch")
                    last_ordinal = ordinal
                    status, evidence, reason, ref = active[2:]
                    for feature, value in (
                        ("coptic_lxx_ref_status", status),
                        ("coptic_lxx_ref_evidence", evidence),
                        ("coptic_lxx_ref_reason", reason),
                    ):
                        _stream_tf_row(handles[feature], node, value)
                    if ref is not None:
                        if status != "reference_candidate":
                            raise ValueError("noncandidate source word has reference ID")
                        _stream_tf_row(handles["coptic_lxx_ref_id"], node, ref)
                        candidate_words += 1
                    status_words += 1
            if (current_record is None or last_ordinal != expected_doc_words
                    or len(seen_docs) != n_docs or status_words != n_words):
                raise ValueError("incomplete Coptic TF/source document bijection")
            _write_feature(
                greek_path, "coptic_lxx_ref_id", greek_refs,
                parent_repo="CenterBLC/LXX", parent_commit=LXX_PIN)
            publish_path_no_clobber(payload, root)
            return LxxModuleSummary(
                coptic_candidate_words=candidate_words,
                lxx_candidate_verses=len(greek_refs),
                coptic_status_words=status_words, source_documents=n_docs)
        finally:
            db.close()
