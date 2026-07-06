# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Enum field serialization and deserialization inliners."""

from typing import TYPE_CHECKING, cast, override

from marshmallow import Schema

from marshmallow_jit.compat import MAEnum
from marshmallow_jit.compat import MAField as Field
from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode

from .base import Inliner

if TYPE_CHECKING:
    pass


class EnumSerializationInliner(Inliner):
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
        field = cast(MAEnum, field)
        with code.indent(f"if {value_variable_name} is not None"):
            if not field.by_value:
                # Enum.__init__ always sets self.field = String() in this branch, and
                # _serialize always uses the member's `.name` here - see Enum._serialize.
                code += f"{value_variable_name} = marshmallow.utils.ensure_text_type({value_variable_name}.name)"
            elif field.by_value is True:
                # Enum.__init__ always sets self.field = Raw() in this branch (identity
                # passthrough), and _serialize always uses the member's `.value` here.
                code += f"{value_variable_name} = {value_variable_name}.value"
            else:
                # by_value is a custom field type/instance - delegate to its own
                # _serialize, since we can't safely assume its behavior generically.
                inner_field_variable = code.add_variable(f"field__{attr_name}__inner", field.field)
                code += (
                    f"{value_variable_name} = {inner_field_variable}._serialize("
                    f"{value_variable_name}.value, {attr_name!r}, obj)"
                )


class EnumDeserializationInliner(Inliner):
    """Enum deserialization converts values to enum members.

    Handles the same cases as marshmallow's Enum._deserialize:
    - by_value=False: looks up enum member by name (string)
    - by_value=True: looks up enum member by value
    - by_value=<custom field>: deserializes using the custom field, then creates enum from result
    - Raises 'unknown' error for invalid names/values
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
        field = cast(MAEnum, field)

        enum_var = code.add_variable(f"field__{attr_name}__enum", field.enum)

        # First check if the value is already an enum instance (early return optimization)
        # This matches marshmallow 4's behavior
        with code.indent(f"if not isinstance({value_variable_name}, {enum_var})"):
            if not field.by_value:
                # by_value=False: look up by name
                # First deserialize using the inner String field, then look up the enum member
                inner_field_variable = code.add_variable(f"field__{attr_name}__inner", field.field)
                code += f"""
# First validate and deserialize using the inner field (String)
{value_variable_name} = {inner_field_variable}._deserialize({value_variable_name}, {attr_name!r}, data)
try:
    {value_variable_name} = getattr({enum_var}, {value_variable_name})
except AttributeError as error:
    raise {field_obj_variable_name}.make_error(
        "unknown", choices={field_obj_variable_name}.choices_text
    ) from error
"""
            elif field.by_value is True:
                # by_value=True: look up by value (uses Raw field internally)
                code += f"""
try:
    {value_variable_name} = {enum_var}({value_variable_name})
except ValueError as error:
    raise {field_obj_variable_name}.make_error(
        "unknown", choices={field_obj_variable_name}.choices_text
    ) from error
"""
            else:
                # by_value=<custom field>: deserialize using custom field, then create enum
                inner_field_variable = code.add_variable(f"field__{attr_name}__inner", field.field)
                code += f"""
# First deserialize using the inner field
temp_value = {inner_field_variable}._deserialize({value_variable_name}, {attr_name!r}, data)
try:
    {value_variable_name} = {enum_var}(temp_value)
except ValueError as error:
    raise {field_obj_variable_name}.make_error(
        "unknown", choices={field_obj_variable_name}.choices_text
    ) from error
"""
