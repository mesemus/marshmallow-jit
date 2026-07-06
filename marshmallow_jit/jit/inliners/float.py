# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Float field serialization and deserialization inliners."""

from typing import TYPE_CHECKING, cast, override

from marshmallow import Schema
from marshmallow.fields import Float

from marshmallow_jit.compat import MAField as Field
from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode
from marshmallow_jit.utils import is_overridden

from .base import Inliner

if TYPE_CHECKING:
    pass


class FloatSerializationInliner(Inliner):
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
        field = cast(Float, field)

        # Check if _format_num has been overridden - if so, we must call the field's method
        # instead of inlining, since custom _format_num logic would be lost
        if is_overridden(field._format_num, Float._format_num):
            # Fall back to calling the field's serialize method
            code += f"{value_variable_name} = {field_obj_variable_name}.serialize({attr_name!r}, "
            code += "obj, accessor=self.get_attribute)"
            return

        with code.indent(f"if {value_variable_name} is not None"):
            code += f"{value_variable_name} = float({value_variable_name})"
            if field.as_string:
                code += f"{value_variable_name} = str({value_variable_name})"


class FloatDeserializationInliner(Inliner):
    """Float deserialization that validates and converts to float.

    Handles the same cases as marshmallow's Number._validated:
    - Rejects booleans (True/False) explicitly
    - Uses _format_num (float()) for conversion
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
        field = cast(Float, field)

        # Check if _validated or _format_num has been overridden
        # If so, fall back to calling the field's _deserialize method
        if is_overridden(field._validated, Float._validated) or is_overridden(field._format_num, Float._format_num):
            code += f"{value_variable_name} = {field_obj_variable_name}._deserialize({value_variable_name}, "
            code += f"{attr_name!r}, data)"
            return

        code += f"""
        # (value is True or value is False) is ~5x faster than isinstance(value, bool)
        if {value_variable_name} is True or {value_variable_name} is False:
            raise {field_obj_variable_name}.make_error("invalid", input={value_variable_name})
        try:
            {value_variable_name} = float({value_variable_name})
        except (TypeError, ValueError) as error:
            raise {field_obj_variable_name}.make_error("invalid", input={value_variable_name}) from error
        except OverflowError as error:
            raise {field_obj_variable_name}.make_error("too_large", input={value_variable_name}) from error
        """
