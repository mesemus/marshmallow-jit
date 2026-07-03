# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Registry for serialization value accessors."""

from marshmallow import Schema
from marshmallow.fields import Field

from marshmallow_jit.jit.registry import Registry

from .base import ValueAccessor


class SerializationAccessorRegistry(Registry[ValueAccessor, [Schema, str, Field]]):
    """Registry for serialization value accessors."""

    def __init__(self) -> None:
        super().__init__("marshmallow_jit.accessors")


serialization_accessor_registry = SerializationAccessorRegistry()
"""Registry for serialization value accessors."""

__all__ = [
    "SerializationAccessorRegistry",
    "serialization_accessor_registry",
]
