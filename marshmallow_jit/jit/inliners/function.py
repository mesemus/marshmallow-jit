# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Function field serialization and deserialization inliners."""

from typing import TYPE_CHECKING, cast, override

from marshmallow import Schema
from marshmallow.fields import Field, Function

from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode

from .base import Inliner

if TYPE_CHECKING:
    pass


class FunctionSerializationInliner(Inliner):
    """Function calls a user-provided callable to get the serialized value.

    The serialize_func is already bound to the field instance, so we call it directly.
    The callable may return `missing` to indicate the field should be omitted.
    """

    can_return_missing = True  # User functions may return missing

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
        field = cast("Function", field)
        if field.serialize_func is None:
            # No serialize function defined - return missing
            code += f"{value_variable_name} = marshmallow.missing"
        else:
            # Register the function as a variable and call it with obj
            func_var = code.add_variable(f"field__{attr_name}__func", field.serialize_func)
            code += f"{value_variable_name} = {func_var}(obj)"


class FunctionDeserializationInliner(Inliner):
    """Function deserialization calls a user-provided deserialize function if one is defined.

    Matches marshmallow's Function._deserialize:
    - If deserialize_func is set, calls it with the input value
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
        field = cast("Function", field)
        if field.deserialize_func is None:
            # No deserialize function defined - return value unchanged
            pass
        else:
            # Register the function as a variable and call it with the value
            func_var = code.add_variable(f"field__{attr_name}__func", field.deserialize_func)
            code += f"{value_variable_name} = {func_var}({value_variable_name})"
