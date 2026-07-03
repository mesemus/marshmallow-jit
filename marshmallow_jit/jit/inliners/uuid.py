# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""UUID field serialization and deserialization inliners."""

from typing import TYPE_CHECKING, cast, override

from marshmallow import Schema
from marshmallow.fields import Field

from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode

from .base import Inliner

if TYPE_CHECKING:
    pass


class UUIDSerializationInliner(Inliner):
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
        with code.indent(f"if {value_variable_name} is not None"):
            code += f"{value_variable_name} = str({value_variable_name})"


class UUIDDeserializationInliner(Inliner):
    """UUID deserialization validates and converts to UUID object.

    Handles bytes (16-byte format) and existing UUID objects, similar to
    marshmallow's UUID._validated method. Returns uuid.UUID objects (not strings).

    If the field overrides _validated(), this inliner will fall back to calling
    the field's _deserialize() method instead.
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
        # Check if _validated is overridden - if so, fall back to field._deserialize()
        from marshmallow.fields import UUID as UUIDField

        from marshmallow_jit.utils import is_overridden

        uuid_field = cast(UUIDField, field)
        if is_overridden(uuid_field._validated, UUIDField._validated):
            # Fall back to calling the field's own _deserialize method
            code += (
                f"{value_variable_name} = {field_obj_variable_name}._deserialize("
                f"{value_variable_name}, {attr_name!r}, data)"
            )
            return

        code.add_import_line("import uuid")
        code += f"""
        if isinstance({value_variable_name}, bytes) and len({value_variable_name}) == 16:
            {value_variable_name} = uuid.UUID(bytes={value_variable_name})
        elif isinstance({value_variable_name}, uuid.UUID):
            # Already a UUID object, keep as-is
            pass
        elif not isinstance({value_variable_name}, str):
            raise {field_obj_variable_name}.make_error("invalid_uuid")
        else:
            try:
                {value_variable_name} = uuid.UUID({value_variable_name})
            except (ValueError, AttributeError, TypeError) as error:
                raise {field_obj_variable_name}.make_error("invalid_uuid") from error
        """
