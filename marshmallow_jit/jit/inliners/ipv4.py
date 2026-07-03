# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""IPv4 address field serialization and deserialization inliners."""

from typing import TYPE_CHECKING

from ._ip_base import _IPSerializationInliner
from .ip import IPDeserializationInliner

if TYPE_CHECKING:
    pass


class IPv4SerializationInliner(_IPSerializationInliner):
    """IPv4 does not override IP's ``_serialize``, so it behaves exactly the same."""

    pass


class IPv4DeserializationInliner(IPDeserializationInliner):
    """IPv4 does not override IP's ``_deserialize``, so it behaves exactly the same."""

    pass
