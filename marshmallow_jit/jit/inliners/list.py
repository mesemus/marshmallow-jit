# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""List field serialization and deserialization inliners."""

from typing import TYPE_CHECKING, cast, override

from marshmallow import Schema
from marshmallow.fields import Field, List

from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode

from .base import Inliner
from .registry import deserialization_inliner_registry, serialization_inliner_registry

if TYPE_CHECKING:
    pass


class ListSerializationInliner(Inliner):
    """Serializes a List field by iterating over elements and serializing each with its inner field's inliner."""

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
        field = cast(List, field)

        # Handle None case - if the list is None, keep it as None
        with code.indent(f"if {value_variable_name} is not None"):
            # Save the original list to iterate over, then reuse the variable for the result
            iter_var = f"{value_variable_name}_iter"
            code += f"{iter_var}, {value_variable_name} = {value_variable_name}, []"

            # Use a unique item variable name based on context level to avoid conflicts in nested lists
            item_var = f"item_{context.level}"

            # Iterate over the saved list and serialize each element
            with code.indent(f"for {item_var} in {iter_var}"):
                # Nest the context to ensure unique variable names for nested lists
                with context.nest():
                    # Get the appropriate inliner for the inner field type
                    try:
                        inner_inliner = serialization_inliner_registry.find(schema, attr_name, field.inner)
                    except KeyError:
                        inner_inliner = None

                    if inner_inliner is None:
                        # Fall back to calling the inner field's _serialize method directly
                        # Since 'item' is already the value (not an object containing the value),
                        # we call _serialize directly instead of serialize()
                        inner_field_var = code.add_variable(f"{attr_name}_inner_field", field.inner)
                        # Call _serialize directly with the item as the value
                        code += f"serialized_item = {inner_field_var}._serialize({item_var}, {attr_name!r}, {item_var})"
                        with code.indent("if serialized_item is not missing"):
                            code += f"{value_variable_name}.append(serialized_item)"
                    else:
                        # Use the inner inliner for efficient serialization
                        if inner_inliner.is_noop:
                            # No transformation needed, just append
                            code += f"{value_variable_name}.append({item_var})"
                        elif inner_inliner.can_return_missing:
                            # Inliner might return missing, so we need to check
                            inner_inliner.generate_code(
                                code, item_var, field_obj_variable_name, schema, attr_name, field.inner, context
                            )
                            with code.indent(f"if {item_var} is not missing"):
                                code += f"{value_variable_name}.append({item_var})"
                        else:
                            # Inliner transforms the value but never returns missing.
                            # For non-noop inliners, we can safely reuse item_var because:
                            # 1. The loop iteration variable is already consumed (we're inside the loop body)
                            # 2. Any nested loops will use their own unique variable names (item_{level+1})
                            # So we transform in-place without needing a separate _transformed variable
                            inner_inliner.generate_code(
                                code, item_var, field_obj_variable_name, schema, attr_name, field.inner, context
                            )
                            code += f"{value_variable_name}.append({item_var})"


class ListDeserializationInliner(Inliner):
    """Deserializes a List field by iterating over elements and deserializing each with its inner field's inliner.

    Handles the same cases as marshmallow's List._deserialize:
    - Validates that the input is a collection (raises 'invalid' error if not)
    - Iterates over elements and deserializes each with the inner field
    - Collects validation errors by index and raises ValidationError with valid_data if any errors occur
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
        field = cast(List, field)

        # Add required imports for generated code
        code.add_import_line("from marshmallow.utils import is_collection")
        code.add_import_line("from marshmallow.exceptions import ValidationError")

        # First, validate that the value is a collection
        # Optimized check: fast path for list (most common case), fallback to is_collection()
        code += f"""
        if not isinstance({value_variable_name}, list):
            if not is_collection({value_variable_name}):
                raise {field_obj_variable_name}.make_error("invalid")
        """

        # Save the original list to iterate over, then reuse the variable for the result
        iter_var = f"{value_variable_name}_iter"
        code += f"{iter_var}, {value_variable_name} = {value_variable_name}, []"

        # Use a unique item variable name based on context level to avoid conflicts in nested lists
        item_var = f"item_{context.level}"
        idx_var = f"idx_{context.level}"

        # Create an errors dict to collect validation errors by index
        errors_var = f"errors_{context.level}"
        result_var = f"result_{context.level}"
        code += f"{errors_var} = {{}}"
        code += f"{result_var} = []"

        # Iterate over the saved list and deserialize each element
        with code.indent(f"for {idx_var}, {item_var} in enumerate({iter_var})"):
            # Nest the context to ensure unique variable names for nested lists
            with context.nest():
                # Get the appropriate inliner for the inner field type
                try:
                    inner_inliner = deserialization_inliner_registry.find(
                        schema, f"{attr_name}[{idx_var}]", field.inner
                    )
                except KeyError:
                    inner_inliner = None

                if inner_inliner is None:
                    # Fall back to calling the inner field's deserialize method directly
                    inner_field_var = code.add_variable(f"{attr_name}_inner_field", field.inner)
                    # Call deserialize directly - this handles validation internally
                    code += f"""
                    try:
                        deserialized_item = {inner_field_var}.deserialize({item_var}, {attr_name!r}, data)
                        {result_var}.append(deserialized_item)
                    except ValidationError as error:
                        if error.valid_data is not None:
                            {result_var}.append(error.valid_data)
                        {errors_var}[{idx_var}] = error.messages
                    """
                else:
                    # Use the inner inliner for efficient deserialization
                    if inner_inliner.is_noop:
                        # No transformation needed, just append
                        code += f"{result_var}.append({item_var})"
                    else:
                        # Get the inner field variable for error messages
                        # Sanitize the attr_name for use in variable names (replace non-alphanumeric with _)
                        safe_attr_name = "".join(
                            c if c.isalnum() or c == "_" else "_" for c in f"{attr_name}_{idx_var}"
                        )
                        inner_field_var = code.add_variable(f"{safe_attr_name}_inner_field", field.inner)

                        # Check if inner field allows None - if so, handle None values explicitly
                        if field.inner.allow_none:
                            with code.indent(f"if {item_var} is None"):
                                code += f"{result_var}.append(None)"
                            with code.indent("else"):
                                # Inliner transforms the value - wrap entire inliner + validate + append in try-except
                                with code.indent("try"):
                                    inner_inliner.generate_code(
                                        code,
                                        item_var,
                                        inner_field_var,  # Pass inner field var, not the List field
                                        schema,
                                        f"{attr_name}[{idx_var}]",
                                        field.inner,
                                        context,
                                    )
                                    # Generate validation code via the inliner
                                    inner_inliner.generate_validate(
                                        code,
                                        item_var,
                                        inner_field_var,
                                        schema,
                                        f"{attr_name}[{idx_var}]",
                                        field.inner,
                                        context,
                                    )
                                    code += f"if {item_var} is not missing:"
                                    with code.indent(""):
                                        code += f"{result_var}.append({item_var})"
                                code += f"""
                                except ValidationError as error:
                                    if error.valid_data is not None:
                                        {result_var}.append(error.valid_data)
                                    {errors_var}[{idx_var}] = error.messages
                                """
                        else:
                            # Inliner transforms the value - wrap entire inliner + validate + append in try-except
                            with code.indent("try"):
                                inner_inliner.generate_code(
                                    code,
                                    item_var,
                                    inner_field_var,  # Pass inner field var, not the List field
                                    schema,
                                    f"{attr_name}[{idx_var}]",
                                    field.inner,
                                    context,
                                )
                                # Generate validation code via the inliner
                                inner_inliner.generate_validate(
                                    code,
                                    item_var,
                                    inner_field_var,
                                    schema,
                                    f"{attr_name}[{idx_var}]",
                                    field.inner,
                                    context,
                                )
                                code += f"if {item_var} is not missing:"
                                with code.indent(""):
                                    code += f"{result_var}.append({item_var})"
                            code += f"""
                            except ValidationError as error:
                                if error.valid_data is not None:
                                    {result_var}.append(error.valid_data)
                                {errors_var}[{idx_var}] = error.messages
                            """

        # Check if there were any errors and raise ValidationError if so
        code += f"""
        if {errors_var}:
            raise ValidationError({errors_var}, valid_data={result_var})
        {value_variable_name} = {result_var}
        """
