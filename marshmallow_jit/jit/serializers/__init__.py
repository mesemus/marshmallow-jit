# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Schema serializers and deserializers for JIT compilation.

This module provides a decoupled serializer system with:
- Base interfaces in ``base.py``
- Implementations in ``mapping.py``, ``instance.py``, ``hybrid.py``
- Registry in ``registry.py``
- Builtin factories in ``entrypoints.py``

Public API:
    from marshmallow_jit.jit.serializers import (
        SchemaSerializerProtocol,
        SchemaDeserializerProtocol,
        serializer_registry,
        deserializer_registry,
    )

For concrete implementations, import directly from their modules:
    from marshmallow_jit.jit.serializers.mapping import MappingSchemaSerializer, MappingSchemaDeserializer
    from marshmallow_jit.jit.serializers.instance import InstanceSchemaSerializer
    from marshmallow_jit.jit.serializers.hybrid import HybridSchemaSerializer
"""

from marshmallow_jit.jit.serializers.base import (
    SchemaDeserializer,
    SchemaSerializer,
)
from marshmallow_jit.jit.serializers.registry import deserializer_registry, serializer_registry

__all__ = [
    "SchemaDeserializer",
    "SchemaSerializer",
    "deserializer_registry",
    "serializer_registry",
]
