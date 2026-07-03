# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Default JIT maker implementation.

Generates JIT-compiled functions with predicate-based dispatch support
for multi-serializer configurations.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Literal, override

from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.makers.base import JITMaker
from marshmallow_jit.jit.makers.dispatcher import PredicateBasedDispatcher, _is_mapping
from marshmallow_jit.jit.python_code import PythonCode
from marshmallow_jit.jit.serializers.base import SchemaDeserializer, SchemaSerializer
from marshmallow_jit.jit.serializers.registry import deserializer_registry, serializer_registry

if TYPE_CHECKING:
    from marshmallow_jit.schema import JITSchemaBase


class JITMaker(JITMaker):
    """Generates JIT-compiled serializer and deserializer methods for schemas."""

    name = "default"

    def __init__(self, schema: JITSchemaBase) -> None:
        self.schema = schema

    @property
    @override
    def schema_name(self) -> str:
        """The name of the schema being compiled."""
        return self.schema.__class__.__name__

    @override
    def make_serialize_method(
        self, previous_serialize_method: Callable[..., Any], context: Context
    ) -> Callable[..., Any] | PredicateBasedDispatcher:
        """Generate a JIT-compiled serializer method.

        The generated method replaces the previous serializer and will have ``self``
        referring to the schema instance in the generated code.
        """

        with context.within_schema(self.schema):
            code_with_predicates = []
            for name, predicate, serializer in self.get_serializers():
                code = PythonCode()
                serializer_function_name = code.generate_variable(f"_jit_serialize_{self.schema_name}")
                with code.indent(
                    f"def {serializer_function_name}(self, obj: typing.Any, "
                    f"*, many: bool = False) -> dict[str, typing.Any]"
                ):
                    serializer.generate_serialize_method_content(code, context)

                method = code.compile({})[serializer_function_name]
                method.__source__ = str(code)
                code_with_predicates.append((name, predicate, method))

            if len(code_with_predicates) == 1:
                # just return the method
                return code_with_predicates[0][2]
            else:
                return PredicateBasedDispatcher(code_with_predicates)

    def get_serializers(
        self,
    ) -> list[tuple[str, Literal[True] | Callable[[Any], bool], SchemaSerializer]]:
        """Get the list of configured serializers with their predicates."""
        if self.schema._jit_options.serializer is None:
            # the default case - for mapping use
            return [
                ("mapping", _is_mapping, serializer_registry.resolve("mapping", self.schema)),
                ("instance", True, serializer_registry.resolve("instance", self.schema)),
            ]
        elif isinstance(self.schema._jit_options.serializer, str):
            return [
                (
                    "default",
                    True,
                    serializer_registry.resolve(self.schema._jit_options.serializer, self.schema),
                )
            ]
        else:
            # list of callables and serializers
            return [
                (
                    f"serializer_{idx}",
                    predicate,
                    serializer_registry.resolve(serializer, self.schema),
                )
                for idx, (predicate, serializer) in enumerate(self.schema._jit_options.serializer)
            ]

    @override
    def make_deserialize_method(
        self, previous_deserialize_method: Callable[..., Any], context: Context
    ) -> Callable[..., Any] | PredicateBasedDispatcher:
        """Generate a JIT-compiled deserializer method.

        The generated method replaces the previous deserializer and will have ``self``
        referring to the schema instance in the generated code.
        """

        with context.within_schema(self.schema):
            code_with_predicates = []
            for name, predicate, deserializer in self.get_deserializers():
                code = PythonCode()
                # Use compatibility imports for marshmallow 3/4
                code.add_import_line("from marshmallow_jit.compat import RAISE, INCLUDE, EXCLUDE")
                code.add_import_line("from marshmallow.error_store import ErrorStore")
                code.add_import_line("from collections.abc import Mapping")
                code.add_import_line("from marshmallow.exceptions import ValidationError")
                deserializer_function_name = code.generate_variable(f"_jit_deserialize_{self.schema_name}")
                with code.indent(
                    f"""def {deserializer_function_name}(
                            self,
                            data: (
                                typing.Mapping[str, typing.Any]
                                | typing.Iterable[typing.Mapping[str, typing.Any]]
                            ),
                            *,
                            error_store: ErrorStore,
                            many: bool = False,
                            partial=None,
                            unknown=RAISE,
                            index=None,
                        ) -> typing.Any | list[typing.Any]
                    """
                ):
                    deserializer.generate_deserialize_method_content(code, context)

                method = code.compile({})[deserializer_function_name]
                method.__source__ = str(code)
                code_with_predicates.append((name, predicate, method))

            if len(code_with_predicates) == 1:
                # just return the method
                return code_with_predicates[0][2]
            else:
                return PredicateBasedDispatcher(code_with_predicates)

    def get_deserializers(
        self,
    ) -> list[tuple[str, Literal[True] | Callable[[Any], bool], SchemaDeserializer]]:
        """Get the list of configured deserializers with their predicates."""
        if not self.schema._jit_options.deserializer:
            # the default case - for mapping use
            return [
                ("default", True, deserializer_registry.resolve("mapping", self.schema)),
            ]
        elif isinstance(self.schema._jit_options.deserializer, str):
            return [
                (
                    "default",
                    True,
                    deserializer_registry.resolve(self.schema._jit_options.deserializer, self.schema),
                )
            ]
        else:
            # list of callables and serializers
            return [
                (
                    f"deserializer_{idx}",
                    predicate,
                    deserializer_registry.resolve(deserializer, self.schema),
                )
                for idx, (predicate, deserializer) in enumerate(self.schema._jit_options.deserializer)
            ]
