# marshmallow-jit Project Guide

## Overview

**marshmallow-jit** is a Just-In-Time compilation library for optimizing marshmallow schema serialization (and deserialization). It dynamically generates and compiles optimized Python code at runtime to replace the default `_serialize` and `_deserialize` methods with faster, specialized implementations.

### Key Differentiators from DeepFriedMarshmallow

- Supports advanced scenarios with error propagation optimization
- Explicit fallback behavior (errors or warnings instead of silent fallbacks)
- Predicate-based multi-serializer support for different object types
- Fully typed codebase targeting Python 3.14+. We concentrate on the quality
  of type checking, using as specific types as possible
- Both serialization and deserialization JIT compilation

## Tech Stack

- **Python**: 3.14+
- **Dependencies**: marshmallow
- **Dev Tools**: uv (package management), ruff (linting/formatting), pytest (testing), ty (type checking)
- **Code Style**: 120 char line length, double quotes, space indentation

## Project Structure

```
marshmallow-jit/
├── marshmallow_jit/           # Main library package
│   ├── __init__.py
│   ├── config.py              # Configuration constants
│   ├── log.py                 # Logging setup
│   ├── schema.py              # JITSchemaMixin, decorators, options
│   ├── utils.py               # Utility functions
│   └── jit/                   # Code generation layer
│       ├── __init__.py
│       ├── accessors.py       # ValueAccessor implementations
│       ├── context.py         # Context tracking for nested schemas
│       ├── maker.py           # JITMaker - generates compiled functions
│       ├── python_code.py     # Dynamic code building and compilation
│       ├── registry.py        # Plugin registries for extensibility
│       ├── serializer.py      # SchemaSerializer implementations
│       ├── setters.py         # ValueSetter for deserialization
│       └── inliners/          # Field-specific serialization inliners
│           ├── __init__.py
│           ├── base.py
│           ├── factories.py
│           └── [field_type]_inliner.py
├── tests/                     # Test suite
│   ├── conftest.py            # Shared fixtures and test schemas
│   ├── test_serialization.py
│   ├── accessors/
│   ├── deserialization/
│   ├── inliners/
│   └── serialization/
├── docs/                      # Documentation
│   ├── architecture.md
│   ├── inliners.md            # Complete inliner reference
│   ├── deserialization_performance_suggestions.md
│   └── generated_code_report.md
├── performance/               # Performance benchmarks
├── pyproject.toml             # Project configuration
└── README.md
```

## Core Architecture

### Layer 1: Schema Layer (`marshmallow_jit/schema.py`)

**JITSchemaMixin**: Intercept schema initialization and replace `_serialize`/`_deserialize` with JIT-compiled versions.

**Application Methods**:
- `@jit_schema(schema_class)` - Decorator for schema classes
- `jit_schema_object(schema_instance)` - Function for schema instances

**JITSchemaOptions**: Configure via `Meta.jit_options`:
```python
class MySchema(Schema):
    class Meta:
        jit_options = {
            "jit_maker_class": "default",
            "serializer": "mapping",  # or "instance", "hybrid", or custom
            "deserializer": "mapping",
            "serialization_value_accessor": "dict",
            "deserialization_value_setter": MyValueSetter,
        }
```

### Layer 2: Code Generation Layer (`marshmallow_jit/jit/`)

**JITMaker** (`maker.py`): Generates compiled serializer/deserializer functions with predicate-based dispatch when multiple serializers configured.

**SchemaSerializer** (`serializer.py`):
- `MappingSchemaSerializer` - Dict-like objects via `DictAccessor`
- `InstanceSchemaSerializer` - Object instances via `InstanceAccessor`
- `HybridSchemaSerializer` - Both dicts and objects via `HybridAccessor`

**ValueAccessor** (`accessors.py`): How to read field values
- `DictAccessor` - Dictionary access with try/except KeyError
- `InstanceAccessor` - `getattr()` for attributes, direct chaining for dotted paths
- `HybridAccessor` - Dict first, falls back to attribute access

**ValueSetter** (`setters.py`): How to set values during deserialization
- `DictSetter` - Set dictionary keys
- `ObjectSetter` - Set object attributes

**Inliners** (`inliners/`): Field-specific transformations inlined into generated code
- 28+ serialization inliners (Integer, String, DateTime, Nested, List, Dict, etc.)
- 29+ deserialization inliners (same coverage + validation logic)
- Factory pattern with inheritance-aware resolution

### Layer 3: Registry Layer (`marshmallow_jit/jit/registry.py`)

Plugin-style extensibility:
- `serializer_registry` - SchemaSerializer implementations
- `deserializer_registry` - SchemaDeserializer implementations
- `serialization_accessor_registry` - ValueAccessor implementations
- `deserialization_accessor_registry` - ValueSetter implementations
- `serialization_inliner_registry` - Serialization inliners
- `deserialization_inliner_registry` - Deserialization inliners
- `maker_registry` - JITMaker implementations

Supports builtin factories and entry point plugins.

### Layer 4: Code Utilities

**PythonCode** (`python_code.py`): Builds and compiles dynamic Python code with variable management, indentation, imports, and controlled execution namespaces.

**Context** (`context.py`): Tracks current schema and serializer during nested serialization, maintaining a stack for proper scoping.

## Usage Patterns

### Basic Usage

```python
from marshmallow import Schema, fields
from marshmallow_jit.schema import jit_schema, JITSchemaMixin

@jit_schema
class UserSchema(Schema):
    name = fields.Str()
    age = fields.Int()

schema = UserSchema()
result = schema.dump({"name": "Alice", "age": 30})
# JIT-compiled, significantly faster than standard marshmallow
```

### With Custom Options

```python
@jit_schema
class UserSchema(Schema):
    class Meta:
        jit_options = {
            "serializer": "instance",  # Optimize for object instances
            "serialization_value_accessor": "hybrid",
        }
    
    name = fields.Str()
    email = fields.Email()
```

### Multi-Serializer Support

```python
from typing import Any

def is_dict(obj: Any) -> bool:
    return isinstance(obj, dict)

def is_dataclass(obj: Any) -> bool:
    return hasattr(obj, '__dataclass_fields__')

@jit_schema
class FlexibleSchema(Schema):
    class Meta:
        jit_options = {
            "serializer": [
                (is_dict, "mapping"),
                (is_dataclass, "instance"),
            ]
        }
    
    field1 = fields.Str()
```

## Development Workflow

### Environment Setup

```bash
# Install dependencies with uv (marshmallow 3.x with utils)
uv sync --group dev --group marshmallow3

# Or for marshmallow 4.x (no utils compatibility yet)
uv sync --group dev --group marshmallow4

# Activate virtual environment
source .venv/bin/activate
```

**Note**: The project supports both marshmallow 3.x and 4.x via compatibility layer in `marshmallow_jit/compat.py`. Marshmallow 3.x is recommended as it has full support including marshmallow-utils fields.

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_serialization.py

# Run with coverage
pytest --cov=marshmallow_jit

# Run specific test category
pytest tests/serialization/
```

### Code Quality

```bash
# Lint and format
ruff check marshmallow_jit tests
ruff format marshmallow_jit tests

# Fix auto-fixable issues
ruff check --fix marshmallow_jit tests

# Type checking
ty check marshmallow_jit tests
```

### Imports

Use relative imports if the imported thing is within the same module
or submodule. Never use relative imports for parent packages (from ..b import)

### Viewing Generated Code

To inspect the dynamically generated Python code:

```bash
# View serialized JIT code
python docs/generated_code/dump_jit.py
```

### Running Performance Benchmarks

```bash
# Run serialization performance benchmarks
python performance/serialization_speed.py

# Run profiling scripts
python profiling/profile_hotspots.py benchmark
python profiling/profile_hotspots.py profile_serialization
python profiling/profile_hotspots.py profile_deserialization
```

### Profiling Tools Installation

```bash
# Add profiling tools to dev environment
uv add --group dev line_profiler scalene

# For memory profiling (optional)
uv add --group dev memray
```

### Adding New Field Inliners

1. Create inliner class in `marshmallow_jit/jit/inliners/`:
```python
from marshmallow_jit.jit.inliners.base import SerializationInliner

class MyCustomFieldSerializationInliner(SerializationInliner):
    def generate_serialize_method_content(self, code, context):
        # Generate Python code for this field type
        code.add_line(f"result['{self.field_name}'] = self._serialize_{self.field_name}(obj)")
```

2. Register in factory (`factories.py`):
```python
serialization_inliner_registry.add_factory(
    BuiltinSerializationInlinerFactory({MyCustomField: MyCustomFieldSerializationInliner})
)
```

### Extending Registries

Create custom factories implementing the `Factory` protocol and register them:

```python
from marshmallow_jit.jit.registry import Factory, serializer_registry

class MySerializerFactory(Factory[...]):
    def find(self, ...) -> ...:
        # Return custom implementation or None
    
    def find_by_name(self, name, ...) -> ...:
        # Resolve by name

serializer_registry.add_factory(MySerializerFactory())
```

## Key Design Decisions

1. **No Silent Fallbacks**: Unknown field types either raise `ValueError` (default) or log warnings, making issues visible during development.

2. **Inlining Over Method Calls**: Field transformations are inlined to eliminate function call overhead.

3. **Predicate-Based Dispatch**: Multiple serializers can be configured with runtime predicate-based selection.

4. **Accessor Optimization**: Different strategies for dict vs object instance access patterns.

5. **Full Type Coverage**: All common marshmallow field types have dedicated inliners with proper validation logic.

6. **Separation of Concerns**: Accessors (read), Setters (write), and Inliners (transform) are independent and composable.

## Testing Strategy

### Test Organization

- `tests/serialization/` - Serialization-specific tests
- `tests/deserialization/` - Deserialization-specific tests
- `tests/accessors/` - Value accessor tests
- `tests/inliners/` - Individual inliner tests
- `tests/conftest.py` - Shared fixtures with extensive test schemas

### Field Matrix Testing

The `conftest.py` defines comprehensive test matrices covering:
- All field types with various configurations
- Edge cases (None values, required fields, many=True)
- Custom field subclasses
- Integration with marshmallow-utils fields

### Example Test Pattern

```python
def test_field_serialization(field_type, value, expected):
    schema = MySchema()
    result = schema.dump({"field": value})
    assert result["field"] == expected
```

## Performance Optimization Toolbox

### Current Performance Baseline (After Optimizations)

| Operation | Plain Marshmallow | JIT-Compiled | Speedup |
|-----------|------------------|--------------|---------|
| **Serialization** | 0.019ms/op | 0.006ms/op | **3.06x** |
| **Deserialization** | 0.059ms/op | 0.024ms/op | **2.51x** |

*Measured with 500K iterations on complex nested schema (10 top-level fields + 8 nested items)*

### Implemented Optimizations ✅

#### 1. Fast-Path Type Checks for Collections
**Location**: `marshmallow_jit/jit/inliners/list.py` (lines 108-113)
```python
# Before: Always call is_collection()
if not is_collection(value):
    raise field.make_error("invalid")

# After: Fast isinstance check first
if not isinstance(value, list):
    if not is_collection(value):  # Fallback for edge cases
        raise field.make_error("invalid")
```
**Impact**: 2% improvement in deserialization

#### 2. Conditional `_validate()` Calls (Compile-Time Check)
**Locations**: 
- `list.py` lines 177-182
- `dict.py` lines 206-210, 264-268
- `serializer.py` lines 285-299, 304-327

**Logic**: Only generate `_validate()` call when:
- `_validate` method is overridden (custom validation logic), OR
- `_validate_all` property is overridden, OR
- Field has validators defined (`field.validators` list is non-empty)

**Implementation**:
```python
from marshmallow.fields import Field as MarshmallowField
from marshmallow_jit.utils import is_overridden, is_property_overridden

has_custom_validate = is_overridden(field._validate, MarshmallowField._validate)
has_custom_validate_all = is_property_overridden(field, '_validate_all', MarshmallowField)
has_validators = bool(field.validators)

if has_custom_validate or has_custom_validate_all or has_validators:
    code += f"{field_var}._validate(value)"
```
**Impact**: 40% improvement (1.66x → 2.28x)

#### 3. Optimized `partial` Parameter Check
**Location**: `marshmallow_jit/jit/inliners/nested.py` (lines 179-189)
```python
# Before: Always call is_collection(partial)
partial_is_collection = marshmallow.utils.is_collection(partial)

# After: Fast path for common cases (True/False/None/list/tuple/set)
if partial is True or partial is False or partial is None:
    partial_is_collection = False
    nested_partial = partial
elif isinstance(partial, (list, tuple, set)):
    partial_is_collection = True
    # Compute nested partial...
else:
    # Fallback for edge cases (querysets, etc.)
    partial_is_collection = marshmallow.utils.is_collection(partial)
    # ... rest of logic
```
**Impact**: 10% improvement (2.28x → 2.51x)

#### 4. Utility Functions Added
**File**: `marshmallow_jit/utils.py`
```python
def is_property_overridden(instance: Any, prop_name: str, base_class: type) -> bool:
    """Check if a property getter has been overridden in the instance's class."""
    if prop_name not in type(instance).__dict__:
        return False
    
    instance_prop = type(instance).__dict__[prop_name]
    base_prop = base_class.__dict__.get(prop_name)
    
    if isinstance(instance_prop, property) and isinstance(base_prop, property):
        return instance_prop.fget is not base_prop.fget
    
    return True
```

### Remaining Bottlenecks & Future Optimizations

#### Priority #1: Inline Validator Logic (Highest Impact)
**Current**: 100K calls to `_validate()` per 10K iterations (22% of runtime)
**Problem**: Even with conditional checks, validator framework overhead remains
**Solution**: Generate validator logic directly instead of calling `_validate()`
```python
# Instead of: field._validate(value)
# Generate inline checks:
if len(value) < min_len:
    raise field.make_error("too_short")
if value not in choices:
    raise field.make_error("invalid_choice")
```
**Expected Impact**: 2.51x → **3.5-4.0x**

#### Priority #2: Further Optimize Collection Checks
**Current**: 90K calls to `is_collection()` per 10K iterations (17% of runtime)
**Problem**: Still called for List field validation on every iteration
**Solution**: 
- Pre-compute expected types at schema definition time
- Use tighter type checks (`type(obj) is list` vs `isinstance`)
- Cache collection type checks per-field
**Expected Impact**: Additional 10-15% improvement

#### Priority #3: Eliminate Generator Detection Overhead
**Current**: `inspect.isgeneratorfunction()` still called for non-list collections
**Problem**: Heavy introspection even when generators aren't used
**Solution**: Add `SUPPORTS_GENERATORS = False` flag to built-in validators
**Expected Impact**: Minor (already reduced by 47%)

### Profiling Commands

```bash
# Quick benchmark
python profiling/profile_hotspots.py benchmark

# Detailed cProfile analysis
python -m cProfile -o output.prof profiling/profile_hotspots.py
python -m snakeviz output.prof

# Line-by-line profiling (requires line_profiler)
kernprof -l -v profiling/profile_hotspots.py

# Scalene (CPU + memory)
python -m scalene profiling/profile_hotspots.py
```

### Key Insights

1. **Schema instance reuse is critical**: Compilation happens once per instance, not per class
2. **Most validators are no-ops**: ~80% of fields have no custom validators
3. **Type introspection is expensive**: `inspect.isgeneratorfunction()` accounts for ~30% of overhead
4. **Common case optimization wins**: Fast paths for `list`, `True`, `False`, `None` eliminate most overhead
5. **Compile-time checks beat runtime**: Moving validation decisions to code generation phase eliminates function call overhead

### Debugging Tips

```python
# View generated JIT code
schema = MyJITSchema()
print(schema._deserialize.__source__)  # For deserialization
print(schema._serialize.__source__)    # For serialization

# Trace specific function calls
import sys
original_func = some_module.some_function
def traced(*args, **kwargs):
    print(f"Called with: {args}")
    return original_func(*args, **kwargs)
some_module.some_function = traced
```

---
## Common Pitfalls

1. **Schema Reuse**: JIT compilation happens on first `__init__`. Reusing schema instances maximizes benefit.

2. **Dynamic Fields**: Fields added after schema initialization won't be included in JIT-compiled code.

3. **Custom Field Types**: Must register custom inliners or configure fallback behavior explicitly.

4. **Nested Schemas**: Each nested schema gets its own JIT compilation; ensure nested schemas also use `@jit_schema`.

## Related Documentation

- `docs/architecture.md` - Detailed component architecture
- `docs/inliners.md` - Complete inliner reference table
- `README.md` - Project overview and motivation
