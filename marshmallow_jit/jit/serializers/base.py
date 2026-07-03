# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Base interfaces for schema serializers and deserializers.

Defines the protocol interfaces without implementation details.
Concrete implementations are in mapping.py, instance.py, hybrid.py.
"""

from typing import TYPE_CHECKING

from marshmallow.fields import Field

from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode

if TYPE_CHECKING:
    from marshmallow_jit.schema import JITSchemaBase


class SchemaSerializer:
    """Base class for schema serialization code generators."""

    name: str

    def __init__(self, schema: JITSchemaBase) -> None:
        pass

    @property
    def schema_name(self) -> str:
        raise NotImplementedError

    def generate_serialize_method_content(self, code: PythonCode, context: Context) -> None:
        raise NotImplementedError

    def generate_serializer_field(
        self, code: PythonCode, attr_name: str, field_obj: Field, key: str, context: Context, ret_var: str
    ) -> None:
        raise NotImplementedError


class SchemaDeserializer:
    """Base class for schema deserialization code generators."""

    name: str

    def __init__(self, schema: JITSchemaBase) -> None:
        pass

    @property
    def schema_name(self) -> str:
        raise NotImplementedError

    def generate_deserialize_method_content(self, code: PythonCode, context: Context) -> None:
        raise NotImplementedError
