# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""DictAccessor for reading field values from dictionary-like objects."""

from typing import override

from marshmallow import Schema, missing
from marshmallow.fields import Field

from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode

from .base import ValueAccessor


class DictAccessor(ValueAccessor):
    """Accessor for dictionary-like objects using key-based access.

    Handles dotted paths for nested dict access and falls back to dump_default
    or ``missing`` when keys are not found.
    """

    name = "dict"

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
        if "." in check_key:
            brackets = "".join(f"[{c!r}]" for c in check_key.split("."))
        else:
            brackets = f"[{check_key!r}]"
        with code.indent("try"):
            code += f"{value_variable_name} = obj{brackets}"
        with code.indent("except KeyError"):
            if field.dump_default is not missing:
                if callable(field.dump_default):
                    code += f"{value_variable_name} = {field_variable_name}.dump_default()"
                else:
                    code += f"{value_variable_name} = {field_variable_name}.dump_default"
            else:
                code += f"{value_variable_name} = missing"
