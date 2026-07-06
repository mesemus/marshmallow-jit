# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Base inliner for IP address field types."""

from typing import TYPE_CHECKING, cast, override

from marshmallow import Schema
from marshmallow.fields import IP

from marshmallow_jit.compat import MAField as Field
from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode

from .base import Inliner

if TYPE_CHECKING:
    pass


class _IPSerializationInliner(Inliner):
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
        field = cast(IP, field)
        attribute = "exploded" if field.exploded else "compressed"
        with code.indent(f"if {value_variable_name} is not None"):
            code += f"{value_variable_name} = {value_variable_name}.{attribute}"
