# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""HybridAccessor for reading field values from both dicts and objects."""

from typing import override

from marshmallow import Schema, missing
from marshmallow.fields import Field

from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode

from .base import ValueAccessor


class HybridAccessor(ValueAccessor):
    """Accessor that tries dict access first, then falls back to attribute access.

    Useful for schemas that need to handle both dict-like and object-like inputs.
    Handles dotted paths by trying each segment as a dict key first, then as an attribute.
    """

    name = "hybrid"

    @override
    def generate_optimized_accessor(
        self,
        code: PythonCode,
        value_variable_name: str,
        schema: Schema,
        attr_name: str,
        check_key: str,
        field_variable_name: str,
        field: Field,
        context: Context,
    ) -> None:
        with code.indent("try"):
            check_key_parts = check_key.split(".")
            accessor = "obj"
            for part in check_key_parts:
                if code.is_valid_variable(part):
                    attribute_access = f"{accessor}.{part}"
                else:
                    attribute_access = f"getattr({accessor}, {part!r})"
                code += f"""
                try:
                    {value_variable_name} = {accessor}[{part!r}]
                except (KeyError, IndexError, TypeError, AttributeError):
                    {value_variable_name} = {attribute_access}
                """
                accessor = value_variable_name
        with code.indent("except AttributeError"):
            if field.dump_default is not missing:
                if callable(field.dump_default):
                    code += f"""
                        {value_variable_name} = {field_variable_name}.dump_default()
                    """
                else:
                    code += f"""
                        {value_variable_name} = {field_variable_name}.dump_default
                    """
            else:
                code += f"""
                    {value_variable_name} = missing
                """
