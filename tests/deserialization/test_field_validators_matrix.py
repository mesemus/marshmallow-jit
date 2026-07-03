# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT

"""Matrix test: fields with validators (validate= attribute) should behave identically
between JIT-compiled and plain marshmallow schemas.

This tests various built-in validators like:
- Length() for string length constraints
- Range() for numerical ranges
- OneOf() for allowed values
- Regexp() for pattern matching
- And() / Or() for combining validators
"""

import decimal
from collections.abc import Callable

import pytest
from marshmallow import Schema, ValidationError, validate
from marshmallow.fields import Decimal, Dict, Field, Float, Integer, List, Str

from marshmallow_jit.schema import JITSchemaMixin


def build_schemas_with_validator(field_factory: Callable[[], Field]) -> tuple[type[Schema], type[Schema]]:
    """Build plain and JIT schemas with the given field factory."""

    class PlainSchema(Schema):
        a = field_factory()

    class JITSchema(JITSchemaMixin, PlainSchema):
        class Meta:
            jit_options = {"deserializer": "mapping"}

    return PlainSchema, JITSchema


def load_or_error(schema_cls: type[Schema], value: object) -> tuple[str, object]:
    """Load a value and return ('ok', result) or ('error', (exc_type, exc_msg, exc_repr))."""
    try:
        return ("ok", schema_cls().load({"a": value}))
    except ValidationError as exc:
        # For validation errors, compare error messages
        messages = exc.messages.get("a", []) if isinstance(exc.messages, dict) else []
        return ("error", ("ValidationError", sorted(messages), repr(exc)))
    except Exception as exc:  # noqa: BLE001 - comparing failure modes across implementations
        return ("error", (type(exc).__name__, str(exc), repr(exc)))


# Test cases: (field_id, field_factory, valid_values, invalid_values)
VALIDATOR_TEST_CASES = [
    # String length validators
    (
        "str_length_min",
        lambda: Str(validate=validate.Length(min=3)),
        ["hello", "abc", "test"],
        ["", "ab", 42],
    ),
    (
        "str_length_max",
        lambda: Str(validate=validate.Length(max=5)),
        ["hi", "hello", "abcde"],
        ["this is too long", 42],
    ),
    (
        "str_length_exact",
        lambda: Str(validate=validate.Length(equal=5)),
        ["hello", "world"],
        ["hi", "hello!", 42],
    ),
    # Numerical range validators
    (
        "int_range",
        lambda: Integer(validate=validate.Range(min=0, max=100)),
        [0, 50, 100, "42"],
        [-1, 101, "not-a-number"],
    ),
    (
        "int_range_min_only",
        lambda: Integer(validate=validate.Range(min=0)),
        [0, 42, 1000],
        [-1, -100],
    ),
    (
        "int_range_max_only",
        lambda: Integer(validate=validate.Range(max=100)),
        [100, 0, -50],
        [101, 1000],
    ),
    (
        "float_range",
        lambda: Float(validate=validate.Range(min=0.0, max=1.0)),
        [0.0, 0.5, 1.0, "0.75"],
        [-0.1, 1.1, "not-a-number"],
    ),
    (
        "decimal_range",
        lambda: Decimal(validate=validate.Range(min="0", max="100")),
        ["0", "50.5", "100", decimal.Decimal("25")],
        ["-1", "101", "not-a-number"],
    ),
    # OneOf validator
    (
        "one_of_strings",
        lambda: Str(validate=validate.OneOf(["red", "green", "blue"])),
        ["red", "green", "blue"],
        ["yellow", "purple", ""],
    ),
    (
        "one_of_integers",
        lambda: Integer(validate=validate.OneOf([1, 3, 5, 7, 9])),
        [1, 3, 5, "7", "9"],
        [0, 2, 10, "not-a-number"],
    ),
    # Regexp validator
    (
        "regexp_email_like",
        lambda: Str(validate=validate.Regexp(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")),
        ["test@example.com", "user.name@domain.org"],
        ["invalid-email", "@missing-local.com", "no-at-sign.com"],
    ),
    (
        "regexp_digits_only",
        lambda: Str(validate=validate.Regexp(r"^\d+$")),
        ["123", "0", "9876543210"],
        ["abc", "123abc", ""],
    ),
    # Combined validators with And()
    (
        "and_min_length_and_regexp",
        lambda: Str(validate=validate.And(validate.Length(min=5), validate.Regexp(r"^[A-Z].*"))),
        ["Hello", "World", "Test123"],
        ["hi", "hello", "12345", ""],
    ),
    (
        "and_range_and_equal",
        lambda: Integer(validate=validate.And(validate.Range(min=0, max=100), validate.Equal(50))),
        [50],
        [0, 49, 51, 100, 1, 47, 101, -5],
    ),
    # Custom error message validators
    (
        "custom_error_message",
        lambda: Str(validate=validate.Length(min=3, error="Must be at least 3 characters")),
        ["hello", "abc"],
        ["ab", ""],
    ),
    # List with inner field validators
    (
        "list_of_validated_strings",
        lambda: List(Str(validate=validate.Length(min=2))),
        [["ab", "cd", "efg"], ["hello", "world"]],
        [["a", "b"], ["x", "y", "z"], "not-a-list"],
    ),
    (
        "list_of_validated_integers",
        lambda: List(Integer(validate=validate.Range(min=0, max=10))),
        [[0, 5, 10], [1, 2, 3]],
        [[-1, 5], [0, 11], [1, 2, 3, 100]],
    ),
    # Dict with validated key and value fields
    (
        "dict_validated_values",
        lambda: Dict(keys=Str(), values=Integer(validate=validate.Range(min=0, max=100))),
        [{"a": 1, "b": 50, "c": 100}, {"x": 0}],
        [{"a": -1}, {"b": 101}, {"c": 50, "d": 200}],
    ),
    (
        "dict_validated_keys",
        lambda: Dict(keys=Str(validate=validate.Length(min=2)), values=Integer()),
        [{"ab": 1, "abc": 2}, {"xy": 10}],
        [{"a": 1}, {"x": 2}, {"ab": 1, "y": 2}],
    ),
    (
        "dict_both_validated",
        lambda: Dict(
            keys=Str(validate=validate.Length(min=2, max=5)), values=Float(validate=validate.Range(min=0.0, max=1.0))
        ),
        [{"ab": 0.5, "abc": 1.0}, {"xyz": 0.0}],
        [{"a": 0.5}, {"abcdef": 0.5}, {"ab": -0.1}, {"cd": 1.5}],
    ),
]


# Build parameterization data
_VALIDATOR_PARAMS = []
_VALIDATOR_IDS = []

for field_id, field_factory, valid_values, invalid_values in VALIDATOR_TEST_CASES:
    # Add valid values
    for idx, value in enumerate(valid_values):
        _VALIDATOR_PARAMS.append((field_factory, True, value))
        _VALIDATOR_IDS.append(f"{field_id}-valid-{idx}")

    # Add invalid values
    for idx, value in enumerate(invalid_values):
        _VALIDATOR_PARAMS.append((field_factory, False, value))
        _VALIDATOR_IDS.append(f"{field_id}-invalid-{idx}")


@pytest.mark.parametrize("validator_field_factory,is_valid,test_value", _VALIDATOR_PARAMS, ids=_VALIDATOR_IDS)
def test_validator_matches_plain_marshmallow(
    validator_field_factory: Callable[[], Field], is_valid: bool, test_value: object
) -> None:
    """JIT deserialization with validators must match plain marshmallow behavior."""
    plain_schema, jit_schema = build_schemas_with_validator(validator_field_factory)

    plain_result = load_or_error(plain_schema, test_value)
    jit_result = load_or_error(jit_schema, test_value)

    assert jit_result == plain_result, (
        f"Mismatch for value {test_value!r}:\n  Plain: {plain_result}\n  JIT:   {jit_result}"
    )
