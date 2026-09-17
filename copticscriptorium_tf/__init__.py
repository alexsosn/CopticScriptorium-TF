"""Coptic Scriptorium TT to native Text-Fabric converter."""

from .model import DocumentModel
from .parser import parse_source_tree, parse_tt_record

__all__ = [
    "ConversionResult",
    "DocumentModel",
    "convert_source_tree",
    "parse_source_tree",
    "parse_tt_record",
]


def __getattr__(name: str):
    """Expose converter conveniences without pre-importing the ``-m`` target."""
    if name in {"ConversionResult", "convert_source_tree"}:
        from .converter import ConversionResult, convert_source_tree

        exports = {
            "ConversionResult": ConversionResult,
            "convert_source_tree": convert_source_tree,
        }
        globals().update(exports)
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
