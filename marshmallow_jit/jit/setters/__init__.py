# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Value setters for deserialization result construction.

This module provides a decoupled setter system with:
- Base class in ``base.py``
- Individual setters in ``dict.py``
- Registry in ``registry.py``
- Builtin factories in ``entrypoints.py``

Public API:
    from marshmallow_jit.jit.setters import ValueSetter, deserialization_value_setter_registry

For concrete implementations, import directly from their modules:
    from marshmallow_jit.jit.setters.dict import DictSetter
"""

from marshmallow_jit.jit.setters.base import ValueSetter
from marshmallow_jit.jit.setters.registry import deserialization_value_setter_registry

__all__ = [
    "ValueSetter",
    "deserialization_value_setter_registry",
]
