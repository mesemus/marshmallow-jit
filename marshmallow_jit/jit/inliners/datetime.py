# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""DateTime field serialization and deserialization inliners."""

from typing import TYPE_CHECKING, cast, override

from marshmallow import Schema
from marshmallow.fields import DateTime as DateTimeField

from marshmallow_jit.compat import MAField as Field
from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode

from .base import Inliner

if TYPE_CHECKING:
    pass


class DateTimeSerializationInliner(Inliner):
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
        field = cast(DateTimeField, field)
        data_format = field.format or field.DEFAULT_FORMAT
        format_func = field.SERIALIZATION_FUNCS.get(data_format)
        with code.indent(f"if {value_variable_name} is not None"):
            if format_func is not None:
                # Not inlined as a qualified reference (e.g. `email.utils.format_datetime`):
                # measured to be consistently ~2-3% *slower* than this single stored-variable
                # call, since each extra dotted attribute access (module -> submodule ->
                # function) costs more than one LOAD_GLOBAL on an already-resolved name -
                # see docs/generated_code_report.md recommendation 4.
                format_func_variable = code.add_variable(f"field__{attr_name}__format_func", format_func)
                code += f"{value_variable_name} = {format_func_variable}({value_variable_name})"
            else:
                code += f"{value_variable_name} = {value_variable_name}.strftime({data_format!r})"


class DateTimeDeserializationInliner(Inliner):
    """DateTime deserialization that parses various datetime formats.

    Handles the same cases as marshmallow's DateTime._deserialize:
    - Supports multiple formats: iso, iso8601, rfc, rfc822, timestamp, timestamp_ms
    - Uses appropriate parsing function for each format
    - Falls back to strptime for custom formats
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
        from marshmallow_jit.compat import _MARSHMALLOW_MAJOR_VERSION

        field = cast(DateTimeField, field)
        # Add necessary imports
        code.add_import_line("import datetime as dt")

        data_format = field.format or field.DEFAULT_FORMAT

        # In marshmallow 4, if value is already a datetime instance, it's accepted
        # In marshmallow 3, datetime instances are rejected and must be strings
        if _MARSHMALLOW_MAJOR_VERSION >= 4:
            # Marshmallow 4: Skip parsing if already a datetime
            with code.indent(f"if not isinstance({value_variable_name}, dt.datetime)"):
                self._generate_parsing_code(code, value_variable_name, field_obj_variable_name, data_format)
        else:
            # Marshmallow 3: Always parse (datetime instances will fail in the parser)
            self._generate_parsing_code(code, value_variable_name, field_obj_variable_name, data_format)

    def _generate_parsing_code(
        self, code: PythonCode, value_variable_name: str, field_obj_variable_name: str, data_format: str
    ) -> None:
        """Generate the datetime parsing code based on field format."""
        # Determine which parser to use based on format
        if data_format in ("iso", "iso8601"):
            code.add_import_line("from marshmallow_jit.compat import from_iso_datetime")
            code += f"""
try:
    {value_variable_name} = from_iso_datetime({value_variable_name})
except (TypeError, AttributeError, ValueError) as error:
    raise {field_obj_variable_name}.make_error(
        "invalid", input={value_variable_name}, obj_type={field_obj_variable_name}.OBJ_TYPE
    ) from error
"""
        elif data_format in ("rfc", "rfc822"):
            code.add_import_line("from marshmallow_jit.compat import from_rfc")
            code += f"""
try:
    {value_variable_name} = from_rfc({value_variable_name})
except (TypeError, AttributeError, ValueError) as error:
    raise {field_obj_variable_name}.make_error(
        "invalid", input={value_variable_name}, obj_type={field_obj_variable_name}.OBJ_TYPE
    ) from error
"""
        elif data_format == "timestamp":
            code.add_import_line("from marshmallow.utils import from_timestamp")
            code += f"""
try:
    {value_variable_name} = from_timestamp({value_variable_name})
except (TypeError, AttributeError, ValueError) as error:
    raise {field_obj_variable_name}.make_error(
        "invalid", input={value_variable_name}, obj_type={field_obj_variable_name}.OBJ_TYPE
    ) from error
"""
        elif data_format == "timestamp_ms":
            code.add_import_line("from marshmallow.utils import from_timestamp_ms")
            code += f"""
try:
    {value_variable_name} = from_timestamp_ms({value_variable_name})
except (TypeError, AttributeError, ValueError) as error:
    raise {field_obj_variable_name}.make_error(
        "invalid", input={value_variable_name}, obj_type={field_obj_variable_name}.OBJ_TYPE
    ) from error
"""
        else:
            # Custom format - use strptime
            code += f"""
try:
    {value_variable_name} = dt.datetime.strptime({value_variable_name}, {data_format!r})
except (TypeError, AttributeError, ValueError) as error:
    raise {field_obj_variable_name}.make_error(
        "invalid", input={value_variable_name}, obj_type={field_obj_variable_name}.OBJ_TYPE
    ) from error
"""
