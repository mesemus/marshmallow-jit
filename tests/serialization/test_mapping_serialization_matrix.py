# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT

"""Matrix test: for every field type with a builtin Inliner, dumping via a JIT-compiled
"mapping" schema must produce exactly the same result (value or raised exception) as
dumping the same dict via a plain marshmallow schema.

The (field_factory, value) cases come from FIELD_SERIALIZATION_MATRIX in the parent
conftest.py, via the `pytest_generate_tests` hook there.
"""

from collections.abc import Callable
from typing import Any

from marshmallow import Schema

from marshmallow_jit.compat import MAField
from marshmallow_jit.schema import JITSchemaMixin


def build_schemas(field_factory: Callable[[], MAField]) -> tuple[type[Schema], type[Schema]]:
    class PlainSchema(Schema):
        a = field_factory()

    class JITSchema(JITSchemaMixin, PlainSchema):
        class Meta:
            jit_options = {"serializer": "mapping"}

    return PlainSchema, JITSchema


def dump_or_error(schema_cls: type[Schema], value: Any) -> tuple[str, Any]:
    try:
        return ("ok", schema_cls().dump({"a": value}))
    except Exception as exc:  # noqa: BLE001 - comparing failure modes across implementations, not handling them
        return ("error", (type(exc), str(exc), repr(exc)))


def test_jit_serialization_matches_plain_marshmallow(field_factory: Callable[[], MAField], value: Any) -> None:
    plain_schema, jit_schema = build_schemas(field_factory)
    plain_result = dump_or_error(plain_schema, value)
    jit_result = dump_or_error(jit_schema, value)
    assert jit_result == plain_result
