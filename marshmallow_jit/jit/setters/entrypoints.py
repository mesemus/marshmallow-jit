# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Factory for builtin deserialization value setters."""

from typing import ClassVar, override

from marshmallow import Schema

from marshmallow_jit.compat import MAField as Field
from marshmallow_jit.jit.registry import Factory

from .base import ValueSetter
from .dict import DictSetter


class BuiltinDeserializationSettersFactory(Factory[[Schema, str, Field], ValueSetter]):
    """Factory for builtin deserialization setters."""

    _setters_by_name: ClassVar[dict[str, ValueSetter]] = {
        "dict": DictSetter(),
    }

    @override
    def find(self, schema: Schema, attr_name: str, field: Field) -> ValueSetter | None:
        # Setters are not field-type-specific, so this factory doesn't apply
        return None

    @override
    def find_by_name(self, name: str, schema: Schema, attr_name: str, field: Field) -> ValueSetter | None:
        return self._setters_by_name.get(name)


builtin_deserialization_setter_factory = BuiltinDeserializationSettersFactory()
