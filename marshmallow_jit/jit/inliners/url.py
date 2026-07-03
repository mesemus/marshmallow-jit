# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""URL field serialization and deserialization inliners."""

from .str import StrDeserializationInliner, StrSerializationInliner


class UrlSerializationInliner(StrSerializationInliner):
    """Url does not override String's ``_serialize``, so it behaves exactly the same."""


class UrlDeserializationInliner(StrDeserializationInliner):
    """Url uses the same deserialization logic as String."""
