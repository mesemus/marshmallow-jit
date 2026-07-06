# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Registry for deserialization value setters."""

from marshmallow import Schema

from marshmallow_jit.compat import MAField as Field
from marshmallow_jit.jit.registry import Registry

from .base import ValueSetter


class DeserializationValueSetterRegistry(Registry[ValueSetter, [Schema, str, Field]]):
    """Registry for deserialization value setters."""

    def __init__(self) -> None:
        super().__init__("marshmallow_jit.setters")


deserialization_value_setter_registry = DeserializationValueSetterRegistry()
"""Registry for deserialization value setters."""

__all__ = [
    "DeserializationValueSetterRegistry",
    "deserialization_value_setter_registry",
]
