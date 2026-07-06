# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Integration with marshmallow-utils' ``NestedAttribute`` field.

Registers a value accessor factory that routes ``NestedAttribute`` fields to
``InstanceAccessor``. Registered as a plugin entry point, so this module is
always imported when the accessor registry loads its factories - it becomes
a no-op when marshmallow-utils is not installed.
"""

import importlib.util
from typing import override

from marshmallow import Schema

from marshmallow_jit.compat import MAField as Field
from marshmallow_jit.jit.accessors.base import ValueAccessor
from marshmallow_jit.jit.accessors.instance import InstanceAccessor
from marshmallow_jit.jit.registry import Factory

_HAS_MARSHMALLOW_UTILS = importlib.util.find_spec("marshmallow_utils") is not None


class NestedAttributeAccessorFactory(Factory[[Schema, str, Field], ValueAccessor]):
    """Routes marshmallow-utils' ``NestedAttribute`` fields to ``InstanceAccessor``."""

    @override
    def find(self, schema: Schema, attr_name: str, field: Field) -> ValueAccessor | None:
        if not _HAS_MARSHMALLOW_UTILS:
            return None
        from marshmallow_utils.fields.nestedattr import (
            NestedAttribute,  # type: ignore[import-not-found,unresolved-import]
        )

        if isinstance(field, NestedAttribute):
            return InstanceAccessor()
        return None

    @override
    def find_by_name(self, name: str, *args: object, **kwargs: object) -> ValueAccessor | None:
        return None


nested_attribute_accessor_factory = NestedAttributeAccessorFactory()
