# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""IPv6 interface field serialization and deserialization inliners."""

from typing import TYPE_CHECKING

from ._ip_base import _IPSerializationInliner
from .ip_interface import IPInterfaceDeserializationInliner

if TYPE_CHECKING:
    pass


class IPv6InterfaceSerializationInliner(_IPSerializationInliner):
    """IPv6Interface does not override IPInterface's ``_serialize``, so it behaves exactly the same."""

    pass


class IPv6InterfaceDeserializationInliner(IPInterfaceDeserializationInliner):
    """IPv6Interface does not override IPInterface's ``_deserialize``, so it behaves exactly the same."""

    pass
