"""Local Text-Fabric 13.1 browser compatibility for one section level.

The native corpus has exactly one real section kind: physical document.
Text-Fabric's standard search-result link formatter assumes a second section
kind for word/annotation nodes, raising IndexError during HTTP query rendering.
Keep the native TF warp and all physical source identities unchanged. Only the
browser app's string-link formatter is overridden for this exact one-level
model; multi-level Text-Fabric corpora use the untouched standard formatter.
"""
from __future__ import annotations

from types import MethodType

from tf.advanced.app import App


def _original_document_section(app, node, *, lang="en", lastSlot=False,
                               fillup=False, level=None):
    """Return the real source-record label containing one native TF node."""
    api = app.api
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
    return literal


def _install_one_level_adapter(app):
    """Do not patch Text-Fabric core or change section identity/slot metadata."""
    api = getattr(app, "api", None)
    if api is None:
        return
    section_types = tuple(api.T.sectionTypes)
    if section_types != ("document",):
        return
    if tuple(api.T.sectionFeats) != ("source_record_id",):
        raise ValueError("one-level document browser requires source_record_id section feature")
    app.sectionStrFromNode = MethodType(_original_document_section, app)


class TfApp(App):
    """Standard TF app, with a minimal source-faithful single-section link fix."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _install_one_level_adapter(self)
