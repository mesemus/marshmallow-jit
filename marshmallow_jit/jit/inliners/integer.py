# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Integer field serialization and deserialization inliners."""

from typing import TYPE_CHECKING, cast, override

from marshmallow import Schema
from marshmallow.fields import Field, Integer

from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode
from marshmallow_jit.utils import is_overridden

from .base import Inliner

if TYPE_CHECKING:
    pass


class IntegerSerializationInliner(Inliner):
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
        field = cast(Integer, field)

        # Check if _format_num has been overridden - if so, we must call the field's method
        # instead of inlining, since custom _format_num logic would be lost
        if is_overridden(field._format_num, Integer._format_num):
            # Fall back to calling the field's serialize method
            code += f"{value_variable_name} = {field_obj_variable_name}.serialize({attr_name!r}, "
            code += "obj, accessor=self.get_attribute)"
            return

        with code.indent(f"if {value_variable_name} is not None"):
            code += f"{value_variable_name} = int({value_variable_name})"
            if field.as_string:
                code += f"{value_variable_name} = str({value_variable_name})"


class IntegerDeserializationInliner(Inliner):
    """Integer deserialization that validates and converts to int.

    Handles the same cases as marshmallow's Integer._validated:
    - Rejects booleans (True/False) explicitly
    - In strict mode, only accepts values that are already integers (numbers.Integral)
    - Uses _format_num (int()) for conversion in non-strict mode
    - Catches TypeError, ValueError, and OverflowError
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
        field = cast(Integer, field)

        # Check if _validated or _format_num has been overridden
        # If so, fall back to calling the field's _deserialize method
        if is_overridden(field._validated, Integer._validated) or is_overridden(field._format_num, Integer._format_num):
            code += f"{value_variable_name} = {field_obj_variable_name}._deserialize({value_variable_name}, "
            code += f"{attr_name!r}, data)"
            return

        # Add import for numbers module (needed for strict mode check)
        code.add_import_line("import numbers")

        if field.strict:
            # Strict mode: only accept values that are already integers
            code += f"""
            # (value is True or value is False) is ~5x faster than isinstance(value, bool)
            if {value_variable_name} is True or {value_variable_name} is False:
                raise {field_obj_variable_name}.make_error("invalid", input={value_variable_name})
            if not isinstance({value_variable_name}, numbers.Integral):
                raise {field_obj_variable_name}.make_error("invalid", input={value_variable_name})
            """
        else:
            # Non-strict mode: allow conversion from strings, floats, etc.
            code += f"""
            # (value is True or value is False) is ~5x faster than isinstance(value, bool)
            if {value_variable_name} is True or {value_variable_name} is False:
                raise {field_obj_variable_name}.make_error("invalid", input={value_variable_name})
            try:
                {value_variable_name} = int({value_variable_name})
            except (TypeError, ValueError) as error:
                raise {field_obj_variable_name}.make_error("invalid", input={value_variable_name}) from error
            except OverflowError as error:
                raise {field_obj_variable_name}.make_error("too_large", input={value_variable_name}) from error
            """
