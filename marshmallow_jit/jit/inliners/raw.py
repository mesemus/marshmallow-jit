# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Raw field serialization and deserialization inliners."""

from typing import TYPE_CHECKING, override

from marshmallow import Schema

from marshmallow_jit.compat import MAField as Field
from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode

from .base import Inliner

if TYPE_CHECKING:
    pass


class RawSerializationInliner(Inliner):
    """Raw does not override Field's base (identity) ``_serialize``, so the value passes
    through unchanged - not even a None-check, since the base ``_serialize`` doesn't do
    one either."""

    is_noop = True


class RawDeserializationInliner(Inliner):
    """Raw deserialization is an identity operation - returns the value unchanged.

    Matches marshmallow's Raw._deserialize which simply returns the value as-is.
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
        # Raw just returns the value as-is - no code needed (noop)
        pass
