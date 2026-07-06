# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Boolean field serialization and deserialization inliners."""

from typing import TYPE_CHECKING, cast, override

from marshmallow import Schema
from marshmallow.fields import Boolean as BooleanField

from marshmallow_jit.compat import MAField as Field
from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode

from .base import Inliner

if TYPE_CHECKING:
    pass


class BooleanSerializationInliner(Inliner):
    """Boolean has complex truthy/falsy logic that's hard to inline correctly.

    We fall back to calling the field's native _serialize method to ensure
    correct handling of custom truthy/falsy sets and edge cases.
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
        # Fall back to the field's native _serialize method
        # Note: We pass the value directly since we're already inside the serialization flow
        code += (
            f"{value_variable_name} = {field_obj_variable_name}._serialize({value_variable_name}, {attr_name!r}, obj)"
        )


class BooleanDeserializationInliner(Inliner):
    """Boolean deserialization handles truthy/falsy value conversion.

    Handles the same cases as marshmallow's Boolean._deserialize:
    - If truthy is empty (default), converts using bool()
    - If truthy is set, checks if value is in truthy (returns True) or falsy (returns False)
    - Raises 'invalid' error for values not in either set
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
        field = cast(BooleanField, field)

        # If no custom truthy/falsy sets, just use bool()
        if not field.truthy and not field.falsy:
            code += f"{value_variable_name} = bool({value_variable_name})"
            return

        # Custom truthy/falsy sets - need to check membership
        truthy_var = code.add_variable(f"field__{attr_name}__truthy", field.truthy)
        falsy_var = code.add_variable(f"field__{attr_name}__falsy", field.falsy)

        code += f"""
        try:
            if {value_variable_name} in {truthy_var}:
                {value_variable_name} = True
            elif {value_variable_name} in {falsy_var}:
                {value_variable_name} = False
            else:
                raise {field_obj_variable_name}.make_error("invalid", input={value_variable_name})
        except TypeError as error:
            raise {field_obj_variable_name}.make_error("invalid", input={value_variable_name}) from error
        """
