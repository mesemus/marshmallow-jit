# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""JIT schema mixin and decorators for marshmallow schemas.

Provides JITSchemaMixin, jit_schema decorator, and related utilities
to apply JIT-compiled serialization/deserialization to marshmallow schemas.
"""

import dataclasses
import types
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar, cast

from marshmallow import Schema

from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.setters import ValueSetter

if TYPE_CHECKING:
    SchemaMixinBase = Schema

    from .jit.accessors import ValueAccessor  # noqa: F401


else:
    SchemaMixinBase = object


@dataclasses.dataclass(frozen=True)
class JITSchemaOptions:
    """Runtime options for a single marshmallow-jit schema.

    To set them up, add ``jit_options`` to your schema's ``Meta`` class.
    """

    jit_maker_class: str | None = None

    serializer: str | list[tuple[Callable[[Any], bool], str]] | None = None
    """
    A serializer to use for the schema and serialized object.

    Use cases:
        - None serializer: the default will be used - for mapping, a serializer with Dict accessor,
          for other types a serializer with InstanceAccessor
        - a single serializer: a single serializer to use for any serialized object
        - a single serializer: a single serializer to use for any serialized object
        - a list of (serializer, predicate) tuples: a list of serializers to use for specific serialized object.
          The object is passed to the predicate function, and the serializer is used if the predicate returns True.
          If no predicate returns True, the default serializer (as for None case) will be used.
    """
    serialization_value_accessor: str | None = None
    """Accessor to be used for getting key from the object"""

    deserializer: str | list[tuple[Callable[[Any], bool], str]] | None = None
    """
    A deserializer to use for the schema and serialized object.

    Use cases:
        - None deserializer: the mapping will be used as in most cases, the input to the deserialize is a dict
        - a single deserializer: a single deserializer to use for any serialized object
        - a list of (deserializer, predicate) tuples: a list of deserializers to use for specific serialized object.
          The object is passed to the predicate function, and the deserializer is used if the predicate returns True.
          If no predicate returns True, the default deserializer (as for None case) will be used.
    """

    deserialization_value_setter: type[ValueSetter] | None = None
    """Setter to be used to set value inside an object."""


class JITSchemaBase(SchemaMixinBase):
    """A typing mixin that enables JIT serialization and deserialization."""

    if TYPE_CHECKING:
        _jit_options: JITSchemaOptions
        _jit_applied: bool
    else:
        # Set default values on the class itself (not as ClassVar) so instances inherit them
        # This allows checking _jit_applied before __init__ has run
        _jit_options = None  # Will be set in __init__
        _jit_applied = False

    _original_serialize: Callable[..., Any]
    _original_deserialize: Callable[..., Any]


def get_options_from_meta(schema: type[Schema] | Schema) -> JITSchemaOptions:
    """Extract JIT options from the schema's ``Meta`` class, if any."""
    meta = getattr(schema, "Meta", None)
    if meta is None:
        return JITSchemaOptions()
    jit = getattr(meta, "jit_options", {})
    return JITSchemaOptions(**jit)


P = ParamSpec("P")
T = TypeVar("T")


class JITSchemaMixin(JITSchemaBase):
    """A schema mixin that applies JIT serialization and deserialization options."""

    def __init__(
        self,
        *,
        only: Sequence[str] | set[str] | None = None,
        exclude: Sequence[str] | set[str] = (),
        many: bool | None = None,
        context: dict[str, Any] | None = None,
        load_only: Sequence[str] | set[str] = (),
        dump_only: Sequence[str] | set[str] = (),
        partial: bool | Sequence[str] | set[str] | None = None,
        unknown: str | None = None,
    ) -> None:
        # super().__init__ is a bound method, so we call it directly
        super().__init__(
            only=only,
            exclude=exclude,
            many=many,
            context=context,
            load_only=load_only,
            dump_only=dump_only,
            partial=partial,
            unknown=unknown,
        )

        if self._jit_applied:
            return

        jit_options = get_options_from_meta(self)
        self._jit_options = jit_options
        self._jit_applied = True

        from .jit.makers.registry import maker_registry

        jit_maker = maker_registry.resolve(jit_options.jit_maker_class or "default", self)

        # Store the original serialize/deserialize methods before replacing them
        self._original_serialize = self._serialize
        self._original_deserialize = self._deserialize

        # Replace with JIT-compiled versions
        self._serialize = types.MethodType(  # ty: ignore[invalid-assignment]
            jit_maker.make_serialize_method(self._original_serialize, Context()), self
        )
        self._deserialize = types.MethodType(  # ty: ignore[invalid-assignment]
            jit_maker.make_deserialize_method(self._original_deserialize, Context()), self
        )

    @classmethod
    def _call_init(
        cls,
        instance: JITSchemaBase,
        prev_init: Callable[..., Any],
        *,
        only: Sequence[str] | set[str] | None = None,
        exclude: Sequence[str] | set[str] = (),
        many: bool | None = None,
        context: dict[str, Any] | None = None,
        load_only: Sequence[str] | set[str] = (),
        dump_only: Sequence[str] | set[str] = (),
        partial: bool | Sequence[str] | set[str] | None = None,
        unknown: str | None = None,
    ) -> None:
        """Call the previous ``__init__`` and apply JIT options if not already applied."""
        # prev_init is the unbound __init__ method, so we need to pass self (instance)
        prev_init(
            instance,
            only=only,
            exclude=exclude,
            many=many,
            context=context,
            load_only=load_only,
            dump_only=dump_only,
            partial=partial,
            unknown=unknown,
        )

        if instance._jit_applied:
            return

        jit_options = get_options_from_meta(instance)
        instance._jit_options = jit_options
        instance._jit_applied = True

        from .jit.makers.registry import maker_registry

        jit_maker = maker_registry.resolve(jit_options.jit_maker_class or "default", instance)

        # bind as a method on the instance: a plain function assigned directly to an
        # instance's __dict__ does not go through the descriptor protocol, so `self`
        # would never be supplied automatically
        instance._original_serialize = instance._serialize
        instance._serialize = types.MethodType(  # ty: ignore[invalid-assignment]
            jit_maker.make_serialize_method(instance._original_serialize, Context()), instance
        )
        instance._original_deserialize = instance._deserialize
        instance._deserialize = types.MethodType(  # ty: ignore[invalid-assignment]
            jit_maker.make_deserialize_method(instance._original_deserialize, Context()), instance
        )


def jit_schema(schema: type[Schema], mixin: type[JITSchemaMixin] = JITSchemaMixin) -> type[JITSchemaBase]:
    """Decorator to apply JIT serialization/deserialization to a schema class.

    Args:
        schema: The schema class to decorate
        mixin: The mixin class to use (defaults to JITSchemaMixin)

    Returns:
        The decorated schema class with JIT capabilities
    """
    # Note: cast is used here because we're dynamically modifying the class,
    # but the type system can't verify this at static analysis time.
    # The decorator ensures the returned type has JIT capabilities.
    typed_schema = cast(type[JITSchemaBase], schema)

    # if already applied, return as-is
    if hasattr(typed_schema, "_jit_applied"):
        return typed_schema

    # not applied yet
    typed_schema._jit_applied = False

    previous_init = typed_schema.__init__

    def patched_init(
        self: JITSchemaBase,
        *,
        only: Sequence[str] | set[str] | None = None,
        exclude: Sequence[str] | set[str] = (),
        many: bool | None = None,
        context: dict[str, Any] | None = None,
        load_only: Sequence[str] | set[str] = (),
        dump_only: Sequence[str] | set[str] = (),
        partial: bool | Sequence[str] | set[str] | None = None,
        unknown: str | None = None,
    ) -> None:
        mixin._call_init(
            self,
            previous_init,
            only=only,
            exclude=exclude,
            many=many,
            context=context,
            load_only=load_only,
            dump_only=dump_only,
            partial=partial,
            unknown=unknown,
        )

    typed_schema.__init__ = patched_init

    return typed_schema


def jit_schema_object(schema: Schema, mixin: type[JITSchemaMixin] = JITSchemaMixin) -> JITSchemaBase:
    """Apply JIT serialization/deserialization to a schema instance.

    Args:
        schema: The schema instance to enhance
        mixin: The mixin class to use (defaults to JITSchemaMixin)

    Returns:
        The schema instance with JIT capabilities applied
    """
    # Note: cast is used here because we're dynamically modifying the instance,
    # but the type system can't verify this at static analysis time.
    typed_schema = cast(JITSchemaBase, schema)
    if hasattr(typed_schema, "_jit_applied"):
        return typed_schema

    typed_schema._jit_applied = False
    mixin._call_init(typed_schema, lambda: None)
    return typed_schema
