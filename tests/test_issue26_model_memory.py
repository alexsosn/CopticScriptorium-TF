"""Memory representation contract for issue #26's first optimization slice."""
from __future__ import annotations

import unittest

from copticscriptorium_tf.model import (
    ConlluSupplement,
    DocumentModel,
    Entity,
    LayoutEvent,
    NormGroup,
    Orig,
    OrigGroup,
    Sentence,
    SupplementalWord,
    Translation,
    Word,
)


SOURCE_MODEL_RECORD_TYPES = (
    Word,
    Sentence,
    Orig,
    NormGroup,
    OrigGroup,
    LayoutEvent,
    Entity,
    Translation,
    SupplementalWord,
    ConlluSupplement,
    DocumentModel,
)


class SourceModelMemoryContractTests(unittest.TestCase):
    def test_immutable_source_model_records_do_not_allocate_instance_dicts(self) -> None:
        for record_type in SOURCE_MODEL_RECORD_TYPES:
            with self.subTest(record_type=record_type.__name__):
                self.assertIn(
                    "__slots__",
                    record_type.__dict__,
                    f"{record_type.__name__} still uses per-instance __dict__ storage",
                )
                self.assertNotIn("__dict__", record_type.__slots__)


if __name__ == "__main__":
    unittest.main()
