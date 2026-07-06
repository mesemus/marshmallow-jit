# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""InstanceAccessor for reading field values from object instances."""

from typing import override

from marshmallow import Schema, missing

from marshmallow_jit.compat import MAField as Field
from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode

from .base import ValueAccessor


class InstanceAccessor(ValueAccessor):
    """Accessor for object instances using attribute-based access.

    Uses ``getattr()`` for single-segment lookups with built-in defaults,
    and direct attribute chaining (e.g., ``obj.a.b.c``) for valid identifiers.
    Falls back to try/except for dotted paths or invalid identifiers.
    """

    name = "instance"

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
        check_key_parts = check_key.split(".")

        if len(check_key_parts) == 1:
            # A single-segment lookup uses getattr()'s built-in default instead of
            # try/except AttributeError. Benchmarked (see docs/generated_code_report.md,
            # recommendation 2): try/except is faster while the attribute is present, but
            # getattr() is faster as soon as it's missing >=~3% of the time, since raising
            # and unwinding AttributeError is far more expensive than getattr()'s constant
            # per-call cost - and dotted chains below still need try/except, since
            # getattr() can't cleanly express "stop at the first missing segment".
            if field.dump_default is not missing and not callable(field.dump_default):
                code += f"{value_variable_name} = getattr(obj, {check_key!r}, {field_variable_name}.dump_default)"
            else:
                code += f"{value_variable_name} = getattr(obj, {check_key!r}, missing)"
                if callable(field.dump_default):
                    with code.indent(f"if {value_variable_name} is missing"):
                        code += f"{value_variable_name} = {field_variable_name}.dump_default()"
            return

        with code.indent("try"):
            if all(code.is_valid_variable(part) for part in check_key_parts):
                # every segment is a valid identifier, so the whole (possibly dotted)
                # attribute chain can be spliced directly, e.g. obj.a.b.c
                code += f"{value_variable_name} = obj.{check_key}"
            else:
                # at least one segment isn't a valid identifier (e.g. a dash or a
                # leading digit) and can't be spliced as `.part`; fall back to a
                # getattr() call for just that segment, same as HybridAccessor does
                accessor = "obj"
                for part in check_key_parts:
                    if code.is_valid_variable(part):
                        code += f"{value_variable_name} = {accessor}.{part}"
                    else:
                        code += f"{value_variable_name} = getattr({accessor}, {part!r})"
                    accessor = value_variable_name
        with code.indent("except AttributeError"):
            if field.dump_default is not missing:
                if callable(field.dump_default):
                    code += f"{value_variable_name} = {field_variable_name}.dump_default()"
                else:
                    code += f"{value_variable_name} = {field_variable_name}.dump_default"
            else:
                code += f"{value_variable_name} = missing"
