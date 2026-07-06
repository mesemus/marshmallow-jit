# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT

"""Shared field matrices for serialization and deserialization parity tests.

This module contains FIELD_SERIALIZATION_MATRIX and FIELD_DESERIALIZATION_MATRIX,
which are used to test that JIT-compiled schema operations produce identical results
to plain marshmallow operations across a wide variety of field types and values.

Any test function that declares `field_factory` and `value` parameters is automatically
parametrized (via `pytest_generate_tests` below) with one case per field configuration
in the appropriate matrix, plus `None` and the type-appropriate "invalid" values for each.
"""

import datetime as dt
import decimal
import enum
import ipaddress
import uuid
from collections.abc import Callable, Generator, Mapping
from typing import Any, override

import pytest
from marshmallow import Schema, post_dump, post_load, pre_load
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
    Tuple,
    Url,
)

from marshmallow_jit.compat import HAS_TIMEDELTA_SERIALIZATION_TYPE, MAField

# Import marshmallow-utils fields if available
try:
    from marshmallow_utils.fields import (  # type: ignore[unresolved-import]
        URL as UtilsURL,
    )
    from marshmallow_utils.fields import (  # type: ignore[unresolved-import]
        EDTFDateString,
        EDTFDateTimeString,
        EDTFLevel2DateString,
        IdentifierSet,
        IdentifierValueSet,
        ISODateString,
        ISOLangString,
        SanitizedHTML,
        SanitizedUnicode,
        StrippedHTML,
        TrimmedString,
        TZDateTime,
    )
    from marshmallow_utils.fields.nestedattr import (
        NestedAttribute as MarshmallowUtilsNestedAttribute,  # type: ignore[unresolved-import]
    )

    MARSHMALLOW_UTILS_AVAILABLE = True
except ImportError:
    MARSHMALLOW_UTILS_AVAILABLE = False

    # Define dummy classes for type checking when marshmallow-utils is not installed
    class EDTFDateString(Str):
        pass

    class EDTFDateTimeString(Str):
        pass

    class EDTFLevel2DateString(Str):
        pass

    class ISODateString(Date):
        pass

    class ISOLangString(Str):
        pass

    class IdentifierSet(List):  # type: ignore[misc,type-arg]
        pass

    class IdentifierValueSet(List):  # type: ignore[misc,type-arg]
        pass

    class SanitizedHTML(Str):
        pass

    class SanitizedUnicode(Str):
        pass

    class StrippedHTML(Str):
        pass

    class TrimmedString(Str):
        pass

    class UtilsURL(Str):
        pass

    class TZDateTime(DateTime):
        pass


class UnstringifiableValue:
    """Raises on str() so tests can check that plain marshmallow and the JIT path fail identically."""

    @override
    def __str__(self) -> str:
        raise RuntimeError("cannot stringify this value")


class _ExampleEnum(enum.Enum):
    RED = "red"
    GREEN = "green"


class _ExampleNestedSchema(Schema):
    id = Integer()
    name = Str()


class _ExampleNestedSchemaWithHooks(Schema):
    """Nested schema with pre_dump/post_dump hooks to test the optimization path.

    The hooks modify the data to ensure they are actually being called during serialization.
    Note: pre_dump runs before serialization (on raw data), post_dump runs after (on serialized dict).
    """

    id = Integer()
    name = Str()

    @post_dump
    def _add_post_hook_marker(self, data: dict[str, object], **kwargs: object) -> dict[str, object]:
        # Hook that adds a marker to verify it's being called
        # This runs AFTER serialization, so the marker will appear in the output
        if isinstance(data, dict):
            data["_hook_was_called"] = True
        return data


class _ExampleNestedSchemaWithPreLoad(Schema):
    """Nested schema with pre_load hook to test deserialization with pre-processing."""

    id = Integer()
    name = Str()

    @pre_load
    def _add_pre_load_marker(self, data: dict[str, object], **kwargs: object) -> dict[str, object]:
        # Hook that adds a marker before deserialization
        # This runs BEFORE deserialization, so we can transform the input
        if isinstance(data, dict):
            data["_pre_load_called"] = True
        return data


class _ExampleNestedSchemaWithPostLoad(Schema):
    """Nested schema with post_load hook to test deserialization with post-processing."""

    id = Integer()
    name = Str()

    @post_load
    def _add_post_load_marker(self, data: dict[str, object], **kwargs: object) -> dict[str, object]:
        # Hook that adds a marker after deserialization
        # This runs AFTER deserialization, so the marker appears in the final result
        if isinstance(data, dict):
            data["_post_load_called"] = True
        return data


class _CustomIntegerField(Integer):
    """Integer field with overridden _format_num to test fallback behavior."""

    @override
    def _format_num(self, value: Any) -> int:
        # Custom formatting: multiply by 2
        return int(value) * 2


class _CustomFloatField(Float):
    """Float field with overridden _format_num to test fallback behavior."""

    @override
    def _format_num(self, value: Any) -> float:
        # Custom formatting: multiply by 3
        return float(value) * 3


class _CustomDecimalField(Decimal):
    """Decimal field with overridden _format_num to test fallback behavior."""

    @override
    def _format_num(self, value: Any) -> decimal.Decimal:
        # Custom formatting: multiply by 5
        from decimal import Decimal as D

        return D(value) * 5


class _CustomIPField(IP):
    """IP field with overridden _deserialize to test fallback behavior."""

    @override
    def _deserialize(  # ty: ignore[invalid-method-override]
        self, value: Any, attr: str | None, data: Mapping[str, Any] | None, **kwargs: Any
    ) -> ipaddress.IPv4Address | ipaddress.IPv6Address | str | None:
        # Custom deserialization: prepend "custom-" to the string representation
        result = super()._deserialize(value, attr, data, **kwargs)
        if result is not None:
            return f"custom-{result}"
        return result


class _CustomIPv4Field(IPv4):
    """IPv4 field with overridden _deserialize to test fallback behavior."""

    @override
    def _deserialize(  # ty: ignore[invalid-method-override]
        self, value: Any, attr: str | None, data: Mapping[str, Any] | None, **kwargs: Any
    ) -> ipaddress.IPv4Address | str | None:
        # Custom deserialization: wrap in brackets
        result = super()._deserialize(value, attr, data, **kwargs)
        if result is not None:
            return f"[{result}]"
        return result


class _CustomIPInterfaceField(IPInterface):
    """IPInterface field with overridden _deserialize to test fallback behavior."""

    @override
    def _deserialize(  # ty: ignore[invalid-method-override]
        self, value: Any, attr: str | None, data: Mapping[str, Any] | None, **kwargs: Any
    ) -> ipaddress.IPv4Interface | ipaddress.IPv6Interface | str | None:
        # Custom deserialization: append "/custom" to the string representation
        result = super()._deserialize(value, attr, data, **kwargs)
        if result is not None:
            return f"{result}/custom"
        return result


class _CustomStrField(Str):
    """Str field with overridden _deserialize to test fallback behavior."""

    @override
    def _deserialize(self, value: Any, attr: str | None, data: Mapping[str, Any] | None, **kwargs: Any) -> str | None:  # type: ignore[override]
        # Custom deserialization: prepend "str-" to the result
        result = super()._deserialize(value, attr, data, **kwargs)
        if result is not None:
            return f"str-{result}"
        return result


class _CustomUUIDField(UUID):
    """UUID field with overridden _deserialize to test fallback behavior."""

    @override
    def _deserialize(  # ty: ignore[invalid-method-override]
        self, value: Any, attr: str | None, data: Mapping[str, Any] | None, **kwargs: Any
    ) -> uuid.UUID | str | None:
        # Custom deserialization: convert UUID to string with prefix
        result = super()._deserialize(value, attr, data, **kwargs)
        if result is not None:
            return f"uuid-{result}"
        return result


class _ConstantUUIDField(UUID):
    """UUID field with overridden _validated that always returns a constant UUID."""

    CONSTANT_UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")

    @override
    def _validated(self, value: object) -> uuid.UUID:
        # Always return the same constant UUID regardless of input
        return self.CONSTANT_UUID


class _CustomDateTimeField(DateTime):
    """DateTime field with overridden _deserialize to test fallback behavior."""

    @override
    def _deserialize(  # ty: ignore[invalid-method-override]
        self, value: Any, attr: str | None, data: Mapping[str, Any] | None, **kwargs: Any
    ) -> dt.datetime | str | None:
        # Custom deserialization: add a note to the isoformat string
        result = super()._deserialize(value, attr, data, **kwargs)
        if result is not None:
            return f"{result.isoformat()}-custom"
        return result


class _CustomTimeDeltaField(TimeDelta):
    """TimeDelta field with overridden _deserialize to test fallback behavior."""

    @override
    def _deserialize(
        self, value: Any, attr: str | None, data: Mapping[str, Any] | None, **kwargs: Any
    ) -> dt.timedelta | None:  # type: ignore[override]
        # Custom deserialization: double the timedelta
        result = super()._deserialize(value, attr, data, **kwargs)
        if result is not None:
            return result * 2
        return result


class _UnrecognizedField(Field):
    """A field type with no registered Inliner (subclasses Field directly, not Raw/Integer/etc.).

    Simulates a third-party field marshmallow-jit doesn't know about. Used as a List's inner
    field to check that ListSerializationInliner/ListDeserializationInliner fall back to calling
    the inner field's own serialize()/deserialize() directly, per the "Custom Field Types" pitfall
    documented in CLAUDE.md.
    """

    @override
    def _serialize(self, value: Any, attr: str | None, obj: Any, **kwargs: Any) -> Any:
        return f"unrecognized:{value}"

    @override
    def _deserialize(self, value: Any, attr: str | None, data: Mapping[str, Any] | None, **kwargs: Any) -> Any:
        return f"unrecognized:{value}"


# Each entry: (field id, field factory, values to try in addition to `None`).
# Values mix well-typed ("valid") inputs with wrong-typed ("invalid") ones that are expected
# to raise - both are asserted to behave identically between plain marshmallow and the JIT path.
FIELD_MATRIX: list[tuple[str, Callable[[], Field], list[Any]]] = [
    ("str", Str, ["hello", "", b"world", b"\xff\xfe", 42, UnstringifiableValue()]),
    ("url", Url, ["https://example.com", "not a url at all", b"\xff\xfe"]),
    ("email", Email, ["a@b.com", "not-an-email", b"\xff\xfe"]),
    ("uuid", UUID, [uuid.uuid4(), uuid.UUID(int=0), "not-a-uuid-object", UnstringifiableValue()]),
    ("integer", lambda: Integer(), [0, 42, -7, "42", "not-a-number", 3.9, True]),
    ("integer_strict", lambda: Integer(strict=True), [0, 42, -7, "42", "not-a-number", 3.9, True]),
    ("integer_as_string", lambda: Integer(as_string=True), [0, 42, "42", "not-a-number"]),
    ("float", lambda: Float(), [0.0, 3.14, "2.5", "not-a-number"]),
    ("float_as_string", lambda: Float(as_string=True), [3.14, "not-a-number"]),
    ("decimal", lambda: Decimal(), ["1.23", decimal.Decimal("5"), 42, "not-a-number"]),
    ("decimal_places", lambda: Decimal(places=2), ["1.2345", 42, "not-a-number"]),
    ("decimal_as_string", lambda: Decimal(as_string=True), ["1.23", "not-a-number"]),
    # allow_nan=True with a non-NaN value: the NaN-specific normalization branch can't be
    # covered here because NaN != NaN makes it incompatible with the shared equality-based
    # matrix comparison - see test_decimal_allow_nan_deserialization below instead.
    ("decimal_allow_nan", lambda: Decimal(allow_nan=True), ["1.5", "not-a-number"]),
    ("boolean", lambda: Boolean(), [True, False, "yes", 0, "banana", UnstringifiableValue()]),
    ("datetime_iso", lambda: DateTime(), [dt.datetime(2024, 1, 2, 3, 4, 5), "not-a-date", 123]),
    (
        "datetime_rfc",
        lambda: DateTime(format="rfc"),
        [dt.datetime(2024, 1, 2, 3, 4, 5, tzinfo=dt.UTC), "not-a-date", 123],
    ),
    ("datetime_timestamp", lambda: DateTime(format="timestamp"), [dt.datetime(2024, 1, 2), "not-a-date"]),
    ("datetime_timestamp_ms", lambda: DateTime(format="timestamp_ms"), [dt.datetime(2024, 1, 2), "not-a-date"]),
    ("datetime_custom_format", lambda: DateTime(format="%Y-%m"), [dt.datetime(2024, 1, 2), "not-a-date"]),
    ("naive_datetime", lambda: NaiveDateTime(), [dt.datetime(2024, 1, 2), "not-a-date"]),
    (
        "naive_datetime_tz",
        lambda: NaiveDateTime(timezone=dt.timezone(dt.timedelta(hours=5))),
        [dt.datetime(2024, 1, 2, tzinfo=dt.UTC), "not-a-date"],
    ),
    ("aware_datetime", lambda: AwareDateTime(), [dt.datetime(2024, 1, 2, tzinfo=dt.UTC), "not-a-date"]),
    (
        "aware_datetime_default_tz",
        lambda: AwareDateTime(default_timezone=dt.timezone(dt.timedelta(hours=-5))),
        [dt.datetime(2024, 1, 2), "not-a-date"],
    ),
    ("time_iso", lambda: Time(), [dt.time(3, 4, 5), "not-a-time", 123]),
    ("time_custom_format", lambda: Time(format="%H:%M"), [dt.time(3, 4, 5), "not-a-time"]),
    ("date_iso", lambda: Date(), [dt.date(2024, 1, 2), "not-a-date", 123]),
    ("date_custom_format", lambda: Date(format="%Y/%m/%d"), [dt.date(2024, 1, 2), "not-a-date"]),
    ("timedelta_seconds", lambda: TimeDelta(), [dt.timedelta(days=1, seconds=2), "not-a-timedelta", 5]),
    ("timedelta_days", lambda: TimeDelta(precision="days"), [dt.timedelta(days=3), "not-a-timedelta"]),
    # In marshmallow 3, TimeDelta has serialization_type parameter
    # In marshmallow 4, TimeDelta always uses float serialization
    *(
        [
            (
                "timedelta_float",
                lambda: TimeDelta(serialization_type=float),
                [dt.timedelta(hours=1, minutes=30), "not-a-timedelta", 1.5],
            ),
            (
                "custom_timedelta",
                lambda: TimeDelta(precision="hours", serialization_type=int),
                [dt.timedelta(hours=3, minutes=15), "not-a-timedelta", 3],
            ),
        ]
        if HAS_TIMEDELTA_SERIALIZATION_TYPE
        else [
            (
                "timedelta_float",
                lambda: TimeDelta(),
                [dt.timedelta(hours=1, minutes=30), "not-a-timedelta", 1.5],
            ),
            (
                "custom_timedelta",
                lambda: TimeDelta(precision="hours"),
                [dt.timedelta(hours=3, minutes=15), "not-a-timedelta", 3.25],
            ),
        ]
    ),
    (
        "ip",
        lambda: IP(),
        [ipaddress.ip_address("127.0.0.1"), ipaddress.ip_address("::1"), "not-an-ip", 123],
    ),
    ("ip_exploded", lambda: IP(exploded=True), [ipaddress.ip_address("::1"), "not-an-ip"]),
    ("ipv4", lambda: IPv4(), [ipaddress.IPv4Address("127.0.0.1"), "not-an-ip"]),
    ("ipv6", lambda: IPv6(), [ipaddress.IPv6Address("::1"), "not-an-ip"]),
    ("ip_interface", lambda: IPInterface(), [ipaddress.ip_interface("192.168.0.2/24"), "not-an-interface", 123]),
    (
        "ip_interface_exploded",
        lambda: IPInterface(exploded=True),
        [ipaddress.ip_interface("::1/128"), "not-an-interface"],
    ),
    ("ipv4_interface", lambda: IPv4Interface(), [ipaddress.IPv4Interface("192.168.0.2/24"), "not-an-interface"]),
    ("ipv6_interface", lambda: IPv6Interface(), [ipaddress.IPv6Interface("::1/128"), "not-an-interface"]),
    # Custom IP fields with overridden _deserialize - test fallback to field._deserialize()
    ("custom_ip", lambda: _CustomIPField(), [ipaddress.ip_address("127.0.0.1"), "not-an-ip"]),
    ("custom_ipv4", lambda: _CustomIPv4Field(), [ipaddress.IPv4Address("127.0.0.1"), "not-an-ip"]),
    (
        "custom_ip_interface",
        lambda: _CustomIPInterfaceField(),
        [ipaddress.ip_interface("192.168.0.2/24"), "not-an-interface"],
    ),
    # Custom fields with overridden _deserialize - test fallback to field._deserialize()
    ("custom_str", lambda: _CustomStrField(), ["hello", "world", b"bytes"]),
    ("custom_uuid", lambda: _CustomUUIDField(), [uuid.uuid4(), "not-a-uuid"]),
    ("constant_uuid", lambda: _ConstantUUIDField(), [uuid.uuid4(), "any-string", "not-a-uuid"]),
    ("custom_datetime", lambda: _CustomDateTimeField(), [dt.datetime(2024, 1, 2), "not-a-date"]),
    ("custom_timedelta", lambda: _CustomTimeDeltaField(), [dt.timedelta(days=1), "not-a-timedelta", 5]),
    # Fields with no builtin Inliner - these go through the generic fallback path
    # (SchemaSerializer.generate_fallback), which just calls the field's own
    # Field.serialize() directly. They're included here as a regression check that the
    # fallback path itself behaves identically to plain marshmallow, not because each one
    # exercises an interesting Inliner-specific code path (there is none yet).
    ("raw", Raw, ["hello", 42, {"nested": "dict"}, UnstringifiableValue()]),
    ("constant", lambda: Constant(42), ["ignored-value", 999]),
    ("method", Method, ["ignored", 5]),
    ("function", lambda: Function(serialize=lambda obj: "function-called"), ["ignored", 5]),
    # Function defaults to dump_only=True, so the entry above never exercises
    # FunctionDeserializationInliner at all. Providing only deserialize= makes marshmallow set
    # load_only=True automatically (Function.__init__ derives dump_only/load_only from which of
    # serialize/deserialize are given), so this is deserialize-only and safely avoids dumping.
    #
    # Note: FunctionDeserializationInliner's other branch (no deserialize_func - passthrough) and
    # FunctionSerializationInliner's "no serialize_func" branch are NOT covered here: both would
    # require a Function with no serialize_func that still participates in dump, which currently
    # exposes a real bug (see conversation/PR notes) rather than a coverage gap - marshmallow-jit's
    # FunctionSerializationInliner treats a missing serialize_func as "omit the field", but plain
    # marshmallow's Function._serialize unconditionally calls it and raises TypeError instead.
    ("function_loadable", lambda: Function(deserialize=lambda v: f"loaded:{v}"), ["ignored", 5]),
    ("enum", lambda: Enum(_ExampleEnum), [_ExampleEnum.RED, "not-an-enum-member"]),
    # by_value=True and by_value=<custom field> deserialization branches aren't exercised by the
    # default (by_value=False) case above.
    ("enum_by_value", lambda: Enum(_ExampleEnum, by_value=True), [_ExampleEnum.RED, "not-an-enum-member"]),
    ("enum_by_custom_field", lambda: Enum(_ExampleEnum, by_value=Str()), [_ExampleEnum.RED, "not-an-enum-member"]),
    ("dict", lambda: Dict(keys=Str(), values=Integer()), [{"x": 1, "y": 2}, "not-a-dict"]),
    # Dict configurations below each exercise one DictSerializationInliner/DictDeserializationInliner
    # branch not reached by the "happy path" entry above (both keys and values have registered,
    # non-noop Inliners there).
    # No key_field at all - keys are passed through unchanged.
    ("dict_no_keys", lambda: Dict(values=Integer()), [{"a": 1, "b": 2}, "not-a-dict"]),
    # No value_field at all - values are passed through unchanged.
    ("dict_no_values", lambda: Dict(keys=Str()), [{"a": 1, "b": 2}, "not-a-dict"]),
    # Neither key_field nor value_field - the dict is used as-is (no per-item processing at all).
    ("dict_bare", Dict, [{"a": 1, "b": 2}, "not-a-dict"]),
    # Raw key/value: Raw's serialization Inliner is a pure passthrough (is_noop=True), exercising
    # the "no transformation needed" fast paths for both keys and values.
    ("dict_raw_key", lambda: Dict(keys=Raw(), values=Integer()), [{"a": 1, "b": 2}, "not-a-dict"]),
    ("dict_raw_value", lambda: Dict(keys=Str(), values=Raw()), [{"a": 1, "b": "x"}, "not-a-dict"]),
    # Keys/values with no registered Inliner at all: exercises the fallback path that calls the
    # key/value field's own serialize()/deserialize() directly, per "Custom Field Types" in
    # CLAUDE.md - the Dict analogue of list_of_unrecognized_field above.
    (
        "dict_unrecognized_key",
        lambda: Dict(keys=_UnrecognizedField(), values=Integer()),
        [{"a": 1, "b": 2}, "not-a-dict"],
    ),
    (
        "dict_unrecognized_value",
        lambda: Dict(keys=Str(), values=_UnrecognizedField()),
        [{"a": 1, "b": "x"}, "not-a-dict"],
    ),
    # A dict with both a valid and an invalid key (per key_field) in the same input: checks that
    # per-key deserialization failures are collected independently, without discarding the entries
    # that succeeded (marshmallow's partial-failure Mapping.deserialize behavior).
    (
        "dict_mixed_key_validity",
        lambda: Dict(keys=Integer(), values=Str()),
        [{"5": "ok", "bad": "still-a-string"}, "not-a-dict"],
    ),
    ("list", lambda: List(Str()), [["a", "b", "c"], 42]),
    ("list_of_lists", lambda: List(List(Str())), [[["a", "b"], ["c"]], 42]),
    # List of Raw: Raw's serialization Inliner is a pure passthrough (is_noop=True), exercising
    # ListSerializationInliner's "no transformation needed, just append" fast path.
    ("list_of_raw", lambda: List(Raw()), [["a", 1, {"x": 2}], 42]),
    # List of a field type with no registered Inliner at all: exercises the fallback path where
    # List(De)SerializationInliner calls the inner field's own serialize()/deserialize() directly,
    # instead of an inlined transformation - the same fallback guarantee as the top-level
    # "Fields with no builtin Inliner" cases above, but for a List's *inner* field.
    ("list_of_unrecognized_field", lambda: List(_UnrecognizedField()), [["a", "b"], 42]),
    ("tuple", lambda: Tuple((Str(), Integer())), [("hello", 42), "not-a-tuple"]),
    ("nested", lambda: Nested(_ExampleNestedSchema), [{"id": 1, "name": "foo"}, {"id": 2, "name": "bar"}]),
    (
        "nested_with_hooks",
        lambda: Nested(_ExampleNestedSchemaWithHooks),
        [{"id": 1, "name": "foo"}, {"id": 2, "name": "bar"}],
    ),
    (
        "nested_with_pre_load",
        lambda: Nested(_ExampleNestedSchemaWithPreLoad),
        [{"id": 1, "name": "foo"}, {"id": 2, "name": "bar"}],
    ),
    (
        "nested_with_post_load",
        lambda: Nested(_ExampleNestedSchemaWithPostLoad),
        [{"id": 1, "name": "foo"}, {"id": 2, "name": "bar"}],
    ),
    # Custom fields with overridden _format_num - test fallback to field.serialize()
    ("custom_integer", lambda: _CustomIntegerField(), [10, 42, -7, "42", "not-a-number", 3.9]),
    ("custom_float", lambda: _CustomFloatField(), [30.0, 126.0, -21.0, "42.0", "not-a-number"]),
    (
        "custom_decimal",
        lambda: _CustomDecimalField(),
        [decimal.Decimal("5"), decimal.Decimal("21"), decimal.Decimal("-3.5"), "42.5", "not-a-number"],
    ),
]


# Special test for NestedAttribute - requires object with attribute access
class _NestedAttrTestObj(dict[str, Any]):
    """Object that inherits from dict but also has attributes."""

    def __init__(self, val: object) -> None:
        super().__init__()
        self.a = {"blah": val}


# Add marshmallow-utils fields if available
if MARSHMALLOW_UTILS_AVAILABLE:
    FIELD_MATRIX.extend(
        [
            # String-based utils fields (inherit from String, use Str inliner)
            (
                "edtf_date_string",
                lambda: EDTFDateString(),
                ["2023-01-01", "2023-XX-01", "not-a-date"],
            ),
            (
                "edtf_datetime_string",
                lambda: EDTFDateTimeString(),
                ["2023-01-01T12:00:00", "2023-XX-01T12:00:00", "not-a-datetime"],
            ),
            (
                "edtf_level2_date_string",
                lambda: EDTFLevel2DateString(),
                ["2023-01-01", "2023-01", "not-a-date"],
            ),
            (
                "iso_date_string",
                lambda: ISODateString(),
                [dt.date(2023, 1, 1), "2023-01-01", "not-a-date"],
            ),
            (
                "isolang_string",
                lambda: ISOLangString(),
                ["en", "en-US", "not-a-language"],
            ),
            (
                "sanitized_html",
                lambda: SanitizedHTML(),
                ["<p>Hello</p>", "<script>alert('x')</script>", 42],
            ),
            (
                "sanitized_unicode",
                lambda: SanitizedUnicode(),
                ["hello", "<b>bold</b>", 42],
            ),
            (
                "stripped_html",
                lambda: StrippedHTML(),
                ["<p>Hello</p>", "<script>alert('x')</script>", 42],
            ),
            (
                "trimmed_string",
                lambda: TrimmedString(),
                ["  hello  ", "\tworld\n", 42],
            ),
            (
                "utils_url",
                lambda: UtilsURL(),
                ["https://example.com", "not-a-url", 42],
            ),
            (
                "tz_datetime",
                lambda: TZDateTime(),
                [dt.datetime(2023, 1, 1, 12, 0, tzinfo=dt.UTC), "not-a-datetime", 123],
            ),
            (
                "identifier_set",
                lambda: IdentifierSet(Str()),
                [["id1", "id2"], [1, 2], "not-a-list"],
            ),
            (
                "identifier_value_set",
                lambda: IdentifierValueSet(Str()),
                [["v1", "v2"], ["a", "b"], "not-a-list"],
            ),
            # NestedAttribute - requires special handling with InstanceAccessor
            # Test with an object that has nested attribute access
            (
                "nested_attribute",
                lambda: MarshmallowUtilsNestedAttribute(type("_InnerSchema", (Schema,), {"blah": Str()})()),
                [_NestedAttrTestObj("test_value"), _NestedAttrTestObj(123), "not-an-obj"],
            ),
        ]
    )


# For now, serialization and deserialization use the same field matrix.
# In the future, deserialization-specific fields/values can be added separately.
FIELD_SERIALIZATION_MATRIX = FIELD_MATRIX
FIELD_DESERIALIZATION_MATRIX = FIELD_MATRIX


@pytest.fixture(scope="session")
def field_matrix() -> list[tuple[str, Callable[[], Field], list[Any]]]:
    """The raw (field id, field factory, values) table, for tests that want to inspect it directly."""
    return FIELD_MATRIX


@pytest.fixture(scope="session")
def field_serialization_matrix() -> list[tuple[str, Callable[[], Field], list[Any]]]:
    """The serialization field matrix."""
    return FIELD_SERIALIZATION_MATRIX


@pytest.fixture(scope="session")
def field_deserialization_matrix() -> list[tuple[str, Callable[[], Field], list[Any]]]:
    """The deserialization field matrix."""
    return FIELD_DESERIALIZATION_MATRIX


def _iter_field_matrix_cases(
    matrix: list[tuple[str, Callable[[], Field], list[Any]]],
) -> Generator[Any]:
    for field_id, field_factory, values in matrix:
        for idx, value in enumerate([None, *values]):
            yield pytest.param(field_factory, value, id=f"{field_id}-{idx}")


def _iter_field_serialization_matrix_cases() -> Generator[Any]:
    yield from _iter_field_matrix_cases(FIELD_SERIALIZATION_MATRIX)


def _iter_field_deserialization_matrix_cases() -> Generator[Any]:
    yield from _iter_field_matrix_cases(FIELD_DESERIALIZATION_MATRIX)


# Field.__init__ has several kwargs that influence *serialization* rather than just validation
# or deserialization:
#   - dump_default: used (instead of omitting the field) when the attribute/key is missing.
#     May be a plain value or a zero-arg callable.
#   - attribute: the internal attribute/key read from the source object, if different from the
#     field's name on the schema.
#   - data_key: the external key written to the output dict, if different from the field's name.
# None of required/allow_none/validate/load_only/load_default/error_messages/metadata affect
# dump() - they only matter for deserialize()/validation - so they are intentionally excluded.
#
# Each case describes how to configure the field and how to build the source object (as kwargs
# for the test's object-builder), reusing the first "valid" value already listed for the field
# in FIELD_MATRIX as a type-appropriate stand-in value.
SERIALIZATION_KWARGS_CASES = [
    "no_dump_default_missing",
    "dump_default_missing",
    "callable_dump_default_missing",
    "attribute_alias_present",
    "attribute_alias_missing",
    "data_key_present",
]

# For deserialization, we test load-relevant kwargs:
#   - load_default: used (instead of omitting the field) when the key is missing in input data.
#     May be a plain value or a zero-arg callable.
#   - attribute: not typically used for deserialization (reads from input dict by data_key/name)
#   - data_key: the input key to read from, if different from the field's name on the schema.
# Note: We don't test 'attribute' for deserialization since it only affects serialization.
DESERIALIZATION_KWARGS_CASES = [
    "no_load_default_missing",
    "load_default_missing",
    "callable_load_default_missing",
    "data_key_present",
]

# For partial loading tests, we test various partial scenarios with missing fields:
PARTIAL_DESERIALIZATION_CASES = [
    "partial_false",
    "partial_true",
    "partial_set_a",
    "partial_set_b",
]


def configure_field(field: MAField, base_value: Any, kwargs_case: str) -> None:
    """Mutates `field` in place to exercise one dump_default/attribute/data_key scenario."""
    if kwargs_case == "dump_default_missing":
        field.dump_default = base_value
    elif kwargs_case == "callable_dump_default_missing":
        field.dump_default = lambda: base_value
    elif kwargs_case in ("attribute_alias_present", "attribute_alias_missing"):
        field.attribute = "internal"
    elif kwargs_case == "data_key_present":
        field.data_key = "external"


def configure_deserialization_field(field: MAField, base_value: Any, kwargs_case: str) -> None:
    """Mutates `field` in place to exercise one load_default/data_key scenario."""
    if kwargs_case == "load_default_missing":
        field.load_default = base_value
    elif kwargs_case == "callable_load_default_missing":
        field.load_default = lambda: base_value
    elif kwargs_case == "data_key_present":
        field.data_key = "external"


def build_source_kwargs(base_value: Any, kwargs_case: str) -> dict[str, Any]:
    """The key(s)/value(s) that should be present on the dumped object/dict for this case."""
    if kwargs_case in ("no_dump_default_missing", "dump_default_missing", "callable_dump_default_missing"):
        return {}
    if kwargs_case == "attribute_alias_present":
        return {"internal": base_value}
    if kwargs_case == "attribute_alias_missing":
        return {}
    if kwargs_case == "data_key_present":
        return {"a": base_value}
    raise ValueError(f"Unknown kwargs_case: {kwargs_case}")


def build_deserialization_source_kwargs(base_value: Any, kwargs_case: str) -> dict[str, Any]:
    """The key(s)/value(s) that should be present on the loaded dict for this case."""
    if kwargs_case in ("no_load_default_missing", "load_default_missing", "callable_load_default_missing"):
        return {}
    if kwargs_case == "data_key_present":
        return {"external": base_value}
    raise ValueError(f"Unknown kwargs_case: {kwargs_case}")


def _iter_field_kwargs_cases(
    matrix: list[tuple[str, Callable[[], Field], list[Any]]], kwargs_cases: list[str]
) -> Generator[Any]:
    for field_id, field_factory, values in matrix:
        base_value = values[0]
        for kwargs_case in kwargs_cases:
            yield pytest.param(field_factory, base_value, kwargs_case, id=f"{field_id}-{kwargs_case}")


def _iter_field_serialization_kwargs_cases() -> Generator[Any]:
    yield from _iter_field_kwargs_cases(FIELD_SERIALIZATION_MATRIX, SERIALIZATION_KWARGS_CASES)


def _iter_field_deserialization_kwargs_cases() -> Generator[Any]:
    yield from _iter_field_kwargs_cases(FIELD_DESERIALIZATION_MATRIX, DESERIALIZATION_KWARGS_CASES)


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Auto-parametrize tests declaring `field_factory`/`value`, or `field_factory`/`base_value`/`kwargs_case`."""
    # Get the module file path, defaulting to empty string if unavailable
    module_file = getattr(metafunc.module, "__file__", None) or ""
    is_deserialization_test = "deserialization" in str(module_file).lower()

    # Serialization tests
    if "field_factory" in metafunc.fixturenames and "value" in metafunc.fixturenames:
        # Check if we're in a serialization test context
        if not is_deserialization_test:
            metafunc.parametrize("field_factory,value", list(_iter_field_serialization_matrix_cases()))
        else:
            metafunc.parametrize("field_factory,value", list(_iter_field_deserialization_matrix_cases()))

    # Kwargs tests
    if (
        "field_factory" in metafunc.fixturenames
        and "base_value" in metafunc.fixturenames
        and "kwargs_case" in metafunc.fixturenames
    ):
        if not is_deserialization_test:
            metafunc.parametrize("field_factory,base_value,kwargs_case", list(_iter_field_serialization_kwargs_cases()))
        else:
            metafunc.parametrize(
                "field_factory,base_value,kwargs_case", list(_iter_field_deserialization_kwargs_cases())
            )
