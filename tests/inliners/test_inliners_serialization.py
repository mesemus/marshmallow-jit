# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT

import datetime as dt
import enum
import ipaddress
import uuid
from typing import Any

import pytest
from marshmallow import Schema
from marshmallow.fields import (
    IP,
    UUID,
    AwareDateTime,
    Boolean,
    Date,
    DateTime,
    Decimal,
    Email,
    Enum,
    Field,
    Float,
    Integer,
    IPInterface,
    IPv4,
    IPv4Interface,
    IPv6,
    IPv6Interface,
    NaiveDateTime,
    Raw,
    Str,
    Time,
    TimeDelta,
    Url,
)

from marshmallow_jit.jit.context import Context
from marshmallow_jit.jit.inliners.aware_datetime import AwareDateTimeSerializationInliner
from marshmallow_jit.jit.inliners.base import Inliner
from marshmallow_jit.jit.inliners.boolean import BooleanSerializationInliner
from marshmallow_jit.jit.inliners.date import DateSerializationInliner
from marshmallow_jit.jit.inliners.datetime import DateTimeSerializationInliner
from marshmallow_jit.jit.inliners.decimal import DecimalSerializationInliner
from marshmallow_jit.jit.inliners.email import EmailSerializationInliner
from marshmallow_jit.jit.inliners.enum import EnumSerializationInliner
from marshmallow_jit.jit.inliners.float import FloatSerializationInliner
from marshmallow_jit.jit.inliners.integer import IntegerSerializationInliner
from marshmallow_jit.jit.inliners.ip import IPSerializationInliner
from marshmallow_jit.jit.inliners.ip_interface import IPInterfaceSerializationInliner
from marshmallow_jit.jit.inliners.ipv4 import IPv4SerializationInliner
from marshmallow_jit.jit.inliners.ipv4_interface import IPv4InterfaceSerializationInliner
from marshmallow_jit.jit.inliners.ipv6 import IPv6SerializationInliner
from marshmallow_jit.jit.inliners.ipv6_interface import IPv6InterfaceSerializationInliner
from marshmallow_jit.jit.inliners.naive_datetime import NaiveDateTimeSerializationInliner
from marshmallow_jit.jit.inliners.raw import RawSerializationInliner
from marshmallow_jit.jit.inliners.str import StrSerializationInliner
from marshmallow_jit.jit.inliners.time import TimeSerializationInliner
from marshmallow_jit.jit.inliners.timedelta import TimeDeltaSerializationInliner
from marshmallow_jit.jit.inliners.url import UrlSerializationInliner
from marshmallow_jit.jit.inliners.uuid import UUIDSerializationInliner
from marshmallow_jit.jit.python_code import PythonCode


class _Color(enum.Enum):
    RED = "red"
    GREEN = "green"


class _Number(enum.Enum):
    ONE = 1
    TWO = 2


def assert_compilable(code: PythonCode, environment: dict[str, Any]) -> None:
    new_code = PythonCode(code.prologue)
    new_code.variables.update(code.variables)
    new_code.extra_imports.update(code.extra_imports)

    with new_code.indent("def f()"):
        new_code += str(code)

    new_code.compile(environment)


def generate(inliner: Inliner, field: Field, attr_name: str = "attr") -> PythonCode:
    code = PythonCode()
    context = Context()
    field_var = code.add_variable("field", field)
    inliner.generate_code(code, "value", field_var, Schema(), attr_name, field, context)
    return code


def field_variable(code: PythonCode, field: Field) -> str:
    for name, value in code.variables.items():
        if value is field:
            return name
    raise AssertionError("field was not registered as a code variable")


def only_variable(code: PythonCode) -> str:
    (name,) = code.variables.keys()
    return name


def run(inliner: Inliner, field: Field, value: Any, attr_name: str = "attr", obj: Any = None) -> Any:
    """Compiles the generated code into a real function and executes it on `value`."""
    code = generate(inliner, field, attr_name)

    wrapper = PythonCode(code.prologue)
    wrapper.variables.update(code.variables)
    wrapper.extra_imports.update(code.extra_imports)
    with wrapper.indent("def f(value, obj=None)"):
        wrapper += str(code)
        wrapper += "return value"

    namespace = wrapper.compile(code.variables)
    return namespace["f"](value, obj)


def assert_matches_marshmallow(inliner: Inliner, field: Field, value: Any, obj: Any = None) -> None:
    if obj is None:
        obj = object()
    assert run(inliner, field, value, obj=obj) == field._serialize(value, "attr", obj)


def test_str_serialization_inliner() -> None:
    inliner = StrSerializationInliner()
    code = PythonCode()
    context = Context()
    field_var = code.add_variable("field", Str())
    inliner.generate_code(code, "value", field_var, Schema(), "attr", Str(), context)
    assert (
        str(code) == "if value is not None:\n    if type(value) is not str:\n"
        "        value = marshmallow.utils.ensure_text_type(value)"
    )
    assert_compilable(code, {})


@pytest.mark.parametrize(
    "inliner_cls,field_cls",
    [
        (StrSerializationInliner, Str),
        (UrlSerializationInliner, Url),
        (EmailSerializationInliner, Email),
    ],
)
def test_str_url_and_email_serialization_reuse_strs_code(inliner_cls: type[Inliner], field_cls: type[Field]) -> None:
    # Url and Email do not override String's _serialize, so their generated code is identical.
    code = generate(inliner_cls(), field_cls())
    assert (
        str(code) == "if value is not None:\n    if type(value) is not str:\n"
        "        value = marshmallow.utils.ensure_text_type(value)"
    )
    assert_compilable(code, {})


@pytest.mark.parametrize(
    "inliner_cls,field_cls",
    [
        (StrSerializationInliner, Str),
        (UrlSerializationInliner, Url),
        (EmailSerializationInliner, Email),
    ],
)
@pytest.mark.parametrize("value", [None, "hello", b"hello", 42, "https://example.com", "a@b.com"])
def test_str_url_and_email_serialization_matches_marshmallow(
    inliner_cls: type[Inliner], field_cls: type[Field], value: object
) -> None:
    assert_matches_marshmallow(inliner_cls(), field_cls(), value)


def test_uuid_serialization_inliner_code() -> None:
    code = generate(UUIDSerializationInliner(), UUID())
    assert str(code) == "if value is not None:\n    value = str(value)"
    assert_compilable(code, {})


@pytest.mark.parametrize("value", [None, uuid.uuid4(), uuid.UUID(int=0)])
def test_uuid_serialization_matches_marshmallow(value: object) -> None:
    assert_matches_marshmallow(UUIDSerializationInliner(), UUID(), value)


def test_integer_serialization_inliner_code() -> None:
    code = generate(IntegerSerializationInliner(), Integer())
    assert str(code) == "if value is not None:\n    value = int(value)"
    assert_compilable(code, {})


def test_integer_serialization_inliner_code_as_string() -> None:
    code = generate(IntegerSerializationInliner(), Integer(as_string=True))
    assert str(code) == "if value is not None:\n    value = int(value)\n    value = str(value)"
    assert_compilable(code, {})


@pytest.mark.parametrize("as_string", [False, True])
@pytest.mark.parametrize("value", [None, 0, 42, -7, "42"])
def test_integer_serialization_matches_marshmallow(as_string: bool, value: object) -> None:
    assert_matches_marshmallow(IntegerSerializationInliner(), Integer(as_string=as_string), value)


def test_float_serialization_inliner_code() -> None:
    code = generate(FloatSerializationInliner(), Float())
    assert str(code) == "if value is not None:\n    value = float(value)"
    assert_compilable(code, {})


def test_float_serialization_inliner_code_as_string() -> None:
    code = generate(FloatSerializationInliner(), Float(as_string=True))
    assert str(code) == "if value is not None:\n    value = float(value)\n    value = str(value)"
    assert_compilable(code, {})


@pytest.mark.parametrize("as_string", [False, True])
@pytest.mark.parametrize("value", [None, 0, 42.5, -7.25, "3.14"])
def test_float_serialization_matches_marshmallow(as_string: bool, value: object) -> None:
    assert_matches_marshmallow(FloatSerializationInliner(), Float(as_string=as_string), value)


def test_decimal_serialization_inliner_code() -> None:
    field = Decimal()
    code = generate(DecimalSerializationInliner(), field)
    fvar = field_variable(code, field)
    assert str(code) == f"if value is not None:\n    value = {fvar}._format_num(value)"
    assert_compilable(code, {})


def test_decimal_serialization_inliner_code_as_string() -> None:
    field = Decimal(as_string=True)
    code = generate(DecimalSerializationInliner(), field)
    fvar = field_variable(code, field)
    assert str(code) == (
        f'if value is not None:\n    value = {fvar}._format_num(value)\n    value = format(value, "f")'
    )
    assert_compilable(code, {})


@pytest.mark.parametrize("as_string", [False, True])
@pytest.mark.parametrize("places,value", [(None, None), (None, "1.2345"), (2, "1.2345"), (None, 42)])
def test_decimal_serialization_matches_marshmallow(as_string: bool, places: int | None, value: object) -> None:
    field = Decimal(places=places, as_string=as_string)
    assert_matches_marshmallow(DecimalSerializationInliner(), field, value)


def test_boolean_serialization_inliner_falls_back_to_field() -> None:
    # Boolean has complex truthy/falsy logic, so the inliner falls back to
    # calling the field's native _serialize method.
    code = generate(BooleanSerializationInliner(), Boolean())
    assert "_serialize" in str(code)
    assert len(code.variables) == 1  # The field variable


@pytest.mark.parametrize("value", [None, True, False, "true", "no", 1, 0])
def test_boolean_serialization_matches_marshmallow(value: object) -> None:
    assert_matches_marshmallow(BooleanSerializationInliner(), Boolean(), value)


def test_raw_serialization_inliner_is_a_noop() -> None:
    # Raw does not override _serialize (it's the base Field identity), so the value must
    # pass through unchanged - not even a None-check.
    code = generate(RawSerializationInliner(), Raw())
    assert str(code) == ""
    # The generate() helper registers a field variable even for noop inliners
    assert len(code.variables) == 1


@pytest.mark.parametrize("value", [None, "hello", 42, {"nested": "dict"}, object()])
def test_raw_serialization_matches_marshmallow(value: object) -> None:
    assert_matches_marshmallow(RawSerializationInliner(), Raw(), value)


def test_enum_serialization_inliner_code_by_name() -> None:
    # by_value=False (the default): serializes the member's .name via a fresh String()
    code = generate(EnumSerializationInliner(), Enum(_Color))
    assert str(code) == ("if value is not None:\n    value = marshmallow.utils.ensure_text_type(value.name)")
    assert_compilable(code, {})


def test_enum_serialization_inliner_code_by_value_true() -> None:
    # by_value=True: serializes the member's .value via a fresh Raw() (identity)
    code = generate(EnumSerializationInliner(), Enum(_Color, by_value=True))
    assert str(code) == "if value is not None:\n    value = value.value"
    assert_compilable(code, {})


def test_enum_serialization_inliner_code_by_value_custom_field() -> None:
    # by_value=<a field>: delegates to that field's own _serialize
    field = Enum(_Number, by_value=Integer())
    code = generate(EnumSerializationInliner(), field)
    # Two variables: the enum field itself and the inner Integer field
    assert len(code.variables) == 2
    inner_fvar = [name for name, val in code.variables.items() if isinstance(val, Integer)][0]
    assert str(code) == (f"if value is not None:\n    value = {inner_fvar}._serialize(value.value, 'attr', obj)")
    assert_compilable(code, {})


@pytest.mark.parametrize("value", [None, _Color.RED, _Color.GREEN])
def test_enum_serialization_matches_marshmallow_by_name(value: object) -> None:
    assert_matches_marshmallow(EnumSerializationInliner(), Enum(_Color), value)


@pytest.mark.parametrize("value", [None, _Color.RED, _Color.GREEN])
def test_enum_serialization_matches_marshmallow_by_value(value: object) -> None:
    assert_matches_marshmallow(EnumSerializationInliner(), Enum(_Color, by_value=True), value)


@pytest.mark.parametrize("value", [None, _Number.ONE])
def test_enum_serialization_matches_marshmallow_by_value_custom_field(value: object) -> None:
    assert_matches_marshmallow(EnumSerializationInliner(), Enum(_Number, by_value=Integer()), value)


@pytest.mark.parametrize("value", ["not-an-enum-member", 42])
def test_enum_serialization_matches_marshmallow_invalid_value(value: object) -> None:
    # Both marshmallow and the inliner should raise AttributeError for invalid values
    # (values that are not enum members and don't have .name/.value attributes)
    field = Enum(_Color)

    # Check that marshmallow raises AttributeError
    with pytest.raises(AttributeError):
        field._serialize(value, "attr", object())

    # Check that the inliner also raises AttributeError
    with pytest.raises(AttributeError):
        run(EnumSerializationInliner(), field, value, obj=object())


@pytest.mark.parametrize(
    "inliner_cls,field_cls",
    [
        (DateTimeSerializationInliner, DateTime),
        (NaiveDateTimeSerializationInliner, NaiveDateTime),
        (AwareDateTimeSerializationInliner, AwareDateTime),
    ],
)
def test_datetime_serialization_inliner_code_default_iso_format(
    inliner_cls: type[Inliner], field_cls: type[Field]
) -> None:
    field = field_cls()
    code = generate(inliner_cls(), field)
    # Two variables: the field itself and the format_func
    assert len(code.variables) == 2
    format_func_var = [name for name, val in code.variables.items() if callable(val) and not isinstance(val, Field)][0]
    assert str(code) == f"if value is not None:\n    value = {format_func_var}(value)"
    assert_compilable(code, {})


@pytest.mark.parametrize(
    "inliner_cls,field_cls",
    [
        (DateTimeSerializationInliner, DateTime),
        (NaiveDateTimeSerializationInliner, NaiveDateTime),
        (AwareDateTimeSerializationInliner, AwareDateTime),
    ],
)
def test_datetime_serialization_inliner_code_custom_strftime_format(
    inliner_cls: type[Inliner], field_cls: type[Field]
) -> None:
    field = field_cls(format="%Y-%m")
    code = generate(inliner_cls(), field)
    assert str(code) == "if value is not None:\n    value = value.strftime('%Y-%m')"
    # The generate() helper registers a field variable even if not used
    assert len(code.variables) == 1
    assert_compilable(code, {})


@pytest.mark.parametrize(
    "inliner_cls,field_cls",
    [
        (DateTimeSerializationInliner, DateTime),
        (NaiveDateTimeSerializationInliner, NaiveDateTime),
        (AwareDateTimeSerializationInliner, AwareDateTime),
    ],
)
@pytest.mark.parametrize("format", ["iso", "rfc", "timestamp", "timestamp_ms", "%Y-%m-%d"])
@pytest.mark.parametrize("naive", [True, False])
def test_datetime_serialization_matches_marshmallow(
    inliner_cls: type[Inliner], field_cls: type[Field], format: str, naive: bool
) -> None:
    value = dt.datetime(2024, 1, 2, 3, 4, 5)
    if not naive:
        value = value.replace(tzinfo=dt.UTC)
    assert_matches_marshmallow(inliner_cls(), field_cls(format=format), value)
    assert_matches_marshmallow(inliner_cls(), field_cls(format=format), None)


def test_time_serialization_inliner_code() -> None:
    field = Time()
    code = generate(TimeSerializationInliner(), field)
    # Two variables: the field itself and the format_func
    assert len(code.variables) == 2
    format_func_var = [name for name, val in code.variables.items() if callable(val) and not isinstance(val, Field)][0]
    assert str(code) == f"if value is not None:\n    value = {format_func_var}(value)"
    assert_compilable(code, {})


@pytest.mark.parametrize("format", ["iso", "%H:%M"])
def test_time_serialization_matches_marshmallow(format: str) -> None:
    field = Time(format=format)
    assert_matches_marshmallow(TimeSerializationInliner(), field, dt.time(3, 4, 5))
    assert_matches_marshmallow(TimeSerializationInliner(), field, None)


def test_date_serialization_inliner_code() -> None:
    field = Date()
    code = generate(DateSerializationInliner(), field)
    # Two variables: the field itself and the format_func
    assert len(code.variables) == 2
    format_func_var = [name for name, val in code.variables.items() if callable(val) and not isinstance(val, Field)][0]
    assert str(code) == f"if value is not None:\n    value = {format_func_var}(value)"
    assert_compilable(code, {})


@pytest.mark.parametrize("format", ["iso", "%Y/%m/%d"])
def test_date_serialization_matches_marshmallow(format: str) -> None:
    field = Date(format=format)
    assert_matches_marshmallow(DateSerializationInliner(), field, dt.date(2024, 1, 2))
    assert_matches_marshmallow(DateSerializationInliner(), field, None)


def test_timedelta_serialization_inliner_code() -> None:
    from marshmallow_jit.compat import HAS_TIMEDELTA_SERIALIZATION_TYPE

    code = generate(TimeDeltaSerializationInliner(), TimeDelta())
    # Check that the generated code contains the expected elements
    code_str = str(code)
    assert "timedelta_to_microseconds" in code_str

    if HAS_TIMEDELTA_SERIALIZATION_TYPE:
        # Marshmallow 3: Uses base_unit and integer division
        assert "base_unit" in code_str
        assert "// unit" in code_str  # Integer division for int serialization_type
    else:
        # Marshmallow 4: Uses direct microseconds division
        assert "microseconds" in code_str
        assert "/ " in code_str  # Float division

    # The generate() helper registers a field variable
    # In marshmallow 4, we also register the unit variable
    assert len(code.variables) >= 1
    assert_compilable(code, {})


@pytest.mark.parametrize("precision", ["weeks", "days", "hours", "minutes", "seconds", "milliseconds", "microseconds"])
@pytest.mark.parametrize("value", [None, dt.timedelta(days=1, hours=2, microseconds=123)])
def test_timedelta_serialization_matches_marshmallow(precision: str, value: object) -> None:
    assert_matches_marshmallow(TimeDeltaSerializationInliner(), TimeDelta(precision=precision), value)


@pytest.mark.parametrize(
    "inliner_cls,field_cls",
    [
        (IPSerializationInliner, IP),
        (IPv4SerializationInliner, IPv4),
        (IPv6SerializationInliner, IPv6),
    ],
)
def test_ip_serialization_inliner_code(inliner_cls: type[Inliner], field_cls: type[Field]) -> None:
    code = generate(inliner_cls(), field_cls())
    assert str(code) == "if value is not None:\n    value = value.compressed"
    # The generate() helper registers a field variable
    assert len(code.variables) == 1
    assert_compilable(code, {})


@pytest.mark.parametrize("inliner_cls,field_cls", [(IPSerializationInliner, IP), (IPv6SerializationInliner, IPv6)])
def test_ip_serialization_inliner_code_exploded(inliner_cls: type[Inliner], field_cls: type[Field]) -> None:
    code = generate(inliner_cls(), field_cls(exploded=True))
    assert str(code) == "if value is not None:\n    value = value.exploded"
    # The generate() helper registers a field variable
    assert len(code.variables) == 1
    assert_compilable(code, {})


@pytest.mark.parametrize(
    "inliner_cls,field_cls,value",
    [
        (IPSerializationInliner, IP, ipaddress.ip_address("127.0.0.1")),
        (IPv4SerializationInliner, IPv4, ipaddress.IPv4Address("127.0.0.1")),
        (IPv6SerializationInliner, IPv6, ipaddress.IPv6Address("::1")),
    ],
)
@pytest.mark.parametrize("exploded", [False, True])
def test_ip_serialization_matches_marshmallow(
    inliner_cls: type[Inliner], field_cls: type[Field], value: object, exploded: bool
) -> None:
    field = field_cls(exploded=exploded)
    assert_matches_marshmallow(inliner_cls(), field, value)
    assert_matches_marshmallow(inliner_cls(), field, None)


@pytest.mark.parametrize(
    "inliner_cls,field_cls,value",
    [
        (IPInterfaceSerializationInliner, IPInterface, ipaddress.ip_interface("192.168.0.2/24")),
        (IPv4InterfaceSerializationInliner, IPv4Interface, ipaddress.IPv4Interface("192.168.0.2/24")),
        (IPv6InterfaceSerializationInliner, IPv6Interface, ipaddress.IPv6Interface("::1/128")),
    ],
)
@pytest.mark.parametrize("exploded", [False, True])
def test_ip_interface_serialization_matches_marshmallow(
    inliner_cls: type[Inliner], field_cls: type[Field], value: object, exploded: bool
) -> None:
    field = field_cls(exploded=exploded)
    assert_matches_marshmallow(inliner_cls(), field, value)
    assert_matches_marshmallow(inliner_cls(), field, None)
