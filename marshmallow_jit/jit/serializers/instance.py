# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Schema serializer for object instances."""

from typing import TYPE_CHECKING

from marshmallow_jit.jit.accessors.instance import InstanceAccessor
from marshmallow_jit.jit.serializers.mapping import BaseSchemaSerializer

if TYPE_CHECKING:
    from marshmallow_jit.schema import JITSchemaBase


class InstanceSchemaSerializer(BaseSchemaSerializer):
    """Serializer optimized for object instances using InstanceAccessor."""

    name = "instance"

    def __init__(self, schema: JITSchemaBase) -> None:
        super().__init__(schema)
        self.default_value_accessor = InstanceAccessor
