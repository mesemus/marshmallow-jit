# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Context tracking for nested schema serialization/deserialization.

Maintains stacks of active schemas, serializers, and deserializers
to properly handle nested schema operations.
"""

import contextlib
from collections.abc import Generator
from typing import TYPE_CHECKING

from marshmallow import Schema

if TYPE_CHECKING:
    from marshmallow_jit.jit.serializers.base import SchemaDeserializer, SchemaSerializer


class Context:
    """Tracks active schemas and serializers during nested serialization/deserialization.

    Maintains stacks of schemas, serializers, and deserializers to support
    proper scoping when processing nested schema structures.
    """

    def __init__(self) -> None:
        self.schema_stack: list[Schema] = []
        self.serializer_stack: list[SchemaSerializer] = []
        self.deserializer_stack: list[SchemaDeserializer] = []
        self.level = 0

    @property
    def current_schema(self) -> Schema:
        """The currently active schema in the context stack."""
        return self.schema_stack[-1]

    @property
    def current_serializer(self) -> SchemaSerializer:
        """The currently active serializer in the context stack."""
        return self.serializer_stack[-1]

    @contextlib.contextmanager
    def within_schema(self, schema: Schema) -> Generator[None]:
        """Context manager to push a schema onto the stack."""
        self.schema_stack.append(schema)
        self.level += 1
        yield
        self.level -= 1
        self.schema_stack.pop()

    @contextlib.contextmanager
    def within_serializer(self, schema_serializer: SchemaSerializer) -> Generator[None]:
        """Context manager to push a serializer onto the stack."""
        self.serializer_stack.append(schema_serializer)
        self.level += 1
        yield
        self.level -= 1
        self.serializer_stack.pop()

    @contextlib.contextmanager
    def within_deserializer(self, schema_deserializer: SchemaDeserializer) -> Generator[None]:
        """Context manager to push a deserializer onto the stack."""
        self.deserializer_stack.append(schema_deserializer)
        self.level += 1
        yield
        self.level -= 1
        self.deserializer_stack.pop()

    @contextlib.contextmanager
    def nest(self) -> Generator[None]:
        """Context manager to increment the nesting level without changing stacks."""
        self.level += 1
        yield
        self.level -= 1
