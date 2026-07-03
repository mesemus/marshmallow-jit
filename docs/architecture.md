# marshmallow-jit Architecture

Similarly to DeepFriedMarshmallow, marshmallow-jit uses a JIT (Just-In-Time) compilation approach to optimize schema serialization.

## Overview

marshmallow-jit dynamically generates optimized Python code at runtime to serialize marshmallow schemas. The generated code is compiled and executed, replacing the default `_serialize` method with a faster, specialized implementation.

**Note**: Currently, only serialization (`dump`) is supported. Deserialization (`load`) is not implemented and will raise `NotImplementedError` if attempted.

Unlike DeepFriedMarshmallow, marshmallow-jit does not fall back to the original `_serialize` implementation for unknown field types. Instead:
- When `FAIL_ON_UNKNOWN_FIELD_TYPE` is enabled (default), it raises a `ValueError`
- Otherwise, it logs a warning and falls back to the field's native `serialize()` method


## Component Layers

### 1. Schema Layer (`marshmallow_jit/schema.py`)

**JITSchemaMixin**: A schema mixin that intercepts schema initialization via `__init__` and replaces `_serialize` with JIT-compiled versions. It can be applied via:
- The `@jit_schema` decorator on schema classes
- The `jit_schema_object()` function on schema instances

**JITSchemaOptions**: Configuration options defined in the schema's `Meta.jit_options`, including:
- `jit_maker_class`: Which JITMaker to use for code generation
- `serializer`: Which SchemaSerializer(s) to use (mapping, instance, hybrid, or custom)
- `serialization_value_accessor`: Custom value accessor for reading field values

### 2. Code Generation Layer (`marshmallow_jit/jit/`)

**JITMaker** (`maker.py`): Responsible for generating JIT-compiled serializer functions. Creates compiled methods with predicate-based dispatch when multiple serializers are configured.

**SchemaSerializer** (`serializer.py`): Generates the serialization logic for a schema. Different variants exist:
- `MappingSchemaSerializer`: Uses `DictAccessor` for dict-like objects
- `InstanceSchemaSerializer`: Uses `InstanceAccessor` for object instances
- `HybridSchemaSerializer`: Uses `HybridAccessor` for both dicts and objects

Each serializer generates Python code that iterates over schema fields and produces optimized serialization logic.

**ValueAccessor** (`accessors.py`): Defines how to read field values from the source object:
- `DictAccessor`: Uses dictionary access with try/except KeyError
- `InstanceAccessor`: Uses `getattr()` for single attributes, direct attribute chaining for dotted paths
- `HybridAccessor`: Attempts dict access first, falls back to attribute access

**Inliner** (`inliners/`): Inlines field-specific serialization transformations directly into the generated code. Each marshmallow field type has a corresponding inliner (e.g., `IntegerSerializationInliner`, `DateTimeSerializationInliner`, `NestedSerializationInliner`). The factory (`BuiltinSerializationInlinersFactory`) maps field types to their inliners, respecting inheritance hierarchies.

### 3. Registry Layer (`marshmallow_jit/jit/registry.py`)

Provides plugin-style extensibility through registries:
- `serializer_registry`: Resolves SchemaSerializer implementations
- `serialization_accessor_registry`: Resolves ValueAccessor implementations  
- `serialization_inliner_registry`: Resolves Inliner implementations
- `maker_registry`: Resolves JITMaker implementations

Supports both builtin factories and entry point plugins for third-party extensions.

### 4. Code Utilities (`marshmallow_jit/jit/python_code.py`, `context.py`)

**PythonCode**: Builds and compiles dynamic Python code. Handles variable management, indentation, imports, and execution in a controlled namespace.

**Context**: Tracks the current schema and serializer during nested serialization (e.g., for Nested fields), maintaining a stack for proper scoping.

## Key Design Decisions

1. **No deserialization support yet**: The focus is on optimizing the hot path of serialization. Deserialization would require a separate implementation.

2. **Explicit fallback behavior**: Unknown field types either error or log warnings rather than silently falling back, making issues visible during development.

3. **Predicate-based multi-serializer support**: Allows different serializers for different object types (e.g., dict vs instance) with runtime dispatch.

4. **Inlining over method calls**: Field transformations are inlined into the generated code to eliminate function call overhead.

5. **Accessor optimization**: Different access strategies are chosen based on the expected input type (dict vs object instance).

## Typing

The codebase is fully typed with Python 3.14 as the minimum supported version.
