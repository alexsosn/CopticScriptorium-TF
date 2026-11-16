"""Backward-compatible import path for tf-build's atomic no-clobber publisher.

The syscall implementation lives in the shared, published tf-build package.
Existing Coptic call sites and platform-monkeypatching tests keep this private
import path; there is no second rename implementation here.
"""

from __future__ import annotations

# Existing tests simulate Windows/unsupported platforms through these modules.
# Python imports them as singletons, shared with tf_build._atomic.
import os as os
import sys as sys

from tf_build.publication import publish_path_no_clobber as publish_path_no_clobber

__all__ = ["publish_path_no_clobber"]
