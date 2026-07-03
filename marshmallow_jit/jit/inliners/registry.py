# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT

"""Registry for serialization and deserialization inliners."""

from marshmallow import Schema
from marshmallow.fields import Field

from marshmallow_jit.jit.registry import Registry

from .base import Inliner


class SerializationInlinerRegistry(Registry[Inliner, [Schema, str, Field]]):
    """Registry for serialization inliners."""

    def __init__(self) -> None:
        super().__init__("marshmallow_jit.serialization_inliners")


class DeserializationInlinerRegistry(Registry[Inliner, [Schema, str, Field]]):
    """Registry for deserialization inliners."""

    def __init__(self) -> None:
        super().__init__("marshmallow_jit.deserialization_inliners")


serialization_inliner_registry = SerializationInlinerRegistry()
"""Registry for serialization inliners."""

deserialization_inliner_registry = DeserializationInlinerRegistry()
"""Registry for deserialization inliners."""

__all__ = [
    "DeserializationInlinerRegistry",
    "SerializationInlinerRegistry",
    "deserialization_inliner_registry",
    "serialization_inliner_registry",
]
