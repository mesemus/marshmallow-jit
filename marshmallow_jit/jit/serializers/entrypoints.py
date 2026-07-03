# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Factory for builtin schema serializers and deserializers."""

from typing import TYPE_CHECKING, ClassVar, override

from marshmallow import Schema

from marshmallow_jit.jit.registry import Factory

if TYPE_CHECKING:
    from marshmallow_jit.jit.serializers.base import SchemaDeserializer, SchemaSerializer

from marshmallow_jit.jit.serializers.hybrid import HybridSchemaSerializer
from marshmallow_jit.jit.serializers.instance import InstanceSchemaSerializer
from marshmallow_jit.jit.serializers.mapping import (
    MappingSchemaDeserializer,
    MappingSchemaSerializer,
)


class BuiltinSchemaSerializersFactory(Factory[[Schema], "SchemaSerializer"]):
    """Factory for builtin schema serializers."""

    _serializers_by_name: ClassVar[dict[str, type]] = {
        "mapping": MappingSchemaSerializer,
        "instance": InstanceSchemaSerializer,
        "hybrid": HybridSchemaSerializer,
    }

    @override
    def find(self, schema: Schema) -> SchemaSerializer | None:
        # Serializers are not selected by name in find(), only by registry resolution
        return None

    @override
    def find_by_name(self, name: str, schema: Schema) -> SchemaSerializer | None:
        serializer_class = self._serializers_by_name.get(name)
        if serializer_class is not None:
            return serializer_class(schema)
        return None


class BuiltinSchemaDeserializersFactory(Factory[[Schema], "SchemaDeserializer"]):
    """Factory for builtin schema deserializers."""

    _deserializers_by_name: ClassVar[dict[str, type]] = {
        "mapping": MappingSchemaDeserializer,
    }

    @override
    def find(self, schema: Schema) -> SchemaDeserializer | None:
        # Deserializers are not selected by name in find(), only by registry resolution
        return None

    @override
    def find_by_name(self, name: str, schema: Schema) -> SchemaDeserializer | None:
        deserializer_class = self._deserializers_by_name.get(name)
        if deserializer_class is not None:
            return deserializer_class(schema)
        return None


builtin_schema_serializer_factory = BuiltinSchemaSerializersFactory()
builtin_schema_deserializer_factory = BuiltinSchemaDeserializersFactory()
