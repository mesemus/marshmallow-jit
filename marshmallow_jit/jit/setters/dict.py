# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""DictSetter for setting deserialized values into dictionary results."""

from typing import override

from marshmallow import Schema
from marshmallow.fields import Field

from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode

from .base import ValueSetter


class DictSetter(ValueSetter):
    """Setter for dictionary results using direct key assignment.

    Handles dotted paths (e.g., 'foo.bar.baz') via marshmallow's ``set_value`` helper.
    Uses direct assignment for simple keys without dots for optimal performance.
    """

    name = "dict"

    @override
    def generate_code(
        self,
        code: PythonCode,
        result_name: str,
        value_variable_name: str,
        field_key: str,
        field_obj_variable_name: str,
        schema: Schema,
        attr_name: str,
        field: Field,
        context: Context,
    ) -> None:
        # Check if the key contains dots (nested path)
        if "." in field_key:
            # For dotted keys, generate recursive set_value logic
            # This is the less common case, so we use a helper approach
            code.add_import_line("from marshmallow.utils import set_value as _utils_set_value")
            code += f"_utils_set_value({result_name}, {field_key!r}, {value_variable_name})"
        else:
            # Common case: simple key without dots - direct assignment is fastest
            code += f"{result_name}[{field_key!r}] = {value_variable_name}"
