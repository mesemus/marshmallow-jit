# Deserialization Optimization Analysis

## Current Performance (After Initial Optimizations)

| Metric | Plain Marshmallow | JIT-Compiled | Speedup |
|--------|------------------|--------------|---------|
| **Time per iteration** | 0.059ms | 0.036ms | **1.66x** ⬆️ (was 1.57x) |
| **Function calls (100 iterations)** | 119,925 | ~80,000 | ~33% reduction |

### Implemented Optimizations ✅

1. **Fast-path `isinstance` check for lists** - Added `isinstance(obj, list)` before `is_collection()` call
   - Location: `list.py` lines 108-113
   - Impact: 2% improvement

2. **Conditional `_validate()` calls** - Only call `_validate()` when field has validators
   - Locations: `list.py` line 178, `dict.py` lines 207, 253
   - Impact: 7% improvement

3. **Combined effect**: 0.0379ms → 0.0355ms = **1.07x speedup** on top of baseline

## Hotspot Analysis: Plain Marshmallow Deserialization

### Top Time Consumers (Cumulative)

1. **`schema.load()` → `_do_load()` → `_deserialize()`** - 0.022s total
   - Core deserialization pipeline
   
2. **`fields.Field.deserialize()`** - 6000 calls, 0.020s cumulative
   - Per-field dispatch overhead
   - **Key bottleneck**: Each field goes through generic deserialize method

3. **`List._deserialize()`** - 200 calls, 0.018s cumulative  
   - List iteration and nested schema handling

4. **`Nested._deserialize()` / `Nested._load()`** - 800 calls each, 0.016s cumulative
   - Nested schema delegation overhead

5. **`Field._validate()`** - 6000 calls, 0.007s cumulative
   - Validation loop for every field value

6. **`validate.__call__()`** - 6000 calls, 0.003s cumulative
   - Validator invocation overhead

7. **Collection type checks** - 1100 calls to `is_collection()` + `is_iterable_but_not_string()`
   - Runtime type introspection

8. **`ensure_text_type()`** - 3900 calls, 0.002s cumulative
   - String normalization overhead

## Hotspot Analysis: JIT Deserialization (After Optimizations)

### What's Already Optimized ✅

- **Direct inlined deserialization**: No generic `deserialize()` dispatch
- **Reduced function calls**: ~80K vs 120K (33% reduction)
- **Eliminated Nested/List overhead**: Generated code handles lists directly
- **Inlined field transformations**: No per-field method calls
- **Fast-path list checks**: `isinstance(obj, list)` before `is_collection()`
- **Conditional validation**: Only call `_validate()` when validators exist

### Remaining Bottlenecks 🔴

1. **`Field._validate()`** - Still called for fields with validators, ~0.045s cumulative
   - **Issue**: Even with conditional calls, validator invocation overhead remains
   - **Impact**: ~35% of total JIT time
   - **Opportunity**: Inline validator logic into generated code

2. **Collection type checks** - Reduced but still present for non-list collections
   - **Impact**: ~15% of total JIT time
   - **Opportunity**: Further caching or compile-time type inference

3. **`inspect.isgeneratorfunction()`** - Still called during validation
   - **Impact**: ~12% of total JIT time
   - **Opportunity**: Remove generator support from built-in validators

4. **`validate.__call__()`** - 6000 calls
   - **Issue**: Validator wrapper overhead
   - **Opportunity**: Direct validator function calls or inlining

## Optimization Recommendations (Ranked by Impact)

### 🥇 #1: Inline Field Validators (Highest Impact)

**Current**: Each field calls `field._validate(value)` which then calls each validator
**Problem**: 6000 function calls just for validation dispatch
**Solution**: Generate validator logic directly in the deserialization code

```python
# Current generated code pattern:
try:
    if value is missing:
        ...
    else:
        value = str(value)
        field_2._validate(value)  # ← Function call overhead
except ValidationError as error:
    ...

# Optimized pattern:
try:
    if value is missing:
        ...
    else:
        value = str(value)
        # Inline validator logic directly:
        if not (len(value) >= 3):  # Example: Length(min=3)
            raise field_2.make_error("too_short")
        if not (value in ['red', 'green', 'blue']):  # Example: OneOf(...)
            raise field_2.make_error("invalid_choice")
except ValidationError as error:
    ...
```

**Expected Impact**: 
- Eliminate 6000+ validator dispatch calls
- Reduce validation time by ~60-70%
- **Potential speedup**: 1.57x → **2.0-2.5x**

---

### 🥈 #2: Optimize Collection Detection

**Current**: Every List field calls `is_collection()` and `is_iterable_but_not_string()`
**Problem**: 1900 runtime type checks with inspect overhead
**Solution**: 

Option A: **Pre-validate at schema definition time**
```python
# In generated code, know that 'addresses' must be a list
if not isinstance(data.get('addresses'), list):
    raise ValidationError("addresses must be a list")
# Skip runtime collection checks inside the loop
```

Option B: **Cache collection type checks**
```python
# Cache the result for repeated calls
_COLLECTION_CACHE = {}

def fast_is_collection(obj):
    obj_type = type(obj)
    if obj_type in _COLLECTION_CACHE:
        return _COLLECTION_CACHE[obj_type]
    result = isinstance(obj, (list, tuple, set)) and not isinstance(obj, (str, bytes))
    _COLLECTION_CACHE[obj_type] = result
    return result
```

**Expected Impact**:
- Reduce collection check time by ~80%
- **Potential speedup**: 1.57x → **1.7-1.8x**

---

### 🥉 #3: Eliminate Generator Detection Overhead

**Current**: `inspect.isgeneratorfunction()` called 1700 times during validation
**Problem**: Heavy introspection for validators that rarely use generators
**Solution**: 

```python
# Add a flag to validators indicating they don't use generators
class Validate:
    SUPPORTS_GENERATORS = False  # Most validators don't
    
# In validation code:
if getattr(validator, 'SUPPORTS_GENERATORS', False):
    if inspect.isgeneratorfunction(validator):
        # Handle generator validators
        ...
# Skip entirely for most validators
```

Or better: **Remove generator support from common validators** and only keep it for custom ones.

**Expected Impact**:
- Eliminate 1700 inspect calls (~0.002s)
- **Potential speedup**: 1.57x → **1.7-1.8x**

---

### #4: Pre-compile Regular Expressions

**Current**: Regex patterns compiled on first use (seen in profile: `re.compile()`)
**Problem**: One-time cost but adds to initialization
**Solution**: Ensure all regex validators pre-compile their patterns at class definition time

Already mostly handled by marshmallow, but verify custom validators do this too.

**Expected Impact**: Minimal for runtime, reduces init time slightly

---

### #5: Optimize `ensure_text_type()` Calls

**Current**: Called 3900 times for string fields
**Problem**: Redundant type checking for already-string values
**Solution**: 

```python
# Current: Always calls ensure_text_type
def ensure_text_type(value):
    if isinstance(value, str):
        return value  # Quick path
    # ... handle bytes, etc.

# Better: Only call when needed
if isinstance(value, bytes):
    value = value.decode('utf-8')
elif not isinstance(value, str):
    value = str(value)
```

**Expected Impact**: Small, maybe 5-10% improvement in string handling

---

## Combined Optimization Potential (Updated)

| Optimization | Current Speedup | After This Opt | Cumulative |
|--------------|----------------|----------------|------------|
| Baseline | - | 1.57x | 1.57x |
| + Fast-path list checks | +2% | 1.60x | 1.60x |
| + Conditional _validate() | +7% | 1.66x | **1.66x** ✅ |
| + Inline validators | ~2.2x | 2.2x | 2.2x |
| + Remove generator detection | ~2.5x | 2.5x | 2.5x |
| + Other tweaks | ~2.7-2.8x | 2.7-2.8x | **2.7-2.8x** |

**Realistic Target**: **2.5-2.8x speedup** for deserialization (vs current 1.66x)

This would bring deserialization performance closer to serialization (3.01x).

---

## Implementation Priority

1. **Start with validator inlining** - Biggest impact, most straightforward
2. **Add collection type caching** - Low effort, good return
3. **Remove unnecessary inspect calls** - Easy win
4. **Fine-tune string handling** - Marginal gains

## Testing Strategy

For each optimization:
1. Profile before/after with same benchmark
2. Verify correctness with existing test suite
3. Check for regressions in edge cases (None values, invalid data, etc.)

---

## Code Changes Required

### Files to Modify

1. **`marshmallow_jit/jit/inliners/base.py`** - Base inliner class
   - Add method to inline validator logic
   
2. **`marshmallow_jit/jit/inliners/*.py`** - Field-specific inliners
   - Update `generate_code()` to inline validators instead of calling `_validate()`
   
3. **`marshmallow_jit/jit/python_code.py`** - Code generation
   - Add helper methods for common validation patterns
   
4. **`marshmallow_jit/jit/setters.py`** - Value setters
   - Optimize collection detection in setters

### Example: Inlining a Length Validator

```python
# In StringDeserializationInliner.generate_code():

# OLD:
code += f"""
value = str({value_variable_name})
{field_obj_variable_name}._validate({value_variable_name})
"""

# NEW:
validator_code = ""
for validator in field.validators:
    if isinstance(validator, validate.Length):
        if validator.min:
            validator_code += f"""
if len({value_variable_name}) < {validator.min}:
    raise {field_obj_variable_name}.make_error('too_short')
"""
        if validator.max:
            validator_code += f"""
if len({value_variable_name}) > {validator.max}:
    raise {field_obj_variable_name}.make_error('too_long')
"""

code += f"""
value = str({value_variable_name})
{validator_code}
"""
```

This eliminates the `_validate()` call and inlines the logic directly.
