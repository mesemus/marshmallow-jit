# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Method field serialization and deserialization inliners."""

from typing import TYPE_CHECKING, cast, override

from marshmallow import Schema
from marshmallow.fields import Field, Method

from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode

from .base import Inliner

if TYPE_CHECKING:
    pass


class MethodSerializationInliner(Inliner):
    """Method calls a schema method to get the serialized value.

    The method name is stored in the field and we generate a call to that method.
    """

    can_return_missing = True  # Returns missing when no serialize_method is defined

    @override
    def generate_code(
        self,
        code: PythonCode,
        value_variable_name: str,
        field_obj_variable_name: str,
        schema: Schema,
        attr_name: str,
        field: Field,
        context: Context,
    ) -> None:
        field = cast("Method", field)
        method_name = field.serialize_method_name
        if method_name is None:
            # No serialize method defined - return missing so the field is skipped
            code += f"{value_variable_name} = marshmallow.missing"
        else:
            # Call the schema method with obj as argument
            code += f"{value_variable_name} = self.{method_name}(obj)"


class MethodDeserializationInliner(Inliner):
    """Method deserialization calls a schema method if one is defined.

    Matches marshmallow's Method._deserialize:
    - If _deserialize_method is set, calls it with the input value
    - Otherwise, returns the value unchanged
    """

    @override
    def generate_code(
        self,
        code: PythonCode,
        value_variable_name: str,
        field_obj_variable_name: str,
        schema: Schema,
        attr_name: str,
        field: Field,
        context: Context,
    ) -> None:
        field = cast("Method", field)
        method_name = field.deserialize_method_name
        if method_name is None:
            # No deserialize method defined - return value unchanged
            pass
        else:
            # Call the schema method with the value as argument
            code += f"{value_variable_name} = self.{method_name}({value_variable_name})"
