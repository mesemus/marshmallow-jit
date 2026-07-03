# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT

"""Serialization inliners, one per field type, one module per class.

Each module is named after the field type it targets (see ``factory.py``'s
``BuiltinSerializationInlinersFactory._inliners_by_type`` for the full, ordered list of
which marshmallow field type maps to which Inliner) - `ls` this directory to see which
field types have been converted to an inliner so far.

Import inliners directly from their modules, e.g.:
    from marshmallow_jit.jit.inliners.str import StrSerializationInliner
"""

from .base import Inliner
from .registry import (
    deserialization_inliner_registry,
    serialization_inliner_registry,
)

__all__ = [
    "deserialization_inliner_registry",
    "Inliner",
    "serialization_inliner_registry",
]
