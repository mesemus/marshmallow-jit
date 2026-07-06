# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""AwareDateTime field serialization and deserialization inliners."""

from typing import TYPE_CHECKING, cast, override

from marshmallow import Schema
from marshmallow.fields import AwareDateTime as AwareDateTimeField

from marshmallow_jit.compat import MAField as Field
from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode

from .base import Inliner

if TYPE_CHECKING:
    pass


class AwareDateTimeSerializationInliner(Inliner):
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


class AwareDateTimeDeserializationInliner(Inliner):
    """AwareDateTime deserialization that parses datetime strings and ensures aware output.

    Handles the same cases as marshmallow's AwareDateTime._deserialize:
    - First deserializes using DateTime logic
    - If result is naive, applies default_timezone
    - Raises 'invalid_awareness' error if naive datetime provided when not expected
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

        field = cast(AwareDateTimeField, field)
        # Add necessary imports
        code.add_import_line("import datetime as dt")
        code.add_import_line("from marshmallow_jit.compat import from_iso_datetime")
        code.add_import_line("from marshmallow.utils import is_aware")

        # In marshmallow 4, if value is already a datetime instance, it's accepted
        # In marshmallow 3, datetime instances are rejected and must be strings
        if _MARSHMALLOW_MAJOR_VERSION >= 4:
            # Marshmallow 4: Skip parsing if already a datetime
            with code.indent(f"if not isinstance({value_variable_name}, dt.datetime)"):
                self._generate_parsing_code(code, value_variable_name, field_obj_variable_name)
        else:
            # Marshmallow 3: Always parse (datetime instances will fail in the parser)
            self._generate_parsing_code(code, value_variable_name, field_obj_variable_name)

        # Then check if naive and handle accordingly
        default_tz_var = code.add_variable(f"field__{attr_name}__default_tz", field.default_timezone)
        code += f"""
if not is_aware({value_variable_name}):
    if {default_tz_var} is None:
        raise {field_obj_variable_name}.make_error(
            "invalid_awareness",
            awareness={field_obj_variable_name}.AWARENESS,
            obj_type={field_obj_variable_name}.OBJ_TYPE
        )
    {value_variable_name} = {value_variable_name}.replace(tzinfo={default_tz_var})
"""

    def _generate_parsing_code(self, code: PythonCode, value_variable_name: str, field_obj_variable_name: str) -> None:
        """Generate the datetime parsing code."""
        code += f"""
try:
    {value_variable_name} = from_iso_datetime({value_variable_name})
except (TypeError, AttributeError, ValueError) as error:
    raise {field_obj_variable_name}.make_error(
        "invalid", input={value_variable_name}, obj_type={field_obj_variable_name}.OBJ_TYPE
    ) from error
"""
