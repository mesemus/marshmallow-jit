# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT

import enum
from typing import override

import pytest
from marshmallow import Schema
from marshmallow.fields import (
    IP,
    UUID,
    AwareDateTime,
    Boolean,
    Constant,
    Date,
    DateTime,
    Decimal,
    Dict,
    Email,
    Enum,
    Field,
    Float,
    Function,
    Integer,
    IPInterface,
    IPv4,
    IPv4Interface,
    IPv6,
    IPv6Interface,
    List,
    Method,
    NaiveDateTime,
    Nested,
    Raw,
    Str,
    Time,
    TimeDelta,
    Url,
)

from marshmallow_jit.jit.inliners.aware_datetime import AwareDateTimeSerializationInliner
from marshmallow_jit.jit.inliners.base import Inliner
from marshmallow_jit.jit.inliners.boolean import BooleanSerializationInliner
from marshmallow_jit.jit.inliners.constant import ConstantSerializationInliner
from marshmallow_jit.jit.inliners.date import DateSerializationInliner
from marshmallow_jit.jit.inliners.datetime import DateTimeSerializationInliner
from marshmallow_jit.jit.inliners.decimal import DecimalSerializationInliner
from marshmallow_jit.jit.inliners.dict import DictSerializationInliner
from marshmallow_jit.jit.inliners.email import EmailSerializationInliner
from marshmallow_jit.jit.inliners.entrypoints import BuiltinSerializationInlinersFactory
from marshmallow_jit.jit.inliners.enum import EnumSerializationInliner
from marshmallow_jit.jit.inliners.float import FloatSerializationInliner
from marshmallow_jit.jit.inliners.function import FunctionSerializationInliner
from marshmallow_jit.jit.inliners.integer import IntegerSerializationInliner
from marshmallow_jit.jit.inliners.ip import IPSerializationInliner
from marshmallow_jit.jit.inliners.ip_interface import IPInterfaceSerializationInliner
from marshmallow_jit.jit.inliners.ipv4 import IPv4SerializationInliner
from marshmallow_jit.jit.inliners.ipv4_interface import IPv4InterfaceSerializationInliner
from marshmallow_jit.jit.inliners.ipv6 import IPv6SerializationInliner
from marshmallow_jit.jit.inliners.ipv6_interface import IPv6InterfaceSerializationInliner
from marshmallow_jit.jit.inliners.list import ListSerializationInliner
from marshmallow_jit.jit.inliners.method import MethodSerializationInliner
from marshmallow_jit.jit.inliners.naive_datetime import NaiveDateTimeSerializationInliner
from marshmallow_jit.jit.inliners.nested import NestedSerializationInliner
from marshmallow_jit.jit.inliners.raw import RawSerializationInliner
from marshmallow_jit.jit.inliners.registry import serialization_inliner_registry
from marshmallow_jit.jit.inliners.str import StrSerializationInliner
from marshmallow_jit.jit.inliners.time import TimeSerializationInliner
from marshmallow_jit.jit.inliners.timedelta import TimeDeltaSerializationInliner
from marshmallow_jit.jit.inliners.url import UrlSerializationInliner
from marshmallow_jit.jit.inliners.uuid import UUIDSerializationInliner
from marshmallow_jit.jit.registry import Registry


class _Color(enum.Enum):
    RED = "red"


class _ExampleNestedSchema(Schema):
    id = Integer()
    name = Str()


FIELD_TO_INLINER = [
    (Str, StrSerializationInliner),
    (Url, UrlSerializationInliner),
    (Email, EmailSerializationInliner),
    (UUID, UUIDSerializationInliner),
    (Integer, IntegerSerializationInliner),
    (Float, FloatSerializationInliner),
    (Decimal, DecimalSerializationInliner),
    (Boolean, BooleanSerializationInliner),
    (lambda: Constant(42), ConstantSerializationInliner),
    (lambda: Method("test_method"), MethodSerializationInliner),
    (lambda: Function(serialize=lambda obj: "test"), FunctionSerializationInliner),
    (Raw, RawSerializationInliner),
    (lambda: Enum(_Color), EnumSerializationInliner),
    (lambda: List(Str()), ListSerializationInliner),
    (lambda: Dict(keys=Str(), values=Integer()), DictSerializationInliner),
    (lambda: Nested(_ExampleNestedSchema), NestedSerializationInliner),
    (DateTime, DateTimeSerializationInliner),
    (NaiveDateTime, NaiveDateTimeSerializationInliner),
    (AwareDateTime, AwareDateTimeSerializationInliner),
    (Time, TimeSerializationInliner),
    (Date, DateSerializationInliner),
    (TimeDelta, TimeDeltaSerializationInliner),
    (IP, IPSerializationInliner),
    (IPv4, IPv4SerializationInliner),
    (IPv6, IPv6SerializationInliner),
    (IPInterface, IPInterfaceSerializationInliner),
    (IPv4Interface, IPv4InterfaceSerializationInliner),
    (IPv6Interface, IPv6InterfaceSerializationInliner),
]


@pytest.mark.parametrize("field_cls,inliner_cls", FIELD_TO_INLINER)
def test_serialization_inliner_factories_matches_each_field_type(
    field_cls: type[Field], inliner_cls: type[Inliner]
) -> None:
    result = serialization_inliner_registry.find(Schema(), "attr", field_cls())
    assert type(result) is inliner_cls


@pytest.mark.parametrize(
    "field,expected_cls",
    [
        pytest.param(NaiveDateTime(), NaiveDateTimeSerializationInliner, id="naive_datetime_over_datetime"),
        pytest.param(AwareDateTime(), AwareDateTimeSerializationInliner, id="aware_datetime_over_datetime"),
        pytest.param(IPv4(), IPv4SerializationInliner, id="ipv4_over_ip"),
        pytest.param(IPv6(), IPv6SerializationInliner, id="ipv6_over_ip"),
        pytest.param(IPv4Interface(), IPv4InterfaceSerializationInliner, id="ipv4_interface_over_ip_interface"),
        pytest.param(IPv6Interface(), IPv6InterfaceSerializationInliner, id="ipv6_interface_over_ip_interface"),
        pytest.param(Url(), UrlSerializationInliner, id="url_over_str"),
        pytest.param(Email(), EmailSerializationInliner, id="email_over_str"),
    ],
)
def test_more_specific_subclasses_take_priority_over_their_base_field(
    field: Field, expected_cls: type[Inliner]
) -> None:
    # Each of these fields is also an instance of a less specific type that is registered
    # with its own (wrong) inliner, so ordering in BuiltinInlinersFactory matters here.
    result = serialization_inliner_registry.find(Schema(), "attr", field)
    assert type(result) is expected_cls


def test_builtin_inliners_factory_is_registered_on_the_module_level_registry() -> None:
    assert any(
        isinstance(factory, BuiltinSerializationInlinersFactory) for factory in serialization_inliner_registry.factories
    )


def test_find_by_name_is_not_supported_for_inliners() -> None:
    factory = BuiltinSerializationInlinersFactory()
    assert factory.find_by_name("str", Schema(), "attr", Str()) is None
    assert factory.find_by_name("", Schema(), "attr", Str()) is None


def test_resolving_an_inliner_by_name_raises_key_error() -> None:
    with pytest.raises(KeyError):
        serialization_inliner_registry.resolve("str", Schema(), "attr", Str())


def test_factories_property_is_lazily_computed_and_cached() -> None:
    registry: Registry[Inliner, [Schema, str, Field]] = Registry("marshmallow_jit.inliners.does-not-exist")
    registry.add_builtin_factory(BuiltinSerializationInlinersFactory())
    # add_builtin_factory triggers _load(), so _entrypoint_loaded is now True
    assert registry._entrypoint_loaded
    # The factories are stored in internal lists
    first_entrypoint = registry.entrypoint_factories
    first_builtin = registry.builtin_factories
    # Subsequent accesses return the same cached lists (not recreated)
    assert registry.entrypoint_factories is first_entrypoint
    assert registry.builtin_factories is first_builtin


def test_add_factory_appends_to_the_computed_factories_list() -> None:
    registry: Registry[Inliner, [Schema, str, Field]] = Registry("marshmallow_jit.inliners.does-not-exist")
    _ = registry.factories

    class _AlwaysStr(BuiltinSerializationInlinersFactory):
        @override
        def find(self, schema: Schema, attr_name: str, field: Field) -> Inliner | None:
            return StrSerializationInliner()

    extra = _AlwaysStr()
    registry.add_factory(extra)
    assert registry.factories[-1] is extra
    assert type(registry.find(Schema(), "attr", Raw())) is StrSerializationInliner
