# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""String field serialization and deserialization inliners."""

from typing import TYPE_CHECKING, override

from marshmallow import Schema

from marshmallow_jit.compat import MAField as Field
from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode

from .base import Inliner

if TYPE_CHECKING:
    pass


class StrSerializationInliner(Inliner):
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
        with code.indent(f"if {value_variable_name} is not None"):
            # Fast path: only call ensure_text_type if needed (already a str is skipped)
            code += f"""
            if type({value_variable_name}) is not str:
                {value_variable_name} = marshmallow.utils.ensure_text_type({value_variable_name})
            """


class StrDeserializationInliner(Inliner):
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
        code += f"""
        # Only call ensure_text_type if needed (already a str is fast path)
        if type({value_variable_name}) is not str:
            if not isinstance({value_variable_name}, (str, bytes)):
                raise {field_obj_variable_name}.make_error("invalid")
            try:
                {value_variable_name} = marshmallow.utils.ensure_text_type({value_variable_name})
            except UnicodeDecodeError as error:
                raise {field_obj_variable_name}.make_error("invalid_utf8") from error
        """
