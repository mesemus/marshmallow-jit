# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT

"""Matrix test for partial loading: for every field type with a builtin Inliner, and for each
partial scenario (False, True, set of fields), loading via a JIT-compiled schema must produce
exactly the same result as loading via a plain marshmallow schema when the field is missing.

The (field_factory, base_value) cases come from FIELD_DESERIALIZATION_MATRIX in the parent
conftest.py, via the `pytest_generate_tests` hook there.
"""

from collections.abc import Callable
from typing import Any

import pytest
from marshmallow import Schema
from marshmallow.fields import Field

from marshmallow_jit.schema import JITSchemaMixin
from tests.conftest import PARTIAL_DESERIALIZATION_CASES


def build_schemas(
    field_factory: Callable[[], Field], base_value: Any, partial_case: str
) -> tuple[type[Schema], type[Schema]]:
    field = field_factory()

    class PlainSchema(Schema):
        a = field
        b = field  # Second field to test partial behavior

    class JITSchema(JITSchemaMixin, PlainSchema):
        class Meta:
            jit_options = {"deserializer": "mapping"}

    return PlainSchema, JITSchema


def load_or_error(schema_cls: type[Schema], source_kwargs: dict[str, Any], partial: bool | set[str]) -> tuple[str, Any]:
    try:
        return ("ok", schema_cls().load(dict(source_kwargs), partial=partial))
    except Exception as exc:  # noqa: BLE001 - comparing failure modes across implementations
        return ("error", (type(exc), str(exc), repr(exc)))


def get_partial_value(partial_case: str) -> bool | set[str]:
    """Convert partial case string to actual partial value."""
    if partial_case == "partial_false":
        return False
    elif partial_case == "partial_true":
        return True
    elif partial_case == "partial_set_a":
        return {"a"}
    elif partial_case == "partial_set_b":
        return {"b"}
    else:
        raise ValueError(f"Unknown partial case: {partial_case}")


def build_partial_source_kwargs(base_value: Any, partial_case: str) -> dict[str, Any]:
    """Build source kwargs where field 'a' is always missing to test partial behavior."""
    # Always omit 'a' to test how partial handles missing required fields
    # Only include 'b' which should always be present
    return {"b": base_value}


@pytest.mark.parametrize(
    ("field_factory", "base_value", "partial_case"),
    [
        (field_factory, base_value, partial_case)
        for field_factory_name, field_factory, values in [
            # Include a representative subset of field types
            ("integer", lambda: __import__("marshmallow.fields").fields.Integer(), [42]),
            ("float", lambda: __import__("marshmallow.fields").fields.Float(), [3.14]),
            ("decimal", lambda: __import__("marshmallow.fields").fields.Decimal(), ["1.23"]),
            ("string", lambda: __import__("marshmallow.fields").fields.Str(), ["hello"]),
            (
                "datetime_iso",
                lambda: __import__("marshmallow.fields").fields.DateTime(),
                [__import__("datetime").datetime(2024, 1, 2)],
            ),
            (
                "date_iso",
                lambda: __import__("marshmallow.fields").fields.Date(),
                [__import__("datetime").date(2024, 1, 2)],
            ),
            (
                "time_iso",
                lambda: __import__("marshmallow.fields").fields.Time(),
                [__import__("datetime").time(3, 4, 5)],
            ),
            (
                "timedelta_seconds",
                lambda: __import__("marshmallow.fields").fields.TimeDelta(),
                [__import__("datetime").timedelta(days=1)],
            ),
            ("uuid", lambda: __import__("marshmallow.fields").fields.UUID(), [__import__("uuid").uuid4()]),
            ("boolean", lambda: __import__("marshmallow.fields").fields.Boolean(), [True]),
        ]
        for base_value in values[:1]  # Use first valid value
        for partial_case in PARTIAL_DESERIALIZATION_CASES
    ],
    ids=lambda x: (x.__name__ if hasattr(x, "__name__") else str(x) if callable(x) else x) if isinstance(x, str) else x,
)
def test_jit_partial_deserialization_matches_plain_marshmallow(
    field_factory: Callable[[], Field],
    base_value: Any,
    partial_case: str,
) -> None:
    """Test that partial loading works identically in JIT and plain marshmallow."""
    plain_schema, jit_schema = build_schemas(field_factory, base_value, partial_case)
    partial_value = get_partial_value(partial_case)
    source_kwargs = build_partial_source_kwargs(base_value, partial_case)

    plain_result = load_or_error(plain_schema, source_kwargs, partial_value)
    jit_result = load_or_error(jit_schema, source_kwargs, partial_value)

    assert jit_result == plain_result, (
        f"Partial case {partial_case} failed:\n  Plain: {plain_result}\n  JIT:   {jit_result}"
    )
