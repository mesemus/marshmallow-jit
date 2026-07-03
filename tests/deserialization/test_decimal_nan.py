# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT

"""Decimal(allow_nan=True) deserializing an actual NaN value.

Kept separate from the shared FIELD_MATRIX (see conftest.py's decimal_allow_nan entry):
decimal.Decimal('NaN') != decimal.Decimal('NaN') (NaN is never equal to itself), so this can't
use the matrix's plain equality comparison - it needs .is_nan() instead.
"""

from marshmallow import Schema
from marshmallow.fields import Decimal

from marshmallow_jit.schema import JITSchemaMixin


def test_decimal_allow_nan_deserialization_matches_plain_marshmallow() -> None:
    class PlainSchema(Schema):
        a = Decimal(allow_nan=True)

    class JITSchema(JITSchemaMixin, PlainSchema):
        class Meta:
            jit_options = {"deserializer": "mapping"}

    plain_result = PlainSchema().load({"a": "nan"})
    jit_result = JITSchema().load({"a": "nan"})

    assert plain_result["a"].is_nan()
    assert jit_result["a"].is_nan()
