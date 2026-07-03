# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Predicate-based dispatch for schemas with multiple serializers/deserializers."""

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from marshmallow_jit.schema import JITSchemaBase


class PredicateBasedDispatcher:
    """Dispatches to compiled methods based on predicate matching.

    Used when a schema has multiple candidate serializers/deserializers. The first
    predicate that returns True determines which method is called.
    """

    def __init__(
        self, code_with_predicates: list[tuple[str, Literal[True] | Callable[[Any], bool], Callable[..., Any]]]
    ) -> None:
        self.code_with_predicates = code_with_predicates

    def __call__(self, schema: JITSchemaBase, obj: Any, *args: object, **kwargs: object) -> dict[str, Any]:
        """Call the first method whose predicate matches the input object."""
        for _name, predicate, method in self.code_with_predicates:
            # Handle both Literal[True] (always match) and callable predicates
            if predicate is True or predicate(obj):
                return method(schema, obj, *args, **kwargs)
        raise ValueError(f"No method matches object {obj!r}, tried {self.code_with_predicates=}")


def _is_mapping(x: object) -> bool:
    """Check if x is a Mapping."""
    return isinstance(x, Mapping)


def _always_true(x: object) -> bool:
    """Always returns True."""
    return True
