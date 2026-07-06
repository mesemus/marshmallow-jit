# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Schema serializers and deserializers for mapping (dict-like) objects."""

from typing import TYPE_CHECKING, override

from marshmallow import fields as marshmallow_fields

from marshmallow_jit.compat import MAField as Field
from marshmallow_jit.config import FAIL_ON_UNKNOWN_FIELD_TYPE
from marshmallow_jit.jit.accessors.base import ValueAccessor
from marshmallow_jit.jit.accessors.dict import DictAccessor
from marshmallow_jit.jit.accessors.registry import serialization_accessor_registry
from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.inliners.base import Inliner
from marshmallow_jit.jit.inliners.registry import (
    deserialization_inliner_registry,
    serialization_inliner_registry,
)
from marshmallow_jit.jit.python_code import PythonCode
from marshmallow_jit.jit.serializers.base import SchemaDeserializer, SchemaSerializer
from marshmallow_jit.jit.setters.base import ValueSetter
from marshmallow_jit.jit.setters.dict import DictSetter
from marshmallow_jit.jit.setters.registry import deserialization_value_setter_registry
from marshmallow_jit.log import log
from marshmallow_jit.utils import is_overridden, is_property_overridden

if TYPE_CHECKING:
    from marshmallow_jit.schema import JITSchemaBase


class BaseSchemaSerializer(SchemaSerializer):
    """Base class for generating JIT-compiled serialization methods.

    Generates code to serialize schema fields by combining value accessors
    (to read values) with inliners (to transform them).
    """

    name: str
    default_value_accessor: type[ValueAccessor]  # Will be overridden by subclasses

    def __init__(self, schema: JITSchemaBase) -> None:
        self.schema = schema

    @override
    @property
    def schema_name(self) -> str:
        """The name of the schema being serialized."""
        return self.schema.__class__.__name__

    @override
    def generate_serialize_method_content(self, code: PythonCode, context: Context) -> None:
        """Generate the body of the compiled ``_serialize`` method."""

        # we do not optimize arrays here (but custom serializer might),
        # so we are just calling the base serialize method for each item
        # and collecting the results into a list

        with context.within_serializer(self):
            code += """
            if many and obj is not None:
                return [self._serialize(d, many=False) for d in obj]
            """

            ret_var = f"ret_{context.level}"
            code += f"{ret_var} = {{}}" if self.schema.dict_class is dict else f"{ret_var} = self.dict_class()"

            for attr_name, field_obj in self.schema.dump_fields.items():
                key = field_obj.data_key if field_obj.data_key is not None else attr_name
                self.generate_serializer_field(code, attr_name, field_obj, key, context, ret_var)

            code += f"return {ret_var}"

    @override
    def generate_serializer_field(
        self, code: PythonCode, attr_name: str, field_obj: Field, key: str, context: Context, ret_var: str
    ) -> None:
        """Generate serialization code for a single field."""
        # always reuse the same variable name for the value to minimize stack usage
        value_variable = "value"

        # Create a variable for the field object to be passed to inliners
        field_obj_var = code.add_variable("field", field_obj)

        value_getter = self.get_value_accessor(attr_name, field_obj)
        value_inliner = self.get_value_inliner(attr_name, field_obj)

        if value_inliner is None:
            if FAIL_ON_UNKNOWN_FIELD_TYPE:
                raise ValueError(
                    f"Unknown field: {attr_name} of type {field_obj.__class__.__name__} within {self.schema_name}"
                )
            else:
                log.warning(
                    "Unknown field: %s of type %s within %s", attr_name, field_obj.__class__.__name__, self.schema_name
                )
            self.generate_fallback(code, value_variable, field_obj, attr_name)
            with code.indent(f"if {value_variable} is not missing"):
                code += f"{ret_var}[{key!r}] = {value_variable}"
        else:
            value_getter.generate_code(code, value_variable, field_obj_var, self.schema, attr_name, field_obj, context)
            # merged into a single "is not missing" block: the inlined transform and the
            # ret[] assignment both only need to happen when the value is actually present

            if field_obj._CHECK_ATTRIBUTE:
                # attribute was gotten, do not proceed if missing
                with code.indent(f"if {value_variable} is not missing"):
                    self._generate_inlined_assignment(
                        code, value_variable, field_obj_var, value_inliner, ret_var, key, attr_name, field_obj, context
                    )
            else:
                # if no value at this point, do not check for missing
                self._generate_inlined_assignment(
                    code, value_variable, field_obj_var, value_inliner, ret_var, key, attr_name, field_obj, context
                )

    def _generate_inlined_assignment(
        self,
        code: PythonCode,
        value_variable: str,
        field_obj_variable: str,
        inliner: Inliner,
        ret_var: str,
        key: str,
        attr_name: str,
        field_obj: Field,
        context: Context,
    ) -> None:
        """Generate code for inlined field transformation and assignment."""
        if not inliner.is_noop:
            inliner.generate_code(code, value_variable, field_obj_variable, self.schema, attr_name, field_obj, context)
            # Only add a second "is not missing" check if the inliner might return missing
            # (e.g., Method/Function fields). Most inliners don't need this.
            if inliner.can_return_missing:
                with code.indent(f"if {value_variable} is not missing"):
                    code += f"{ret_var}[{key!r}] = {value_variable}"
            else:
                code += f"{ret_var}[{key!r}] = {value_variable}"
        else:
            code += f"{ret_var}[{key!r}] = {value_variable}"

    def generate_fallback(self, code: PythonCode, value_variable: str, field_obj: Field, attr_name: str) -> None:
        """Generate fallback code using the field's native ``serialize`` method."""
        var_name = code.add_variable(f"{attr_name}__field", field_obj)
        code += f"{value_variable} = {var_name}.serialize({attr_name!r}, obj, accessor=self.get_attribute)"

    def get_value_accessor(self, attr_name: str, field_obj: Field) -> ValueAccessor:
        """Get the accessor for reading values from this field."""
        if self.schema._jit_options.serialization_value_accessor is not None:
            return serialization_accessor_registry.resolve(
                self.schema._jit_options.serialization_value_accessor, self.schema, attr_name, field_obj
            )
        # Check for field-specific accessor factories (e.g., NestedAttribute -> InstanceAccessor)
        try:
            return serialization_accessor_registry.find(self.schema, attr_name, field_obj)
        except KeyError:
            pass
        return self.default_value_accessor()

    def get_value_inliner(self, attr_name: str, field_obj: Field) -> Inliner | None:
        """Get the inliner for transforming this field's value, or None if not available."""
        try:
            return serialization_inliner_registry.find(self.schema, attr_name, field_obj)
        except KeyError:
            # Registry.find() raises KeyError (not ValueError) when no factory matches -
            # that just means this field type has no builtin Inliner, so fall back.
            return None


class BaseSchemaDeserializer(SchemaDeserializer):
    """Base class for generating JIT-compiled deserialization methods.

    Generates code to deserialize schema fields by combining inliners
    (to transform values) with value setters (to store results).
    """

    name: str
    default_value_setter: type[ValueSetter] = DictSetter

    def __init__(self, schema: JITSchemaBase) -> None:
        self.schema = schema

    @override
    @property
    def schema_name(self) -> str:
        """The name of the schema being deserialized."""
        return self.schema.__class__.__name__

    @override
    def generate_deserialize_method_content(self, code: PythonCode, context: Context) -> None:
        """Generate the body of the compiled ``_deserialize`` method."""

        # note: could be split to the cases where partial is a collection and is not
        # for further optimization
        with context.within_deserializer(self):
            code += """
            index_errors = self.opts.index_errors
            index = index if index_errors else None
            if many:
                # we do not optimize arrays here (but custom serializer might),
                # so we are just calling the base serialize method for each item
                # and collecting the results into a list

                return self._deserialize_before_jit(
                    data, error_store=error_store, many=many, partial=partial, unknown=unknown, index=index
                )
            """
            ret_var = f"ret_{context.level}"
            code += f"{ret_var} = {{}}" if self.schema.dict_class is dict else f"{ret_var} = self.dict_class()"
            self._check_is_mapping(code, ret_var)

            # Optimized partial check: fast path for common cases (True, False, None, list/tuple/set)
            code += """
            if partial is True or partial is False or partial is None:
                partial_is_collection = False
            elif isinstance(partial, (list, tuple, set)):
                partial_is_collection = True
            else:
                # Fallback to marshmallow's is_collection for edge cases (querysets, etc.)
                partial_is_collection = marshmallow.utils.is_collection(partial)
            """
            for attr_name, field_obj in self.schema.load_fields.items():
                field_name = field_obj.data_key if field_obj.data_key is not None else attr_name
                field_obj_var = code.add_variable("field", field_obj)
                field_obj_deserialize_var = code.add_variable("field_obj_deserialize", field_obj.deserialize)
                inner_field_obj_deserialize_var = code.add_variable("field_obj_deserialize", field_obj._deserialize)

                # Check if deserialize() or _validate_missing() are overridden
                deserialize_is_overridden = is_overridden(field_obj.deserialize, marshmallow_fields.Field.deserialize)
                validate_missing_is_overridden = is_overridden(
                    field_obj._validate_missing, marshmallow_fields.Field._validate_missing
                )

                field_obj_key = field_obj.attribute or attr_name
                value_setter = self.get_value_setter(attr_name, field_obj)
                value_inliner = self.get_value_inliner(attr_name, field_obj)

                # Determine if we need to prepare partial kwargs (d_kwargs)
                # - If deserialize() is overridden, we must call it with **d_kwargs
                # - If _validate_missing() is overridden, we must call deserialize() with **d_kwargs
                # - If no inliner exists, we fall back to _deserialize which uses **d_kwargs
                # - If we have an inliner that needs partial kwargs, generate d_kwargs
                # - Otherwise, the inliner handles deserialization directly without d_kwargs
                needs_partial_kwargs = (
                    deserialize_is_overridden
                    or validate_missing_is_overridden
                    or value_inliner is None
                    or value_inliner.needs_partial_kwargs
                )

                code += f"""
                try:
                    value = data[{field_name!r}]
                except:
                    value = missing
                """
                with code.indent(
                    f"""if (
                    value is not missing
                    or not(partial is True or (partial_is_collection and {attr_name!r} in partial))
                )"""
                ):
                    if needs_partial_kwargs:
                        code += f"""
                        # If we have a value or not ignoring missing fields
                        d_kwargs = {{}}
                        # Allow partial loading of nested schemas.
                        if partial_is_collection:
                            prefix = {field_name!r} + "."
                            len_prefix = len(prefix)
                            sub_partial = [f[len_prefix:] for f in partial if f.startswith(prefix)]
                            d_kwargs["partial"] = sub_partial
                        elif partial is not None:
                            d_kwargs["partial"] = partial
                        """

                    # Deserialize the value
                    if deserialize_is_overridden or validate_missing_is_overridden:
                        # Use the full deserialize() method for custom fields
                        code += f"""
                        try:
                            value = {field_obj_deserialize_var}(
                                value,
                                {field_name!r},
                                data,
                                **d_kwargs,
                            )
                        except ValidationError as error:
                            error_store.store_error(error.messages, {field_name!r}, index=index)
                            return error.valid_data or missing
                        """
                    else:
                        # Inline the base Field.deserialize() logic for optimization
                        code += """
                        # Inline Field.deserialize() - validate missing, handle None, call _deserialize, validate
                        """
                        with code.indent("try"):
                            # Handle missing/required/null validation and default values
                            with code.indent("if value is missing"):
                                code += f"""
                                if {field_obj_var}.required:
                                    raise {field_obj_var}.make_error("required")
                                """
                                if callable(field_obj.load_default):
                                    code += f"value = {field_obj_var}.load_default()"
                                else:
                                    code += f"value = {field_obj_var}.load_default"

                            code += f"""
                            elif value is None:
                                if not {field_obj_var}.allow_none:
                                    raise {field_obj_var}.make_error("null")
                                value = None
                            """
                            if value_inliner is not None:
                                # Use the optimized inliner for deserialization directly on 'value'
                                with code.indent("else"):
                                    value_inliner.generate_code(
                                        code, "value", field_obj_var, self.schema, attr_name, field_obj, context
                                    )
                                    # Generate validation code via the inliner
                                    value_inliner.generate_validate(
                                        code, "value", field_obj_var, self.schema, attr_name, field_obj, context
                                    )
                            else:
                                # Call the optimized _deserialize method directly
                                with code.indent("else"):
                                    code += f"""
                                        value = {inner_field_obj_deserialize_var}(
                                            value,
                                            {field_name!r},
                                            data,
                                            **d_kwargs,
                                        )
                                    """
                                    # Call _validate only if needed (compile-time check)
                                    has_custom_validate = is_overridden(field_obj._validate, Field._validate)
                                    has_custom_validate_all = is_property_overridden(field_obj, "_validate_all", Field)
                                    has_validators = bool(field_obj.validators)

                                    if has_custom_validate or has_custom_validate_all or has_validators:
                                        with code.indent("if value is not missing"):
                                            code += f"{field_obj_var}._validate(value)"

                        with code.indent("except ValidationError as error"):
                            code += f"""
                            error_store.store_error(error.messages, {field_name!r}, index=index)
                            return error.valid_data if error.valid_data is not None else missing
                            """

                    with code.indent("if value is not missing"):
                        value_setter.generate_code(
                            code,
                            ret_var,  # result_name - the result dict variable
                            "value",  # value_variable_name - the deserialized value
                            field_obj_key,
                            field_obj_var,  # field_obj_variable_name
                            self.schema,  # schema
                            attr_name,  # attr_name
                            field_obj,  # field
                            context,  # context
                        )

            fields = {
                field_obj.data_key if field_obj.data_key is not None else field_name
                for field_name, field_obj in self.schema.load_fields.items()
            }
            loaded_fields_var = code.add_variable("loaded_fields", fields)
            code += f"""
            if unknown != EXCLUDE:
                for key in set(data) - {loaded_fields_var}:
                    value = data[key]
                    if unknown == INCLUDE:
                        {ret_var}[key] = value
                    elif unknown == RAISE:
                        error_store.store_error(
                            [self.error_messages["unknown"]],
                            key,
                            (index if index_errors else None),
                        )
            """

            code += f"return {ret_var}"

    def _check_is_mapping(self, code: PythonCode, ret_var: str) -> None:
        """Generate runtime check that input data is a mapping."""
        code += f"""
        if not isinstance(data, Mapping):
            error_store.store_error([self.error_messages["type"]], index=index)
            return {ret_var}
        """

    def get_value_setter(self, attr_name: str, field_obj: Field) -> ValueSetter:
        """Get the setter for storing deserialized values for this field."""
        if self.schema._jit_options.deserialization_value_setter is not None:
            return deserialization_value_setter_registry.resolve(
                self.schema._jit_options.deserialization_value_setter, self.schema, attr_name, field_obj
            )
        try:
            return deserialization_value_setter_registry.find(self.schema, attr_name, field_obj)
        except KeyError:
            pass
        return self.default_value_setter()

    def get_value_inliner(self, attr_name: str, field_obj: Field) -> Inliner | None:
        """Get the inliner for transforming this field's value during deserialization, or None if not available."""
        try:
            return deserialization_inliner_registry.find(self.schema, attr_name, field_obj)
        except KeyError:
            # Registry.find() raises KeyError (not ValueError) when no factory matches -
            # that just means this field type has no builtin Inliner, so fall back.
            return None


class MappingSchemaSerializer(BaseSchemaSerializer):
    """Serializer optimized for dict-like objects using DictAccessor."""

    name = "mapping"

    def __init__(self, schema: JITSchemaBase) -> None:
        super().__init__(schema)
        self.default_value_accessor = DictAccessor


class MappingSchemaDeserializer(BaseSchemaDeserializer):
    """Deserializer for dict-like input data using DictSetter."""

    name = "mapping"

    @override
    def __init__(self, schema: JITSchemaBase) -> None:
        super().__init__(schema)
        self.default_value_setter = DictSetter
