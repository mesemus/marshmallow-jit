# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT

"""Matrix test: for every field type with a builtin Inliner, and for each of the
load-relevant Field.__init__ kwargs (load_default, data_key - see
conftest.py's DESERIALIZATION_KWARGS_CASES), loading via a JIT-compiled schema must produce
exactly the same result as loading via a plain marshmallow schema.

The (field_factory, base_value, kwargs_case) cases come from FIELD_DESERIALIZATION_MATRIX
in the parent conftest.py, via the `pytest_generate_tests` hook there.
"""

from collections.abc import Callable
from typing import Any

from marshmallow import Schema
from marshmallow.fields import Field

from marshmallow_jit.schema import JITSchemaMixin
from tests.deserialization.conftest import (
    build_deserialization_source_kwargs,
    configure_deserialization_field,
)


def build_schemas(
    field_factory: Callable[[], Field], base_value: Any, kwargs_case: str
) -> tuple[type[Schema], type[Schema]]:
    field = field_factory()
    configure_deserialization_field(field, base_value, kwargs_case)

    class PlainSchema(Schema):
        a = field

    class JITSchema(JITSchemaMixin, PlainSchema):
        class Meta:
            jit_options = {"deserializer": "mapping"}

    return PlainSchema, JITSchema


def load_or_error(schema_cls: type[Schema], source_kwargs: dict[str, Any]) -> tuple[str, Any]:
    try:
        return ("ok", schema_cls().load(dict(source_kwargs)))
    except Exception as exc:  # noqa: BLE001 - comparing failure modes across implementations, not handling them
        return ("error", (type(exc), str(exc), repr(exc)))


def test_jit_deserialization_matches_plain_marshmallow(
    field_factory: Callable[[], Field], base_value: Any, kwargs_case: str
) -> None:
    plain_schema, jit_schema = build_schemas(field_factory, base_value, kwargs_case)
    source_kwargs = build_deserialization_source_kwargs(base_value, kwargs_case)
    plain_result = load_or_error(plain_schema, source_kwargs)
    jit_result = load_or_error(jit_schema, source_kwargs)
    assert jit_result == plain_result
