# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Base ValueSetter class for setting deserialized values into result objects."""

from typing import TYPE_CHECKING

from marshmallow import Schema
from marshmallow.fields import Field

from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode

if TYPE_CHECKING:
    pass


class ValueSetter:
    """Protocol for setting deserialized values into result objects.

    Implementations generate code to insert deserialized field values into
    the result dictionary or object, supporting both simple keys and dotted paths.
    """

    name: str

    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

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
        """Generate code to set a deserialized value into the result object."""
        raise NotImplementedError
