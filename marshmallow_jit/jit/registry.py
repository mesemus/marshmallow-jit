# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Plugin registries for marshmallow-jit extensibility.

Defines the generic ``Factory`` and ``Registry`` infrastructure used by the
serializer, accessor, setter, inliner, and maker packages to build their own
typed registries.
"""

from collections.abc import Callable
from importlib import metadata
from typing import TYPE_CHECKING, Any, overload, override

from marshmallow_jit.log import log

if TYPE_CHECKING:
    pass
else:
    # Runtime imports to avoid circular dependencies
    # These are imported lazily when needed
    pass

#
# Schema serializers
#


class Factory[**P, T]:
    """Protocol for object factories used in plugin registries."""

    def find(self, *args: P.args, **kwargs: P.kwargs) -> T | None:
        """Create an object for the given args/kwargs, or return None if not supported."""

    def find_by_name(self, name: str, *args: P.args, **kwargs: P.kwargs) -> T | None:
        """Find an object by its registered name, or return None if not found."""


class ConstantFactory[**P, T](Factory[P, T]):
    """A factory that always returns the same pre-configured value."""

    def __init__(self, value: Callable[P, T] | type[T], allow_find: bool = True) -> None:
        self.value = value
        self.allow_find = allow_find

    @override
    def find(self, *args: P.args, **kwargs: P.kwargs) -> T | None:
        if not self.allow_find:
            return None
        return self.value(*args, **kwargs)

    @override
    def find_by_name(self, name: str, *args: P.args, **kwargs: P.kwargs) -> T | None:
        if hasattr(self.value, "name") and name == self.value.name:
            return self.value(*args, **kwargs)
        return None


class Registry[T, **P]:
    """Registry for plugin-style extensibility with factory discovery.

    Supports both builtin factories and entry point plugins. Factories are
    searched in order: entry points first, then builtin factories.
    """

    def __init__(self, entrypoint_name: str) -> None:
        """
        Initialize the registry. Will lazily load the factories and builtin factories,
        the builtin factories are registered as entrypoint_name.builtin
        """
        self.entrypoint_name = entrypoint_name
        self._entrypoint_factories: list[Factory[P, T]] = []
        self._builtin_factories: list[Factory[P, T]] = []

        self._entrypoint_loaded = False

    def _load(self) -> None:
        """Load entrypoint and builtin factories, caching them as instance attributes."""
        self._entrypoint_factories = [
            ep.load() for ep in sorted(metadata.entry_points(group=self.entrypoint_name), key=lambda e: e.name)
        ]
        self._builtin_factories = [
            ep.load()
            for ep in sorted(
                metadata.entry_points(group=f"{self.entrypoint_name}.builtin"),
                key=lambda e: e.name,
            )
        ]
        self._entrypoint_loaded = True

    @property
    def entrypoint_factories(self) -> list[Factory[P, T]]:
        """Return actual entrypoint factories."""
        if not self._entrypoint_loaded:
            self._load()
        return self._entrypoint_factories

    @property
    def builtin_factories(self) -> list[Factory[P, T]]:
        """Return actual builtin factories."""
        if not self._entrypoint_loaded:
            self._load()
        return self._builtin_factories

    @property
    def factories(self) -> list[Factory[P, T]]:
        """All available factories (entry points + builtins)."""
        return self.entrypoint_factories + self.builtin_factories

    def add_factory(self, factory: Factory[P, T]) -> None:
        """Add a factory to the front of the search order (entry point priority)."""
        self.entrypoint_factories.insert(0, factory)

    def add_builtin_factory(self, factory: Factory[P, T]) -> None:
        """Add a builtin factory to the end of the search order."""
        self.builtin_factories.append(factory)

    def _build_error_context(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
        """Build detailed error context for registry resolution failures.

        Includes field type hierarchy, schema information, and helpful debugging hints.
        """
        parts = []

        # Extract field and schema from args if present
        schema = None
        field = None
        attr_name = None

        # Common patterns: (schema, attr_name, field) or (schema,)
        if len(args) >= 3:
            schema, attr_name, field = args[0], args[1], args[2]
        elif len(args) == 1:
            schema = args[0]

        # Build type hierarchy for field
        if field is not None:
            field_type = type(field)
            mro_names = [cls.__name__ for cls in field_type.__mro__ if cls is not object]
            parts.append(f"Field type: {field_type.__module__}.{field_type.__qualname__}")
            parts.append(f"Field MRO: {' -> '.join(mro_names)}")
            parts.append(f"Field name: {getattr(field, 'name', '<unnamed>')!r}")

        # Build schema info
        if schema is not None:
            schema_type = type(schema)
            parts.append(f"Schema: {schema_type.__module__}.{schema_type.__qualname__}")

        # Attribute name if available
        if attr_name is not None:
            parts.append(f"Attribute: {attr_name!r}")

        # Additional context from kwargs
        if kwargs:
            parts.append(f"Additional kwargs: {kwargs}")

        return "\n".join(parts)

    def _log_resolution_failure(self, args: tuple[Any, ...], kwargs: dict[str, Any], error_reason: str) -> None:
        """Log detailed information about registry resolution failure.

        Logs at WARNING level with full context for debugging.
        """
        context = self._build_error_context(args, kwargs)

        log.warning(
            "Registry resolution failed: %s\n%s",
            error_reason,
            context,
        )

    def find(self, *args: P.args, **kwargs: P.kwargs) -> T:
        """Find the first factory matching the given arguments.

        Raises KeyError with detailed context if no factory matches.
        """
        return self._find_impl(args, kwargs, silent=False)

    def try_find(self, *args: P.args, **kwargs: P.kwargs) -> T:
        """Find the first factory matching the given arguments (silent mode).

        Like find() but doesn't log warnings when no factory matches.
        Useful when checking for optional field-specific handlers.

        Raises KeyError without logging if no factory matches.
        """
        return self._find_impl(args, kwargs, silent=True)

    def _find_impl(self, args: tuple[Any, ...], kwargs: dict[str, Any], silent: bool) -> T:
        """Internal implementation of find with silent option."""
        for factory in self.factories:
            if (ret := factory.find(*args, **kwargs)) is not None:
                return ret

        # Log detailed warning before raising (unless silenced)
        if not silent:
            self._log_resolution_failure(args, kwargs, f"No factory found for {self.entrypoint_name}")

        raise KeyError(
            f"Could not find factory {self.entrypoint_name} for {args} {kwargs}. "
            f"See logs for detailed context including field type hierarchy."
        )

    if TYPE_CHECKING:

        @overload
        def resolve(self, obj_or_string: str, *args: P.args, **kwargs: P.kwargs) -> T: ...  # type: ignore[overload-overlap]

        @overload
        def resolve(self, obj_or_string: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T: ...

        @overload
        def resolve(self, obj_or_string: type[T], *args: P.args, **kwargs: P.kwargs) -> T: ...

    def resolve(
        self,
        obj_or_string: str | type[T] | Callable[P, T],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        """Resolve a string name to a factory result, or call a callable directly.

        Raises KeyError with detailed context if string name cannot be resolved.

        Args:
            obj_or_string: Either a string name to look up, a callable to invoke,
                          or a type to instantiate
            *args: Positional arguments passed to the callable/factory
            **kwargs: Keyword arguments passed to the callable/factory

        Returns:
            The resolved object of type T

        Raises:
            KeyError: If a string name cannot be resolved to any factory
        """
        if isinstance(obj_or_string, str):
            for factory in self.factories:
                if (ret := factory.find_by_name(obj_or_string, *args, **kwargs)) is not None:
                    return ret

            # Log detailed warning before raising
            self._log_resolution_failure(
                args,
                kwargs,
                f"No factory found with name '{obj_or_string}' for {self.entrypoint_name}",
            )

            raise KeyError(
                f"Could not find factory {self.entrypoint_name} for '{obj_or_string}'. "
                f"See logs for detailed context including available factories."
            )
        return obj_or_string(*args, **kwargs)
