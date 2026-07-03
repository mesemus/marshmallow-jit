# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT

from marshmallow import Schema
from marshmallow.fields import Integer

from marshmallow_jit.schema import JITSchemaMixin


def test_schema_deserialization_canary() -> None:
    class MySchema(JITSchemaMixin, Schema):
        a = Integer()

        class Meta:
            jit_options = {"serializer": "mapping"}

    assert MySchema().load({}) == {}
    assert MySchema().load({"a": 1}) == {"a": 1}
    assert MySchema().load({"a": 1.5}) == {"a": 1}
