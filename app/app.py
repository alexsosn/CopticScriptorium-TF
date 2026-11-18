"""Local Text-Fabric 13.1 browser compatibility for one section level.

The native corpus has exactly one real section kind: physical document.
Text-Fabric's standard search-result link formatter assumes a second section
kind for word/annotation nodes, raising IndexError during HTTP query rendering.
Keep the native TF warp and all physical source identities unchanged. Only the
browser app's in-memory section-tuple lookup and its single-section passage
handler are adapted for this exact one-level model; multi-level Text-Fabric
corpora retain upstream behavior.
"""
from __future__ import annotations

from types import MethodType

from tf.advanced.app import App
from tf.advanced.tables import composeP


def _native_document_node(api, node):
    """Resolve the one real physical document without inventing section levels."""
    if api.F.otype.v(node) == "document":
        document = node
    else:
        enclosing = tuple(api.L.u(node, otype="document"))
        if len(enclosing) != 1:
            raise ValueError("browser node has no unique enclosing document")
        document = enclosing[0]
    literal = api.F.source_record_id.v(document)
    if not isinstance(literal, str) or not literal:
        raise ValueError("browser section is missing physical document label")
    return document


def _install_one_level_adapter(app):
    """Patch only this app's in-memory TF section lookup; preserve native warp."""
    api = getattr(app, "api", None)
    if api is None:
        return
    section_types = tuple(api.T.sectionTypes)
    if section_types != ("document",):
        return
    if tuple(api.T.sectionFeats) != ("source_record_id",):
        raise ValueError("one-level document browser requires source_record_id section feature")

    # Text-Fabric 13.1.0's sectionTuple indexes sectionTypes[1] for a word or
    # annotation even when exactly one level exists. Standard browser results
    # call T.sectionFromNode → sectionTuple directly, not only app links.
    # The native T.nodeFromSection and original TF section data stay intact.
    def native_single_section_tuple(node, lastSlot=False, fillup=False):
        return (_native_document_node(api, node),)

    api.T.sectionTuple = native_single_section_tuple



def _single_section_passage(
    kernel, features, query, sec0, sec1=None, sec2=None,
    opened=frozenset(), getx=None, **options,
):
    """Render one genuine document via TF's own display, not fictitious verses.

    Text-Fabric 13.1.0's default passage handler unconditionally indexes
    sectionTypes[1] and fails on a valid one-level native TF corpus. The
    standard upstream composeP renderer already supports index level zero.
    """
    app = kernel.app
    api = app.api
    T = api.T
    labels = tuple(T.sectionFromNode(d)[0] for d in api.F.otype.s("document"))
    document = (
        T.nodeFromSection((sec0,))
        if sec0 and not sec1 and not sec2 else None
    )
    if document is None:
        return ("", "document", (labels, ()), 0)
    if api.F.otype.v(document) != "document":
        raise ValueError("browser source passage did not resolve to a document")
    if api.F.source_record_id.v(document) != sec0:
        raise ValueError("browser source passage label disagrees with native TF")
    rendered = composeP(
        app, 0, "document", features, (document,),
        opened, sec0, getx=getx, **options,
    )
    return (rendered, "document", (labels, ()), 0)


def _install_one_level_passage_kernel_adapter():
    """Restrict a TF 13.1.0 browser handler fix to this corpus app only."""
    from tf.browser import web as browser_web

    previous = browser_web.makeTfKernel
    if getattr(previous, "_coptic_one_level_passage", False):
        return

    def with_coptic_single_document_passage(app, app_name):
        kernel = previous(app, app_name)
        if (
            isinstance(app, TfApp)
            and tuple(app.api.T.sectionTypes) == ("document",)
            and tuple(app.api.T.sectionFeats) == ("source_record_id",)
        ):
            kernel.passage = MethodType(_single_section_passage, kernel)
        return kernel

    with_coptic_single_document_passage._coptic_one_level_passage = True
    browser_web.makeTfKernel = with_coptic_single_document_passage


class TfApp(App):
    """Standard TF app with source-faithful one-section browser compatibility."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _install_one_level_adapter(self)
        if getattr(self, "_browse", False) and tuple(self.api.T.sectionTypes) == ("document",):
            _install_one_level_passage_kernel_adapter()
