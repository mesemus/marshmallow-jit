# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Base interface for JIT makers.

Defines the protocol interface without implementation details.
Concrete implementation is in default.py.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from marshmallow_jit.jit.context import Context

if TYPE_CHECKING:
    from marshmallow_jit.jit.makers.dispatcher import PredicateBasedDispatcher
    from marshmallow_jit.schema import JITSchemaBase


class JITMaker:
    """Base class for JIT maker code generators.

    Generates JIT-compiled serializer and deserializer methods for schemas.
    """

    name: str

    def __init__(self, schema: JITSchemaBase) -> None:
        pass

    @property
    def schema_name(self) -> str:
        raise NotImplementedError

    def make_serialize_method(
        self, previous_serialize_method: Callable[..., Any], context: Context
    ) -> Callable[..., Any] | PredicateBasedDispatcher:
        raise NotImplementedError

    def make_deserialize_method(
        self, previous_deserialize_method: Callable[..., Any], context: Context
    ) -> Callable[..., Any] | PredicateBasedDispatcher:
        raise NotImplementedError
