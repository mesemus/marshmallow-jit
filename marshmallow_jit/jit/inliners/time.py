# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Time field serialization and deserialization inliners."""

from typing import TYPE_CHECKING, cast, override

from marshmallow import Schema
from marshmallow.fields import Time as TimeField

from marshmallow_jit.compat import MAField as Field
from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode

from .base import Inliner

if TYPE_CHECKING:
    pass


class TimeSerializationInliner(Inliner):
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
        from ._temporal_base import _TemporalSerializationInliner

        inline = _TemporalSerializationInliner()
        inline.generate_code(code, value_variable_name, field_obj_variable_name, schema, attr_name, field, context)


class TimeDeserializationInliner(Inliner):
    """Time deserialization that parses time strings.

    Handles the same cases as marshmallow's Time._deserialize:
    - Supports formats: iso, iso8601 (both use ISO 8601 time format)
    - Falls back to strptime for custom formats
    - Returns time objects (not datetime)
    - Catches TypeError, AttributeError, ValueError and raises 'invalid' error
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
        field = cast(TimeField, field)
        # Add necessary imports
        code.add_import_line("import datetime as dt")

        # Check if value is already a time instance (early return optimization)
        with code.indent(f"if not isinstance({value_variable_name}, dt.time)"):
            data_format = field.format or field.DEFAULT_FORMAT
            func = field.DESERIALIZATION_FUNCS.get(data_format)

            if func is not None:
                # Use built-in deserialization function (iso/iso8601 both use from_iso_time)
                code.add_import_line("from marshmallow_jit.compat import from_iso_time")
                code += f"""
try:
    {value_variable_name} = from_iso_time({value_variable_name})
except (TypeError, AttributeError, ValueError) as error:
    raise {field_obj_variable_name}.make_error(
        "invalid", input={value_variable_name}, obj_type={field_obj_variable_name}.OBJ_TYPE
    ) from error
"""
            else:
                # Custom format - use strptime and extract time
                code += f"""
try:
    {value_variable_name} = dt.datetime.strptime({value_variable_name}, {data_format!r}).time()
except (TypeError, AttributeError, ValueError) as error:
    raise {field_obj_variable_name}.make_error(
        "invalid", input={value_variable_name}, obj_type={field_obj_variable_name}.OBJ_TYPE
    ) from error
"""
