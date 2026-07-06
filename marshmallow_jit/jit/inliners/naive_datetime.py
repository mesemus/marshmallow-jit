# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""NaiveDateTime field serialization and deserialization inliners."""

from typing import TYPE_CHECKING, cast, override

from marshmallow import Schema
from marshmallow.fields import Field
from marshmallow.fields import NaiveDateTime as NaiveDateTimeField

from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode

from .base import Inliner

if TYPE_CHECKING:
    pass


class NaiveDateTimeSerializationInliner(Inliner):
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
        # Same as DateTime serialization
        from ._temporal_base import _TemporalSerializationInliner

        inline = _TemporalSerializationInliner()
        inline.generate_code(code, value_variable_name, field_obj_variable_name, schema, attr_name, field, context)


class NaiveDateTimeDeserializationInliner(Inliner):
    """NaiveDateTime deserialization that parses datetime strings and ensures naive output.

    Handles the same cases as marshmallow's NaiveDateTime._deserialize:
    - First deserializes using DateTime logic
    - If result is timezone-aware, converts to UTC and removes tzinfo
    - Raises 'invalid_awareness' error if aware datetime provided when not expected
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
        field = cast(NaiveDateTimeField, field)
        # Add necessary imports
        code.add_import_line("import datetime as dt")
        code.add_import_line("from marshmallow_jit.compat import from_iso_datetime")
        code.add_import_line("from marshmallow.utils import is_aware")

        # Check if value is already a datetime instance (early return optimization)
        with code.indent(f"if not isinstance({value_variable_name}, dt.datetime)"):
            # First deserialize as regular datetime
            code += f"""
try:
    {value_variable_name} = from_iso_datetime({value_variable_name})
except (TypeError, AttributeError, ValueError) as error:
    raise {field_obj_variable_name}.make_error(
        "invalid", input={value_variable_name}, obj_type={field_obj_variable_name}.OBJ_TYPE
    ) from error
"""

        # Then check if aware and handle accordingly
        timezone_var = code.add_variable(f"field__{attr_name}__timezone", field.timezone)
        code += f"""
        if is_aware({value_variable_name}):
            if {timezone_var} is None:
                raise {field_obj_variable_name}.make_error(
                    "invalid_awareness",
                    awareness={field_obj_variable_name}.AWARENESS,
                    obj_type={field_obj_variable_name}.OBJ_TYPE
                )
            {value_variable_name} = {value_variable_name}.astimezone({timezone_var}).replace(tzinfo=None)
        """
