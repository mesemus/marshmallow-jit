# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Email field serialization and deserialization inliners."""

from .str import StrDeserializationInliner, StrSerializationInliner


class EmailSerializationInliner(StrSerializationInliner):
    """Email does not override String's ``_serialize``, so it behaves exactly the same."""


class EmailDeserializationInliner(StrDeserializationInliner):
    """Email uses the same deserialization logic as String."""
