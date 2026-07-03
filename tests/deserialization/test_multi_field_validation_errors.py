# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT

"""Multi-field deserialization validation error tests.

This module tests that when loading data with multiple fields results in validation errors,
the `valid_data` attribute of the ValidationError is identical between JIT-compiled schemas
and plain marshmallow schemas.

This ensures that partial deserialization behavior is consistent across both implementations.
"""

from collections.abc import Callable
from typing import Any

import pytest
from marshmallow import Schema, ValidationError
from marshmallow.fields import Decimal, Email, Field, Float, Integer, List, Str

from marshmallow_jit.schema import JITSchemaMixin


def _raise(msg: str) -> None:
    """Helper to raise a validation error with a custom message in inline validators."""
    raise ValidationError(msg)


def build_multi_field_schemas(field_configs: dict[str, Callable[[], Field]]) -> tuple[type[Schema], type[Schema]]:
    """Build plain and JIT schemas with the given field configurations.

    Args:
        field_configs: Dict mapping field names to field factories (callable returning a field).

    Returns:
        Tuple of (PlainSchema class, JITSchema class)
    """

    class PlainSchema(Schema):
        pass

    # Dynamically add fields to PlainSchema
    for name, field_factory in field_configs.items():
        setattr(PlainSchema, name, field_factory())

    class JITSchema(JITSchemaMixin, PlainSchema):
        class Meta:
            jit_options = {"deserializer": "mapping"}

    return PlainSchema, JITSchema


# Type alias for error info dict
type ErrorInfo = dict[str, Any]
type ResultOrError = tuple[str, Any]  # ("ok", result) or ("error", ErrorInfo)


def load_or_error_with_valid_data(schema_cls: type[Schema], data: dict[str, Any]) -> ResultOrError:
    """Load data and return result or detailed error information including valid_data.

    Args:
        schema_cls: Schema class to use for loading.
        data: Data dict to load.

    Returns:
        Tuple of (status, result_or_error_info) where:
        - On success: ("ok", deserialized_data_dict)
        - On error: ("error", {
            "exc_type": str,
            "messages": dict,
            "data": dict,
            "valid_data": dict,
            "exc_repr": str
          })
    """
    try:
        result = schema_cls().load(data)
        return ("ok", result)
    except ValidationError as exc:
        return (
            "error",
            {
                "exc_type": "ValidationError",
                "messages": exc.messages,
                "data": exc.data,
                "valid_data": exc.valid_data if exc.valid_data else {},
                "exc_repr": repr(exc),
            },
        )
    except Exception as exc:  # noqa: BLE001 - comparing failure modes across implementations
        return (
            "error",
            {
                "exc_type": type(exc).__name__,
                "messages": str(exc),
                "data": None,
                "valid_data": None,
                "exc_repr": repr(exc),
            },
        )


def compare_validation_errors(plain_result: ResultOrError, jit_result: ResultOrError, data: dict[str, Any]) -> None:
    """Compare validation error details between plain and JIT schemas.

    Args:
        plain_result: Result tuple from plain marshmallow.
        jit_result: Result tuple from JIT schema.
        data: Original input data (for error messages).

    Raises:
        AssertionError: If results don't match.
    """
    assert jit_result[0] == plain_result[0], (
        f"Status mismatch for data {data!r}:\n  Plain: {plain_result[0]}\n  JIT:   {jit_result[0]}"
    )

    if plain_result[0] == "ok":
        # Both succeeded - check data matches
        assert jit_result[1] == plain_result[1], (
            f"Success data mismatch for data {data!r}:\n  Plain: {plain_result[1]}\n  JIT:   {jit_result[1]}"
        )
    else:
        # Both failed - compare error details
        plain_error = plain_result[1]
        jit_error = jit_result[1]

        # Check exception type
        assert jit_error["exc_type"] == plain_error["exc_type"], (
            f"Exception type mismatch for data {data!r}:\n  Plain: {plain_error['exc_type']}\n"
            f"  JIT:   {jit_error['exc_type']}"
        )

        # Most importantly: check valid_data matches
        assert jit_error["valid_data"] == plain_error["valid_data"], (
            f"valid_data mismatch for data {data!r}:\n  Plain: {plain_error['valid_data']}\n"
            f"  JIT:   {jit_error['valid_data']}"
        )

        # Also check messages match
        assert jit_error["messages"] == plain_error["messages"], (
            f"messages mismatch for data {data!r}:\n  Plain: {plain_error['messages']}\n"
            f"  JIT:   {jit_error['messages']}"
        )

        # And raw data matches
        assert jit_error["data"] == plain_error["data"], (
            f"data mismatch for data {data!r}:\n  Plain: {plain_error['data']}\n  JIT:   {jit_error['data']}"
        )


# Test case definitions: (test_id, field_configs, test_data_cases)
# Each test_data_cases entry: (description, data_dict, should_succeed)
MULTI_FIELD_VALIDATION_TEST_CASES = [
    # Basic required field failures
    (
        "required_fields_missing",
        {
            "name": lambda: Str(required=True),
            "age": lambda: Integer(required=True),
            "email": lambda: Email(required=True),
        },
        [
            ("all_present_valid", {"name": "Alice", "age": 30, "email": "alice@example.com"}, True),
            ("all_missing", {}, False),
            ("only_name_present", {"name": "Alice"}, False),
            ("name_and_age_present", {"name": "Alice", "age": 30}, False),
            ("name_and_email_present", {"name": "Alice", "email": "alice@example.com"}, False),
        ],
    ),
    # Mixed valid/invalid types
    (
        "mixed_type_errors",
        {
            "name": lambda: Str(required=True),
            "age": lambda: Integer(required=True),
            "email": lambda: Email(),
            "score": lambda: Float(),
        },
        [
            ("all_valid", {"name": "Bob", "age": 25, "email": "bob@test.com", "score": 95.5}, True),
            (
                "age_invalid_string",
                {"name": "Bob", "age": "not-a-number", "email": "bob@test.com", "score": 95.5},
                False,
            ),
            ("email_invalid", {"name": "Bob", "age": 25, "email": "not-an-email", "score": 95.5}, False),
            ("multiple_invalid", {"name": "Bob", "age": "bad", "email": "bad@", "score": 95.5}, False),
            ("name_missing_age_invalid", {"age": "bad", "email": "bob@test.com"}, False),
        ],
    ),
    # Numeric range validation with multiple fields
    (
        "numeric_range_multiple_fields",
        {
            "age": lambda: Integer(validate=lambda v: 0 <= v <= 150 or _raise("Age must be 0-150")),
            "temperature": lambda: Float(validate=lambda v: -273.15 <= v <= 1000 or _raise("Invalid temperature")),
            "percentage": lambda: Float(validate=lambda v: 0 <= v <= 100 or _raise("Percentage must be 0-100")),
        },
        [
            ("all_in_range", {"age": 30, "temperature": 25.5, "percentage": 75.0}, True),
            ("age_out_of_range", {"age": 200, "temperature": 25.5, "percentage": 75.0}, False),
            ("temp_out_of_range", {"age": 30, "temperature": -300, "percentage": 75.0}, False),
            ("multiple_out_of_range", {"age": 200, "temperature": -300, "percentage": 150}, False),
            ("all_out_of_range", {"age": 200, "temperature": -300, "percentage": 150}, False),
        ],
    ),
    # String length validations
    (
        "string_length_multiple_fields",
        {
            "username": lambda: Str(validate=lambda v: len(v) >= 3 or _raise("Username too short")),
            "password": lambda: Str(validate=lambda v: len(v) >= 8 or _raise("Password too short")),
            "code": lambda: Str(validate=lambda v: len(v) == 4 or _raise("Code must be exactly 4 chars")),
        },
        [
            ("all_valid", {"username": "john", "password": "secret123", "code": "ABCD"}, True),
            ("username_too_short", {"username": "ab", "password": "secret123", "code": "ABCD"}, False),
            ("password_too_short", {"username": "john", "password": "short", "code": "ABCD"}, False),
            ("code_wrong_length", {"username": "john", "password": "secret123", "code": "ABC"}, False),
            ("multiple_too_short", {"username": "ab", "password": "x", "code": "ABCD"}, False),
        ],
    ),
    # Combination of required + validation errors
    (
        "required_plus_validation",
        {
            "email": lambda: Email(required=True),
            "age": lambda: Integer(required=True, validate=lambda v: v >= 18 or _raise("Must be 18+")),
            "nickname": lambda: Str(validate=lambda v: len(v) <= 20 or _raise("Nickname too long")),
        },
        [
            ("all_valid", {"email": "user@example.com", "age": 25, "nickname": "coolguy"}, True),
            ("email_missing", {"age": 25, "nickname": "coolguy"}, False),
            ("age_under_18", {"email": "user@example.com", "age": 16, "nickname": "coolguy"}, False),
            ("nickname_too_long", {"email": "user@example.com", "age": 25, "nickname": "a" * 25}, False),
            ("email_missing_age_under_18", {"age": 16, "nickname": "coolguy"}, False),
            ("all_errors", {"email": "bad@", "age": 16, "nickname": "a" * 25}, False),
        ],
    ),
    # Nested-like structure with multiple independent fields
    (
        "contact_info_fields",
        {
            "first_name": lambda: Str(required=True, validate=lambda v: len(v) >= 1 or _raise("Required")),
            "last_name": lambda: Str(required=True, validate=lambda v: len(v) >= 1 or _raise("Required")),
            "phone": lambda: Str(validate=lambda v: v.replace("-", "").isdigit() or _raise("Invalid phone")),
            "website": lambda: Str(validate=lambda v: v.startswith("http") or _raise("Must start with http")),
        },
        [
            (
                "all_valid",
                {"first_name": "Jane", "last_name": "Doe", "phone": "555-1234", "website": "https://example.com"},
                True,
            ),
            (
                "first_name_empty",
                {"first_name": "", "last_name": "Doe", "phone": "555-1234", "website": "https://example.com"},
                False,
            ),
            (
                "phone_invalid",
                {"first_name": "Jane", "last_name": "Doe", "phone": "abc-defg", "website": "https://example.com"},
                False,
            ),
            (
                "website_no_protocol",
                {"first_name": "Jane", "last_name": "Doe", "phone": "555-1234", "website": "example.com"},
                False,
            ),
            (
                "multiple_invalid",
                {"first_name": "", "last_name": "Doe", "phone": "abc", "website": "example.com"},
                False,
            ),
        ],
    ),
    # Decimal precision validation
    (
        "financial_fields",
        {
            "amount": lambda: Decimal(required=True, places=2),
            "tax_rate": lambda: Decimal(validate=lambda v: 0 <= v <= 1 or _raise("Tax rate must be 0-1")),
            "quantity": lambda: Integer(validate=lambda v: v > 0 or _raise("Quantity must be positive")),
        },
        [
            ("all_valid", {"amount": "19.99", "tax_rate": "0.0825", "quantity": 5}, True),
            ("amount_missing", {"tax_rate": "0.0825", "quantity": 5}, False),
            ("tax_rate_negative", {"amount": "19.99", "tax_rate": "-0.1", "quantity": 5}, False),
            ("quantity_zero", {"amount": "19.99", "tax_rate": "0.0825", "quantity": 0}, False),
            ("tax_and_quantity_invalid", {"amount": "19.99", "tax_rate": "1.5", "quantity": -1}, False),
        ],
    ),
    # List fields with validation
    (
        "list_fields",
        {
            "tags": lambda: List(Str(validate=lambda v: len(v) >= 2), required=True),
            "scores": lambda: List(Integer(validate=lambda v: 0 <= v <= 100)),
        },
        [
            ("all_valid", {"tags": ["python", "testing"], "scores": [85, 90, 95]}, True),
            ("tags_empty", {"tags": [], "scores": [85, 90]}, False),
            ("tag_too_short", {"tags": ["a", "bb"], "scores": [85, 90]}, False),
            ("score_out_of_range", {"tags": ["python"], "scores": [85, 150, 95]}, False),
            ("both_invalid", {"tags": ["x"], "scores": [-1, 150]}, False),
        ],
    ),
    # Edge case: all fields valid except one
    (
        "single_failure_many_fields",
        {
            "field_a": lambda: Str(required=True),
            "field_b": lambda: Integer(required=True),
            "field_c": lambda: Email(required=True),
            "field_d": lambda: Float(required=True),
            "field_e": lambda: Decimal(required=True),
        },
        [
            (
                "all_valid",
                {"field_a": "text", "field_b": 42, "field_c": "a@b.com", "field_d": 3.14, "field_e": "2.5"},
                True,
            ),
            (
                "only_field_b_invalid",
                {"field_a": "text", "field_b": "bad", "field_c": "a@b.com", "field_d": 3.14, "field_e": "2.5"},
                False,
            ),
            (
                "only_field_c_invalid",
                {"field_a": "text", "field_b": 42, "field_c": "bad", "field_d": 3.14, "field_e": "2.5"},
                False,
            ),
            (
                "only_field_e_invalid",
                {"field_a": "text", "field_b": 42, "field_c": "a@b.com", "field_d": 3.14, "field_e": "bad"},
                False,
            ),
        ],
    ),
    # Edge case: first field fails, rest are valid
    (
        "first_field_fails",
        {
            "field_a": lambda: Integer(required=True, validate=lambda v: v > 0 or _raise("Must be positive")),
            "field_b": lambda: Str(required=True),
            "field_c": lambda: Email(required=True),
        },
        [
            ("all_valid", {"field_a": 1, "field_b": "text", "field_c": "a@b.com"}, True),
            ("field_a_zero", {"field_a": 0, "field_b": "text", "field_c": "a@b.com"}, False),
            ("field_a_negative", {"field_a": -5, "field_b": "text", "field_c": "a@b.com"}, False),
        ],
    ),
    # Edge case: last field fails, rest are valid
    (
        "last_field_fails",
        {
            "field_a": lambda: Str(required=True),
            "field_b": lambda: Integer(required=True),
            "field_c": lambda: Email(required=True),
        },
        [
            ("all_valid", {"field_a": "text", "field_b": 42, "field_c": "a@b.com"}, True),
            ("field_c_invalid", {"field_a": "text", "field_b": 42, "field_c": "not-email"}, False),
        ],
    ),
    # Complex real-world scenario: user registration
    (
        "user_registration",
        {
            "username": lambda: Str(
                required=True, validate=lambda v: (len(v) >= 3 and len(v) <= 30) or _raise("Username 3-30 chars")
            ),
            "email": lambda: Email(required=True),
            "age": lambda: Integer(required=True, validate=lambda v: v >= 13 or _raise("Must be 13+")),
            "bio": lambda: Str(validate=lambda v: len(v) <= 500 or _raise("Bio too long")),
            "website": lambda: Str(
                validate=lambda v: not v or v.startswith("http") or _raise("URL must have protocol")
            ),
        },
        [
            (
                "complete_valid",
                {
                    "username": "johndoe123",
                    "email": "john@example.com",
                    "age": 25,
                    "bio": "Hello, world!",
                    "website": "https://johndoe.com",
                },
                True,
            ),
            (
                "username_too_short",
                {"username": "jo", "email": "john@example.com", "age": 25, "bio": "Hi", "website": ""},
                False,
            ),
            (
                "underage",
                {"username": "johndoe", "email": "john@example.com", "age": 10, "bio": "Hi", "website": ""},
                False,
            ),
            (
                "bio_too_long",
                {"username": "johndoe", "email": "john@example.com", "age": 25, "bio": "x" * 501, "website": ""},
                False,
            ),
            (
                "website_no_protocol",
                {"username": "johndoe", "email": "john@example.com", "age": 25, "bio": "Hi", "website": "johndoe.com"},
                False,
            ),
            (
                "multiple_user_errors",
                {"username": "ab", "email": "bad@", "age": 10, "bio": "x" * 600, "website": "nope.com"},
                False,
            ),
            ("missing_email_age", {"username": "johndoe", "age": 10, "bio": "Hi"}, False),
        ],
    ),
]


@pytest.mark.parametrize(
    "test_id,field_configs,desc,data,should_succeed",
    [
        (f"{test_id}_{desc}", field_configs, desc, data, should_succeed)
        for test_id, field_configs, test_cases in MULTI_FIELD_VALIDATION_TEST_CASES
        for desc, data, should_succeed in test_cases
    ],
    ids=lambda x: x[2] if isinstance(x, tuple) else x,
)
def test_multi_field_validation_error_valid_data(
    test_id: str,
    field_configs: dict[str, Callable[[], Field]],
    desc: str,
    data: dict[str, Any],
    should_succeed: bool,
) -> None:
    """Test that valid_data in ValidationError matches between plain and JIT schemas.

    This is critical for ensuring that partial deserialization works correctly
    and that any post-validation processing can rely on consistent behavior.
    """
    plain_schema, jit_schema = build_multi_field_schemas(field_configs)

    plain_result = load_or_error_with_valid_data(plain_schema, data)
    jit_result = load_or_error_with_valid_data(jit_schema, data)

    compare_validation_errors(plain_result, jit_result, data)


# Simpler parametrized version for better test output
SIMPLE_MULTI_FIELD_CASES = [
    # (schema_fields, test_data, description)
    (
        {"name": Str(required=True), "age": Integer(required=True)},
        {"name": "Alice", "age": 30},
        "both_valid",
    ),
    (
        {"name": Str(required=True), "age": Integer(required=True)},
        {"name": "Alice", "age": "bad"},
        "age_invalid",
    ),
    (
        {"name": Str(required=True), "age": Integer(required=True)},
        {"name": "Alice"},
        "age_missing",
    ),
    (
        {"name": Str(required=True), "age": Integer(required=True), "email": Email()},
        {"name": "Bob", "age": 25, "email": "bad@"},
        "email_invalid_name_age_valid",
    ),
    (
        {"name": Str(required=True), "age": Integer(required=True), "email": Email()},
        {"name": "Bob", "age": "bad", "email": "bad@"},
        "age_and_email_invalid",
    ),
    (
        {"a": Str(), "b": Integer(), "c": Float(), "d": Decimal()},
        {"a": "x", "b": "bad", "c": 1.5, "d": "bad"},
        "b_and_d_invalid",
    ),
]


@pytest.mark.parametrize(
    "fields_dict,data,description",
    SIMPLE_MULTI_FIELD_CASES,
    ids=lambda x: x[2] if isinstance(x, tuple) and len(x) == 3 else x,
)
def test_simple_multi_field_valid_data(
    fields_dict: dict[str, object], data: dict[str, object], description: str
) -> None:
    """Simple test cases for multi-field validation with clear valid_data expectations."""

    class PlainSchema(Schema):
        pass

    for name, field in fields_dict.items():
        setattr(PlainSchema, name, field)

    class JITSchema(JITSchemaMixin, PlainSchema):
        class Meta:
            jit_options = {"deserializer": "mapping"}

    plain_result = load_or_error_with_valid_data(PlainSchema, data)
    jit_result = load_or_error_with_valid_data(JITSchema, data)

    compare_validation_errors(plain_result, jit_result, data)
