# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Schema serializer for both dicts and objects."""

from typing import TYPE_CHECKING

from marshmallow_jit.jit.accessors.hybrid import HybridAccessor
from marshmallow_jit.jit.serializers.mapping import BaseSchemaSerializer

if TYPE_CHECKING:
    from marshmallow_jit.schema import JITSchemaBase


class HybridSchemaSerializer(BaseSchemaSerializer):
    """Serializer that handles both dicts and objects using HybridAccessor."""

    name = "hybrid"

    def __init__(self, schema: JITSchemaBase) -> None:
        super().__init__(schema)
        self.default_value_accessor = HybridAccessor
