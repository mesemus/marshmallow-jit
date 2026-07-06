# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Dict field serialization and deserialization inliners."""

from typing import TYPE_CHECKING, cast, override

from marshmallow import Schema
from marshmallow.fields import Dict as DictField

from marshmallow_jit.compat import MAField as Field
from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode

from .base import Inliner
from .registry import deserialization_inliner_registry, serialization_inliner_registry

if TYPE_CHECKING:
    pass


class DictSerializationInliner(Inliner):
    """Serializes a Dict field by iterating over items and serializing keys/values."""

    @override
    def generate_code(
        self,
        code: PythonCode,
        value_variable_name: str,
        field_obj_variable_name: str,
        schema: Schema,
        attr_name: str,
        field: Field,
        context: Context,
    ) -> None:
        field = cast(DictField, field)

        # Handle None case - if the dict is None, keep it as None
        with code.indent(f"if {value_variable_name} is not None"):
            # Special case: no key_field and no value_field - just convert to dict
            # This matches marshmallow's behavior: self.mapping_type(value)
            if field.key_field is None and field.value_field is None:
                field_var = code.add_variable(field_obj_variable_name, field)
                code += f"{value_variable_name} = {field_var}.mapping_type({value_variable_name})"
            else:
                # Marshmallow's Dict serialization has two phases:
                # 1. Serialize keys by iterating: for k in value
                # 2. Serialize values by iterating: for k, v in value.items()
                # This matches marshmallow's error behavior when value is not a proper mapping

                iter_var = f"{value_variable_name}_iter"
                code += f"{iter_var} = {value_variable_name}"

                # Use unique variable names based on context level
                key_var = f"key_{context.level}"
                val_var = f"value_{context.level}"

                # Phase 1: Serialize keys if key_field is defined
                # Build a keys dict: {original_key: serialized_key}
                if field.key_field is not None:
                    keys_dict_var = f"{value_variable_name}_keys"
                    code += f"{keys_dict_var} = {{}}"

                    with code.indent(f"for {key_var} in {iter_var}"):
                        try:
                            key_inliner = serialization_inliner_registry.find(
                                schema, f"{attr_name}_key", field.key_field
                            )
                        except KeyError:
                            key_inliner = None

                        # Serialize the key
                        serialized_key_var = f"{key_var}_serialized"
                        if key_inliner is None:
                            # Fall back to calling _serialize directly
                            key_field_var = code.add_variable(f"{attr_name}_key_field", field.key_field)
                            code += f"{serialized_key_var} = {key_field_var}._serialize({key_var}, None, None)"
                        elif key_inliner.is_noop:
                            # No transformation needed
                            code += f"{serialized_key_var} = {key_var}"
                        else:
                            # Use inliner to transform the key
                            code += f"{serialized_key_var} = {key_var}"
                            with context.nest():
                                key_inliner.generate_code(
                                    code,
                                    serialized_key_var,
                                    field_obj_variable_name,
                                    schema,
                                    f"{attr_name}_key",
                                    field.key_field,
                                    context,
                                )

                        # Store mapping: original_key -> serialized_key
                        code += f"{keys_dict_var}[{key_var}] = {serialized_key_var}"

                # Phase 2: Iterate over items and serialize values
                code += f"{value_variable_name} = {{}}"
                with code.indent(f"for {key_var}, {val_var} in {iter_var}.items()"):
                    # Get the serialized key (or use original if no key_field)
                    if field.key_field is not None:
                        # Check if key is in keys dict (it should be if phase 1 succeeded)
                        with code.indent(f"if {key_var} in {keys_dict_var}"):
                            final_key_var = f"{key_var}_final"
                            code += f"{final_key_var} = {keys_dict_var}[{key_var}]"

                            # Now serialize the value
                            self._serialize_dict_value(
                                code,
                                context,
                                schema,
                                attr_name,
                                field,
                                value_variable_name,
                                final_key_var,
                                val_var,
                                field_obj_variable_name,
                            )
                    else:
                        # No key transformation, use key as-is
                        self._serialize_dict_value(
                            code,
                            context,
                            schema,
                            attr_name,
                            field,
                            value_variable_name,
                            key_var,
                            val_var,
                            field_obj_variable_name,
                        )

    def _serialize_dict_value(
        self,
        code: PythonCode,
        context: Context,
        schema: Schema,
        attr_name: str,
        field: DictField,
        result_var: str,
        key_var: str,
        val_var: str,
        field_obj_variable_name: str,
    ) -> None:
        """Helper to serialize a dict value and add it to the result."""
        # Process value if value_field is defined
        if field.value_field is not None:
            try:
                value_inliner = serialization_inliner_registry.find(schema, f"{attr_name}_value", field.value_field)
            except KeyError:
                value_inliner = None

            if value_inliner is None:
                # Fall back to calling _serialize directly
                value_field_var = code.add_variable(f"{attr_name}_value_field", field.value_field)
                code += f"{val_var} = {value_field_var}._serialize({val_var}, {attr_name!r}, {val_var})"
                code += f"{result_var}[{key_var}] = {val_var}"
            elif value_inliner.can_return_missing:
                # Value might become missing after transformation
                # Nest context for value processing
                with context.nest():
                    value_inliner.generate_code(
                        code,
                        val_var,
                        field_obj_variable_name,
                        schema,
                        f"{attr_name}_value",
                        field.value_field,
                        context,
                    )
                with code.indent(f"if {val_var} is not missing"):
                    code += f"{result_var}[{key_var}] = {val_var}"
            else:
                # Value transforms but never returns missing
                if not value_inliner.is_noop:
                    # Nest context for value processing
                    with context.nest():
                        value_inliner.generate_code(
                            code,
                            val_var,
                            field_obj_variable_name,
                            schema,
                            f"{attr_name}_value",
                            field.value_field,
                            context,
                        )
                code += f"{result_var}[{key_var}] = {val_var}"
        else:
            # No value_field, just copy the value
            code += f"{result_var}[{key_var}] = {val_var}"


class DictDeserializationInliner(Inliner):
    """Deserializes a Dict field by iterating over items and deserializing keys/values.

    Handles the same cases as marshmallow's Mapping._deserialize:
    - Validates that the input is a Mapping (raises 'invalid' error if not)
    - Deserializes keys using key_field's inliner (if defined)
    - Deserializes values using value_field's inliner (if defined)
    - Collects validation errors by key and raises ValidationError with valid_data if any errors occur
    """

    @override
    def generate_code(
        self,
        code: PythonCode,
        value_variable_name: str,
        field_obj_variable_name: str,
        schema: Schema,
        attr_name: str,
        field: Field,
        context: Context,
    ) -> None:
        field = cast(DictField, field)

        # Add required imports for generated code
        code.add_import_line("from collections.abc import Mapping")
        code.add_import_line("from marshmallow.exceptions import ValidationError")

        # First, validate that the value is a Mapping
        code += f"""
        if not isinstance({value_variable_name}, Mapping):
            raise {field_obj_variable_name}.make_error("invalid")
        """

        # If no key_field and no value_field, just return the dict as-is
        if field.key_field is None and field.value_field is None:
            # No transformation needed, just convert to the mapping type (dict for Dict field)
            code += f"{value_variable_name} = dict({value_variable_name})"
            return

        # Create result dict and errors dict
        result_var = f"result_{context.level}"
        errors_var = f"errors_{context.level}"
        code += f"{result_var} = {{}}"
        code += f"{errors_var} = {{}}"

        # Use unique variable names based on context level
        key_var = f"key_{context.level}"
        val_var = f"val_{context.level}"

        # Iterate over dict items
        with code.indent(f"for {key_var}, {val_var} in {value_variable_name}.items()"):
            # Nest the context to ensure unique variable names for nested structures
            with context.nest():
                # Track whether key deserialization succeeded
                key_success_var = f"key_success_{context.level}"
                code += f"{key_success_var} = True"

                # Process key if key_field is defined
                deser_key_var = key_var  # Default: use key as-is
                if field.key_field is not None:
                    try:
                        key_inliner = deserialization_inliner_registry.find(schema, f"{attr_name}_key", field.key_field)
                    except KeyError:
                        key_inliner = None

                    if key_inliner is None:
                        # Fall back to calling the key field's deserialize method directly
                        key_field_var = code.add_variable(f"{attr_name}_key_field", field.key_field)
                        code += f"""
                        try:
                            {deser_key_var} = {key_field_var}.deserialize({key_var}, {attr_name!r}, data)
                        except ValidationError as error:
                            {errors_var}[{key_var}] = {{"key": error.messages}}
                            {key_success_var} = False
                        """
                    else:
                        # Use the key inliner for efficient deserialization
                        # Sanitize the attr_name for use in variable names
                        safe_attr_name = "".join(c if c.isalnum() or c == "_" else "_" for c in f"{attr_name}_key")
                        key_field_var = code.add_variable(f"{safe_attr_name}_key_field", field.key_field)
                        with code.indent("try"):
                            key_inliner.generate_code(
                                code,
                                key_var,
                                key_field_var,
                                schema,
                                f"{attr_name}_key",
                                field.key_field,
                                context,
                            )
                            # Generate validation code via the inliner
                            key_inliner.generate_validate(
                                code,
                                key_var,
                                key_field_var,
                                schema,
                                f"{attr_name}_key",
                                field.key_field,
                                context,
                            )
                            code += f"{deser_key_var} = {key_var}"
                        code += f"""
                        except ValidationError as error:
                            {errors_var}[{key_var}] = {{"key": error.messages}}
                            {key_success_var} = False
                        """

                # Process value if value_field is defined
                deser_val_var = val_var  # Default: use value as-is
                if field.value_field is not None:
                    try:
                        value_inliner = deserialization_inliner_registry.find(
                            schema, f"{attr_name}_value", field.value_field
                        )
                    except KeyError:
                        value_inliner = None

                    if value_inliner is None:
                        # Fall back to calling the value field's deserialize method directly
                        value_field_var = code.add_variable(f"{attr_name}_value_field", field.value_field)
                        code += f"""
                        try:
                            {deser_val_var} = {value_field_var}.deserialize({val_var}, {attr_name!r}, data)
                        except ValidationError as error:
                            # Only record value error if key deserialization succeeded
                            if {key_success_var}:
                                {errors_var}.setdefault({deser_key_var}, {{}})["value"] = error.messages
                        """
                    else:
                        # Use the value inliner for efficient deserialization
                        # Sanitize the attr_name for use in variable names
                        safe_attr_name = "".join(c if c.isalnum() or c == "_" else "_" for c in f"{attr_name}_value")
                        value_field_var = code.add_variable(f"{safe_attr_name}_value_field", field.value_field)
                        with code.indent("try"):
                            # Check if the value is None and the field allows None
                            # This mimics marshmallow's Field.deserialize() check before _deserialize
                            if field.value_field.allow_none:
                                with code.indent(f"if {val_var} is None"):
                                    code += f"{deser_val_var} = None"
                                with code.indent("else"):
                                    value_inliner.generate_code(
                                        code,
                                        val_var,
                                        value_field_var,
                                        schema,
                                        f"{attr_name}_value",
                                        field.value_field,
                                        context,
                                    )
                                    # Generate validation code via the inliner
                                    value_inliner.generate_validate(
                                        code,
                                        val_var,
                                        value_field_var,
                                        schema,
                                        f"{attr_name}_value",
                                        field.value_field,
                                        context,
                                    )
                                    code += f"{deser_val_var} = {val_var}"
                            else:
                                value_inliner.generate_code(
                                    code,
                                    val_var,
                                    value_field_var,
                                    schema,
                                    f"{attr_name}_value",
                                    field.value_field,
                                    context,
                                )
                                # Generate validation code via the inliner
                                value_inliner.generate_validate(
                                    code,
                                    val_var,
                                    value_field_var,
                                    schema,
                                    f"{attr_name}_value",
                                    field.value_field,
                                    context,
                                )
                                code += f"{deser_val_var} = {val_var}"
                        code += f"""
                        except ValidationError as error:
                            # Only record value error if key deserialization succeeded
                            if {key_success_var}:
                                {errors_var}.setdefault({deser_key_var}, {{}})["value"] = error.messages
                        """

                # If key deserialization succeeded, add to result
                with code.indent(f"if {key_success_var}"):
                    code += f"{result_var}[{deser_key_var}] = {deser_val_var}"

        # Check if there were any errors and raise ValidationError if so
        code += f"""
        if {errors_var}:
            raise ValidationError({errors_var}, valid_data={result_var})
        {value_variable_name} = {result_var}
        """
