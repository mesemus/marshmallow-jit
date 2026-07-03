# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Factory for builtin serialization value accessors.

Maps accessor names to their implementations (dict, instance, hybrid).
"""

from typing import ClassVar, override

from marshmallow import Schema
from marshmallow.fields import Field

from marshmallow_jit.jit.registry import Factory

from .base import ValueAccessor
from .dict import DictAccessor
from .hybrid import HybridAccessor
from .instance import InstanceAccessor


class BuiltinSerializationAccessorsFactory(Factory[[Schema, str, Field], ValueAccessor]):
    """Factory for builtin serialization accessors."""

    _accessors_by_name: ClassVar[dict[str, ValueAccessor]] = {
        "dict": DictAccessor(),
        "instance": InstanceAccessor(),
        "hybrid": HybridAccessor(),
    }

    @override
    def find(self, schema: Schema, attr_name: str, field: Field) -> ValueAccessor | None:
        # Accessors are not field-type-specific, so this factory doesn't apply
        return None

    @override
    def find_by_name(self, name: str, schema: Schema, attr_name: str, field: Field) -> ValueAccessor | None:
        return self._accessors_by_name.get(name)


builtin_serialization_accessor_factory = BuiltinSerializationAccessorsFactory()
