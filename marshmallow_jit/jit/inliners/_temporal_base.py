# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Base inliner for temporal (date/time) field types."""

from typing import TYPE_CHECKING, cast, override

from marshmallow import Schema
from marshmallow.fields import DateTime

from marshmallow_jit.compat import MAField as Field
from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode

from .base import Inliner

if TYPE_CHECKING:
    pass


class _TemporalSerializationInliner(Inliner):
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
        field = cast(DateTime, field)
        data_format = field.format or field.DEFAULT_FORMAT
        format_func = field.SERIALIZATION_FUNCS.get(data_format)
        with code.indent(f"if {value_variable_name} is not None"):
            if format_func is not None:
                # Not inlined as a qualified reference (e.g. `email.utils.format_datetime`):
                # measured to be consistently ~2-3% *slower* than this single stored-variable
                # call, since each extra dotted attribute access (module -> submodule ->
                # function) costs more than one LOAD_GLOBAL on an already-resolved variable -
                # see docs/generated_code_report.md recommendation 4.
                format_func_variable = code.add_variable(f"field__{attr_name}__format_func", format_func)
                code += f"{value_variable_name} = {format_func_variable}({value_variable_name})"
            else:
                code += f"{value_variable_name} = {value_variable_name}.strftime({data_format!r})"
