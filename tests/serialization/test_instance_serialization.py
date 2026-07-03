# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT

from dataclasses import dataclass

from marshmallow import Schema
from marshmallow.fields import Integer

from marshmallow_jit.schema import JITSchemaMixin


def test_schema_serialization_canary() -> None:
    class MySchema(Schema):
        a = Integer()

    class MyJITSchema(JITSchemaMixin, MySchema):
        class Meta:
            jit_options = {"serializer": "instance"}

    @dataclass
    class Data:
        a: object = None

    assert MySchema().dump(Data()) == MyJITSchema().dump(Data()) == {"a": None}
    assert MySchema().dump(Data(1)) == MyJITSchema().dump(Data(1)) == {"a": 1}
    assert MySchema().dump(Data(1.5)) == MyJITSchema().dump(Data(1.5)) == {"a": 1}
