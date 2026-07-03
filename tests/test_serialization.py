# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT

from marshmallow import Schema
from marshmallow.fields import Int


class SerializationSchema(Schema):
    a = Int(required=True)
    b = Int(required=False)


def test_serialization() -> None:
    schema = SerializationSchema()
    result = schema.dump({"a": 1, "b": 2})
    assert result == {"a": 1, "b": 2}

    result = schema.dump({})
    assert result == {}
