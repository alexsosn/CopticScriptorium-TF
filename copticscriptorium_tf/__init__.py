"""Coptic Scriptorium to Text-Fabric local materializer.

The source/model layer is deliberately independent of Text-Fabric. TF graph
construction and serialization live in later implementation tickets.
"""

from .model import DocumentModel
from .parser import parse_source_tree, parse_tt_record

__all__ = ["DocumentModel", "parse_source_tree", "parse_tt_record"]
