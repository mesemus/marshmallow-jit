# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Registry for schema serializers and deserializers."""

from marshmallow import Schema

from marshmallow_jit.jit.registry import Registry
from marshmallow_jit.jit.serializers.base import SchemaDeserializer, SchemaSerializer


class SchemaSerializerRegistry(Registry[SchemaSerializer, [Schema]]):
    """Registry for schema serializers."""

    def __init__(self) -> None:
        super().__init__("marshmallow_jit.schema_serializers")


class SchemaDeserializerRegistry(Registry[SchemaDeserializer, [Schema]]):
    """Registry for schema deserializers."""

    def __init__(self) -> None:
        super().__init__("marshmallow_jit.schema_deserializers")


serializer_registry = SchemaSerializerRegistry()
"""Registry for schema serializers."""

deserializer_registry = SchemaDeserializerRegistry()
"""Registry for schema deserializers."""

__all__ = [
    "SchemaDeserializerRegistry",
    "SchemaSerializerRegistry",
    "deserializer_registry",
    "serializer_registry",
]
