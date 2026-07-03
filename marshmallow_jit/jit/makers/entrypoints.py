# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Factory for builtin JIT makers."""

from typing import TYPE_CHECKING, ClassVar, override

from marshmallow import Schema

from marshmallow_jit.jit.registry import Factory

if TYPE_CHECKING:
    from marshmallow_jit.jit.makers.base import JITMaker

from marshmallow_jit.jit.makers.default import JITMaker as DefaultJITMaker


class BuiltinMakersFactory(Factory[[Schema], "JITMaker"]):
    """Factory for builtin JIT makers."""

    _makers_by_name: ClassVar[dict[str, type]] = {
        "default": DefaultJITMaker,
    }

    @override
    def find(self, schema: Schema) -> JITMaker | None:
        # Makers are not selected by name in find(), only by registry resolution
        return None

    @override
    def find_by_name(self, name: str, schema: Schema) -> JITMaker | None:
        maker_class = self._makers_by_name.get(name)
        if maker_class is not None:
            return maker_class(schema)
        return None


builtin_maker_factory = BuiltinMakersFactory()
