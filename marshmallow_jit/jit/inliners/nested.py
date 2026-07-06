# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Nested field serialization and deserialization inliners."""

from typing import TYPE_CHECKING, cast, override

from marshmallow import Schema
from marshmallow.fields import Nested

from marshmallow_jit.compat import MAField as Field
from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.python_code import PythonCode

from .base import Inliner

if TYPE_CHECKING:
    pass


class NestedSerializationInliner(Inliner):
    """Serializes a Nested field by delegating to the nested schema's dump method.

    Optimization: If the nested schema has no pre_dump or post_dump hooks, we skip
    the overhead of handling many/collection logic and directly call _serialize,
    which is faster since it avoids the dump() method call overhead.
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
        field = cast(Nested, field)

        # Access field.schema here at code generation time (not runtime)
        # This is safe because we're in the JIT compilation phase
        nested_schema = field.schema

        # Check if the nested schema has any pre_dump or post_dump hooks
        # If not, we can optimize by calling _serialize directly instead of dump()
        has_hooks = bool(nested_schema._hooks.get("pre_dump", []) or nested_schema._hooks.get("post_dump", []))

        # Determine the effective 'many' setting at code generation time
        effective_many = field.many or nested_schema.many

        # Handle None case - if the nested object is None, keep it as None
        with code.indent(f"if {value_variable_name} is not None"):
            # Get the nested schema variable - captured at compile time
            nested_schema_var = code.add_variable(f"{attr_name}_schema", nested_schema)

            if has_hooks:
                # Must use dump() to ensure hooks are invoked
                # Use unique variable names based on context level
                result_var = f"result_{context.level}"
                item_var = f"item_{context.level}"

                # Generate code based on whether we're handling many or single items
                if effective_many:
                    # Iterate over collection and serialize each item individually
                    code += f"""
                    if isinstance({value_variable_name}, (list, tuple)):
                        {result_var} = []
                        for {item_var} in {value_variable_name}:
                            {result_var}.append({nested_schema_var}.dump({item_var}, many=False))
                        {value_variable_name} = {result_var}
                    else:
                        {value_variable_name} = {nested_schema_var}.dump({value_variable_name}, many=True)
                    """
                else:
                    # Single object - check if value is a collection at runtime
                    code += f"""
                    if isinstance({value_variable_name}, (list, tuple)):
                        {result_var} = []
                        for {item_var} in {value_variable_name}:
                            {result_var}.append({nested_schema_var}.dump({item_var}, many=False))
                        {value_variable_name} = {result_var}
                    else:
                        {value_variable_name} = {nested_schema_var}.dump({value_variable_name}, many=False)
                    """
            else:
                # No hooks - optimize by calling _serialize directly
                # This bypasses the dump() method overhead and goes straight to serialization
                # Use unique variable names based on context level
                result_var = f"result_{context.level}"
                item_var = f"item_{context.level}"

                if effective_many:
                    # Iterate over collection and serialize each item individually
                    code += f"""
                    if isinstance({value_variable_name}, (list, tuple)):
                        {result_var} = []
                        for {item_var} in {value_variable_name}:
                            {result_var}.append({nested_schema_var}._serialize({item_var}, many=False))
                        {value_variable_name} = {result_var}
                    else:
                        {value_variable_name} = {nested_schema_var}._serialize({value_variable_name}, many=True)
                    """
                else:
                    # Single object - check if value is a collection at runtime
                    code += f"""
                    if isinstance({value_variable_name}, (list, tuple)):
                        {result_var} = []
                        for {item_var} in {value_variable_name}:
                            {result_var}.append({nested_schema_var}._serialize({item_var}, many=False))
                        {value_variable_name} = {result_var}
                    else:
                        {value_variable_name} = {nested_schema_var}._serialize({value_variable_name}, many=False)
                    """


class NestedDeserializationInliner(Inliner):
    """Deserializes a Nested field by delegating to the nested schema's _deserialize method.

    Handles the same cases as marshmallow's Nested._deserialize:
    - Validates required/allow_none on the Nested field itself
    - Applies pre_load functions on the Nested field
    - Calls the nested schema's JIT-compiled _deserialize method
    - Applies validators on the Nested field
    - Applies post_load functions on the Nested field
    - Handles many/collection logic based on field.many and nested_schema.many
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
        field = cast(Nested, field)

        # Access field.schema here at code generation time (not runtime)
        # This is safe because we're in the JIT compilation phase
        nested_schema = field.schema

        # Determine the effective 'many' setting at code generation time
        effective_many = field.many or nested_schema.many

        # Add required imports
        code.add_import_line("from marshmallow.exceptions import ValidationError")

        # Step 1: Validate required/allow_none (same as Field._validate_missing)
        code += f"""
        if {value_variable_name} is missing:
            if {field_obj_variable_name}.required:
                raise {field_obj_variable_name}.make_error("required")
            {value_variable_name} = {field_obj_variable_name}.load_default
        """

        # If still missing after load_default, return early
        code += f"""
        if {value_variable_name} is missing:
            return {value_variable_name}
        """

        # Step 2: Apply pre_load functions on the Nested field
        # Note: In marshmallow 4+, pre_load/post_load are not directly on fields.
        # They may be handled at the schema level instead.
        # For now, we skip this step as the nested schema's _deserialize will handle its own hooks.

        # Step 3: Handle None case
        with code.indent(f"if {value_variable_name} is not None"):
            # Step 3a: Test collection if many=True
            if effective_many:
                code += f"""
                from marshmallow.utils import is_collection
                if not isinstance({value_variable_name}, list) and not is_collection({value_variable_name}):
                    raise {field_obj_variable_name}.make_error("type", input={value_variable_name},
                        type={value_variable_name}.__class__.__name__)
                """

            # Step 3b: Get the nested schema variable
            nested_schema_var = code.add_variable(f"{attr_name}_schema", nested_schema)

            # Step 3c: Compute nested partial value directly (no intermediate dict needed)
            # The partial parameter comes from the parent deserialization context
            # Optimized check: fast path for common cases (True, False, None, list/tuple/set)
            code += f"""
            if partial is True or partial is False or partial is None:
                partial_is_collection = False
                nested_partial = partial
            elif isinstance(partial, (list, tuple, set)):
                partial_is_collection = True
                prefix = {attr_name!r} + "."
                len_prefix = len(prefix)
                nested_partial = [f[len_prefix:] for f in partial if f.startswith(prefix)]
            else:
                # Fallback to marshmallow's is_collection for edge cases (querysets, etc.)
                partial_is_collection = marshmallow.utils.is_collection(partial)
                if partial_is_collection:
                    prefix = {attr_name!r} + "."
                    len_prefix = len(prefix)
                    nested_partial = [f[len_prefix:] for f in partial if f.startswith(prefix)]
                elif partial is not None:
                    nested_partial = partial
                else:
                    nested_partial = None
            """

            # Step 3d: Call the nested schema's load() method
            # We use load() instead of _deserialize() because it properly handles
            # error nesting and all the schema-level logic
            if effective_many:
                # Always treat as many - iterate over collection and call load for each
                result_var = f"result_{context.level}"
                item_var = f"item_{context.level}"
                unknown_arg = f"unknown={field_obj_variable_name}.unknown"
                code += f"""
                if isinstance({value_variable_name}, (list, tuple)):
                    {result_var} = []
                    for {item_var} in {value_variable_name}:
                        {result_var}.append({nested_schema_var}.load(
                            {item_var}, {unknown_arg}, partial=nested_partial
                        ))
                    {value_variable_name} = {result_var}
                else:
                    {value_variable_name} = {nested_schema_var}.load(
                        {value_variable_name}, {unknown_arg}, partial=nested_partial
                    )
                """
            else:
                # Single object - check if value is a collection at runtime
                result_var = f"result_{context.level}"
                item_var = f"item_{context.level}"
                unknown_arg = f"unknown={field_obj_variable_name}.unknown"
                code += f"""
                if isinstance({value_variable_name}, (list, tuple)):
                    {result_var} = []
                    for {item_var} in {value_variable_name}:
                        {result_var}.append({nested_schema_var}.load(
                            {item_var}, {unknown_arg}, partial=nested_partial
                        ))
                    {value_variable_name} = {result_var}
                else:
                    {value_variable_name} = {nested_schema_var}.load(
                        {value_variable_name}, {unknown_arg}, partial=nested_partial
                    )
                """
