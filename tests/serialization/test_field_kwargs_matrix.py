# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT

"""Matrix test: for every field type with a builtin Inliner, and for each of the
dump-relevant Field.__init__ kwargs (dump_default, attribute, data_key - see
conftest.py's KWARGS_CASES), dumping via a JIT-compiled "instance" schema must produce
exactly the same result as dumping via a plain marshmallow schema.

The (field_factory, base_value, kwargs_case) cases come from FIELD_SERIALIZATION_MATRIX
in the parent conftest.py, via the `pytest_generate_tests` hook there.
"""

from collections.abc import Callable
from typing import Any

from conftest import build_source_kwargs, configure_field
from marshmallow import Schema
from marshmallow.fields import Field

from marshmallow_jit.schema import JITSchemaMixin


class Data:
    """A plain attribute-holding object, dumped via the "instance" serializer/accessor.

    Unlike the Data class in test_field_serialization_matrix.py, attributes are set from
    kwargs so a case can omit "a" entirely (simulating a missing attribute) or set some
    other attribute name (simulating Field(attribute=...) aliasing).
    """

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


def build_schemas(
    field_factory: Callable[[], Field], base_value: Any, kwargs_case: str
) -> tuple[type[Schema], type[Schema]]:
    field = field_factory()
    configure_field(field, base_value, kwargs_case)

    class PlainSchema(Schema):
        a = field

    class JITSchema(JITSchemaMixin, PlainSchema):
        class Meta:
            jit_options = {"serializer": "instance"}

    return PlainSchema, JITSchema


def dump_or_error(schema_cls: type[Schema], source_kwargs: dict[str, Any]) -> tuple[str, Any]:
    try:
        return ("ok", schema_cls().dump(Data(**source_kwargs)))
    except Exception as exc:  # noqa: BLE001 - comparing failure modes across implementations, not handling them
        return ("error", (type(exc), str(exc), repr(exc)))


def test_jit_serialization_matches_plain_marshmallow(
    field_factory: Callable[[], Field], base_value: Any, kwargs_case: str
) -> None:
    plain_schema, jit_schema = build_schemas(field_factory, base_value, kwargs_case)
    source_kwargs = build_source_kwargs(base_value, kwargs_case)
    plain_result = dump_or_error(plain_schema, source_kwargs)
    jit_result = dump_or_error(jit_schema, source_kwargs)
    assert jit_result == plain_result
