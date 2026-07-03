# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Registry for JIT makers."""

from marshmallow import Schema

from marshmallow_jit.jit.makers.base import JITMaker
from marshmallow_jit.jit.registry import Registry


class MakerRegistry(Registry[JITMaker, [Schema]]):
    """Registry for JIT makers."""

    def __init__(self) -> None:
        super().__init__("marshmallow_jit.makers")


maker_registry = MakerRegistry()
"""Registry for JIT makers."""

__all__ = [
    "MakerRegistry",
    "maker_registry",
]
