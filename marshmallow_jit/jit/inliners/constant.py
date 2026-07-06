# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Constant field serialization and deserialization inliners."""

from typing import TYPE_CHECKING, cast, override

from marshmallow import Schema

from marshmallow_jit.compat import MAConstant
from marshmallow_jit.compat import MAField as Field
from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode

from .base import Inliner

if TYPE_CHECKING:
    pass


class ConstantSerializationInliner(Inliner):
    """Constant always returns its fixed value regardless of input."""

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
        field = cast(MAConstant, field)
        # Constant._serialize just returns self.constant, ignoring the input value entirely
        code += f"{value_variable_name} = {field.constant!r}"


class ConstantDeserializationInliner(Inliner):
    """Constant deserialization always returns the fixed constant value, ignoring input.

    Matches marshmallow's Constant._deserialize which simply returns self.constant.
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
        field = cast(MAConstant, field)
        # Constant._deserialize just returns self.constant, ignoring the input value entirely
        code += f"{value_variable_name} = {field.constant!r}"
