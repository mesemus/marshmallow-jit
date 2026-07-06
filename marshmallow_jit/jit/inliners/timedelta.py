# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""TimeDelta field serialization and deserialization inliners."""

from typing import TYPE_CHECKING, cast, override

from marshmallow import Schema
from marshmallow.fields import TimeDelta as TimeDeltaField

from marshmallow_jit.compat import HAS_TIMEDELTA_SERIALIZATION_TYPE
from marshmallow_jit.compat import MAField as Field
from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode

from .base import Inliner

if TYPE_CHECKING:
    pass


class TimeDeltaSerializationInliner(Inliner):
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
        field = cast(TimeDeltaField, field)

        # Marshmallow 4 uses a different approach - calculate base_unit from precision
        # We need to generate code that creates the base_unit timedelta
        precision = field.precision

        with code.indent(f"if {value_variable_name} is not None"):
            if HAS_TIMEDELTA_SERIALIZATION_TYPE:
                # Marshmallow 3: Use serialization_type
                if field.serialization_type is int:
                    # Integer serialization: delta // unit
                    code += f"""
base_unit = __import__('datetime').timedelta(**{{{precision!r}: 1}})
delta = marshmallow.utils.timedelta_to_microseconds({value_variable_name})
unit = marshmallow.utils.timedelta_to_microseconds(base_unit)
{value_variable_name} = delta // unit
"""
                else:
                    # Float serialization: total_seconds() / base_unit.total_seconds()
                    code += f"""
base_unit = __import__('datetime').timedelta(**{{{precision!r}: 1}})
{value_variable_name} = {value_variable_name}.total_seconds() / base_unit.total_seconds()
"""
            else:
                # Marshmallow 4: Always uses float serialization with microseconds division
                code.add_import_line("import marshmallow.utils")
                # Get the unit mapping from the field at compile time
                unit_var = code.add_variable(
                    f"field__{attr_name}__unit",
                    field._unit_to_microseconds_mapping[precision],  # type: ignore
                )
                code += f"""
microseconds = marshmallow.utils.timedelta_to_microseconds({value_variable_name})
{value_variable_name} = microseconds / {unit_var}
"""


class TimeDeltaDeserializationInliner(Inliner):
    """TimeDelta deserialization that parses time duration values.

    Handles the same cases as marshmallow's TimeDelta._deserialize:
    - Converts input value using serialization_type (int or float)
    - Creates timedelta with the specified precision
    - Catches TypeError, ValueError for invalid inputs
    - Catches OverflowError for values too large
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

        field = cast(TimeDeltaField, field)
        # Add necessary imports
        code.add_import_line("import datetime as dt")

        precision = field.precision

        # In marshmallow 4, if value is already a timedelta instance, it's accepted
        # In marshmallow 3, timedelta instances are rejected and must be numbers
        if _MARSHMALLOW_MAJOR_VERSION >= 4:
            # Marshmallow 4: Skip parsing if already a timedelta
            with code.indent(f"if not isinstance({value_variable_name}, dt.timedelta)"):
                self._generate_parsing_code(code, value_variable_name, field_obj_variable_name, field, precision)
        else:
            # Marshmallow 3: Always parse (timedelta instances will fail in the parser)
            self._generate_parsing_code(code, value_variable_name, field_obj_variable_name, field, precision)

    def _generate_parsing_code(
        self,
        code: PythonCode,
        value_variable_name: str,
        field_obj_variable_name: str,
        field: TimeDeltaField,
        precision: str,
    ) -> None:
        """Generate the timedelta parsing code based on serialization_type."""
        if HAS_TIMEDELTA_SERIALIZATION_TYPE:
            # Marshmallow 3: Use serialization_type
            serialization_type = field.serialization_type.__name__
            if serialization_type == "int":
                code += f"""
try:
    value = int({value_variable_name})
except (TypeError, ValueError) as error:
    raise {field_obj_variable_name}.make_error("invalid") from error

try:
    {value_variable_name} = dt.timedelta(**{{{precision!r}: value}})
except OverflowError as error:
    raise {field_obj_variable_name}.make_error("invalid") from error
"""
            else:
                # Float serialization_type
                code += f"""
try:
    value = float({value_variable_name})
except (TypeError, ValueError) as error:
    raise {field_obj_variable_name}.make_error("invalid") from error

try:
    {value_variable_name} = dt.timedelta(**{{{precision!r}: value}})
except OverflowError as error:
    raise {field_obj_variable_name}.make_error("invalid") from error
"""
        else:
            # Marshmallow 4: Always uses float
            code += f"""
try:
    value = float({value_variable_name})
except (TypeError, ValueError) as error:
    raise {field_obj_variable_name}.make_error("invalid") from error

try:
    {value_variable_name} = dt.timedelta(**{{{precision!r}: value}})
except OverflowError as error:
    raise {field_obj_variable_name}.make_error("invalid") from error
"""
