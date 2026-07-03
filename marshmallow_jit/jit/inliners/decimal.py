# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Decimal field serialization and deserialization inliners."""

from typing import TYPE_CHECKING, cast, override

from marshmallow import Schema
from marshmallow.fields import Decimal as DecimalField
from marshmallow.fields import Field

from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode
from marshmallow_jit.utils import is_overridden

from .base import Inliner

if TYPE_CHECKING:
    pass


class DecimalSerializationInliner(Inliner):
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
        field = cast(DecimalField, field)
        # Decimal's rounding (places/rounding/allow_nan) is intricate and instance-specific,
        # so the actual bound field method is reused instead of reimplementing it inline.
        with code.indent(f"if {value_variable_name} is not None"):
            code += f"{value_variable_name} = {field_obj_variable_name}._format_num({value_variable_name})"
            if field.as_string:
                code += f'{value_variable_name} = format({value_variable_name}, "f")'


class DecimalDeserializationInliner(Inliner):
    """Decimal deserialization that validates and converts to decimal.Decimal.

    Handles the same cases as marshmallow's Decimal._validated:
    - Uses _format_num for conversion (Decimal(str(value)))
    - Handles allow_nan flag for NaN/infinity values
    - Applies places and rounding if specified
    - Catches InvalidOperation for invalid decimal strings
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
        field = cast(DecimalField, field)

        # Check if _validated or _format_num has been overridden
        # If so, fall back to calling the field's _deserialize method
        if is_overridden(field._validated, DecimalField._validated) or is_overridden(
            field._format_num, DecimalField._format_num
        ):
            code += f"{value_variable_name} = {field_obj_variable_name}._deserialize({value_variable_name}, "
            code += f"{attr_name!r}, data)"
            return
            return

        # Add necessary imports
        code.add_import_line("import decimal")

        # Build the conversion logic
        # Decimal uses str(value) before converting to handle float precision issues
        lines = [
            "try:",
            f"    {value_variable_name} = decimal.Decimal(str({value_variable_name}))",
        ]

        # Handle allow_nan check
        if not field.allow_nan:
            lines.extend(
                [
                    "except decimal.InvalidOperation as error:",
                    f'    raise {field_obj_variable_name}.make_error("invalid") from error',
                    f"if {value_variable_name}.is_nan() or {value_variable_name}.is_infinite():",
                    f'    raise {field_obj_variable_name}.make_error("special")',
                ]
            )
        else:
            # When allow_nan is True, we still need to catch InvalidOperation
            # but handle NaN specially (avoid sNaN, -sNaN, -NaN)
            lines.extend(
                [
                    "except decimal.InvalidOperation as error:",
                    f'    raise {field_obj_variable_name}.make_error("invalid") from error',
                    f"if {value_variable_name}.is_nan():",
                    f"    {value_variable_name} = decimal.Decimal('NaN')",
                ]
            )

        # Handle places and rounding (only for finite numbers)
        if field.places is not None:
            # field.places is already a Decimal representing the quantize value
            lines.extend(
                [
                    f"if {value_variable_name}.is_finite():",
                    f"    {value_variable_name} = {value_variable_name}.quantize({field_obj_variable_name}.places, "
                    f"rounding={field.rounding!r})",
                ]
            )

        code += "\n".join(lines) + "\n"
