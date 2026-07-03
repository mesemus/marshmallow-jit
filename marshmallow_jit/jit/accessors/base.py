# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Base ValueAccessor class for reading field values during serialization.

Defines the ValueAccessor base class and common code generation
used by all accessor implementations (DictAccessor, InstanceAccessor, HybridAccessor).
"""

from typing import TYPE_CHECKING

from marshmallow import Schema
from marshmallow.fields import Field

from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode
from marshmallow_jit.utils import is_overridden

if TYPE_CHECKING:
    pass


class ValueAccessor:
    """Protocol for accessing field values from objects during serialization.

    Implementations generate code to retrieve values from different object types
    (dicts, objects, or both) with appropriate error handling for missing values.
    """

    name: str

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
        """Generate code to access a field value from an object.

        If the field has ``_CHECK_ATTRIBUTE=False``, no code is generated. If the schema's
        ``get_attribute`` is overridden, it is called; otherwise optimized accessor code is generated.
        """
        if not field._CHECK_ATTRIBUTE:
            return

        check_key = attr_name if field.attribute is None else field.attribute

        # Use the passed-in field_obj_variable_name instead of creating a new one
        field_variable_name = field_obj_variable_name

        if is_overridden(schema.get_attribute, Schema.get_attribute):
            code += f"""
            {value_variable_name} = self.get_attribute(obj, {check_key!r}, default={field_variable_name}.dump_default)
            """
        else:
            self.generate_optimized_accessor(
                code, value_variable_name, schema, attr_name, check_key, field_variable_name, field, context
            )

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
        """Generate optimized accessor code for this specific accessor type."""
        raise NotImplementedError
