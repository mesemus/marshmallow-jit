# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Value accessors for reading field values during serialization.

This module provides a decoupled accessor system with:
- Base class in ``base.py``
- Individual accessors in ``dict.py``, ``instance.py``, ``hybrid.py``
- Registry in ``registry.py``
- Builtin factories in ``entrypoints.py``

Public API:
    from marshmallow_jit.jit.accessors import ValueAccessor, serialization_accessor_registry

For concrete implementations, import directly from their modules:
    from marshmallow_jit.jit.accessors.dict import DictAccessor
    from marshmallow_jit.jit.accessors.instance import InstanceAccessor
    from marshmallow_jit.jit.accessors.hybrid import HybridAccessor
"""

from marshmallow_jit.jit.accessors.base import ValueAccessor
from marshmallow_jit.jit.accessors.registry import serialization_accessor_registry

__all__ = [
    "ValueAccessor",
    "serialization_accessor_registry",
]
