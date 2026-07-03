# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""JIT makers: generate compiled serializer/deserializer methods for schemas.

This module provides a decoupled maker system with:
- Base interface in ``base.py``
- Predicate-based dispatch in ``dispatcher.py``
- Default implementation in ``default.py``
- Registry in ``registry.py``
- Builtin factories in ``entrypoints.py``

Public API:
    from marshmallow_jit.jit.makers import JITMaker, maker_registry

For the default implementation, import directly from its module:
    from marshmallow_jit.jit.makers.default import JITMaker
"""

from marshmallow_jit.jit.makers.base import JITMaker
from marshmallow_jit.jit.makers.registry import maker_registry

__all__ = [
    "JITMaker",
    "maker_registry",
]
