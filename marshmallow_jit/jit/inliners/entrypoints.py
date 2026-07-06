# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Factory for builtin serialization/deserialization inliners.

Maps marshmallow field types to their corresponding Inliner implementations,
maintaining specificity ordering for proper inheritance handling.
"""

from typing import ClassVar, override

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

from marshmallow_jit.compat import MAField as Field

from marshmallow_jit.jit.registry import Factory
from marshmallow_jit.utils import is_overridden

from .aware_datetime import AwareDateTimeDeserializationInliner, AwareDateTimeSerializationInliner
from .base import Inliner
from .boolean import BooleanDeserializationInliner, BooleanSerializationInliner
from .constant import ConstantDeserializationInliner, ConstantSerializationInliner
from .date import DateDeserializationInliner, DateSerializationInliner
from .datetime import DateTimeDeserializationInliner, DateTimeSerializationInliner
from .decimal import DecimalDeserializationInliner, DecimalSerializationInliner
from .dict import DictDeserializationInliner, DictSerializationInliner
from .email import EmailDeserializationInliner, EmailSerializationInliner
from .enum import EnumDeserializationInliner, EnumSerializationInliner
from .float import FloatDeserializationInliner, FloatSerializationInliner
from .function import FunctionDeserializationInliner, FunctionSerializationInliner
from .integer import IntegerDeserializationInliner, IntegerSerializationInliner
from .ip import IPDeserializationInliner, IPSerializationInliner
from .ip_interface import IPInterfaceDeserializationInliner, IPInterfaceSerializationInliner
from .ipv4 import IPv4DeserializationInliner, IPv4SerializationInliner
from .ipv4_interface import IPv4InterfaceDeserializationInliner, IPv4InterfaceSerializationInliner
from .ipv6 import IPv6DeserializationInliner, IPv6SerializationInliner
from .ipv6_interface import IPv6InterfaceDeserializationInliner, IPv6InterfaceSerializationInliner
from .list import ListDeserializationInliner, ListSerializationInliner
from .method import MethodDeserializationInliner, MethodSerializationInliner
from .naive_datetime import NaiveDateTimeDeserializationInliner, NaiveDateTimeSerializationInliner
from .nested import NestedDeserializationInliner, NestedSerializationInliner
from .raw import RawDeserializationInliner, RawSerializationInliner
from .str import StrDeserializationInliner, StrSerializationInliner
from .time import TimeDeserializationInliner, TimeSerializationInliner
from .timedelta import TimeDeltaDeserializationInliner, TimeDeltaSerializationInliner
from .url import UrlDeserializationInliner, UrlSerializationInliner
from .uuid import UUIDDeserializationInliner, UUIDSerializationInliner


class BuiltinSerializationInlinersFactory(Factory[[Schema, str, Field], Inliner]):
    # Ordered most-specific-first, as some fields subclass others and would otherwise be
    # matched by their parent's (less accurate) inliner: NaiveDateTime/AwareDateTime subclass
    # DateTime, IPv4/IPv6 subclass IP, IPv4Interface/IPv6Interface subclass IPInterface, and
    # Url/Email subclass Str.
    _inliners_by_type: ClassVar[list[tuple[type[Field], Inliner]]] = [
        (Url, UrlSerializationInliner()),
        (Email, EmailSerializationInliner()),
        (UUID, UUIDSerializationInliner()),  # Must come before Str - UUID subclasses String
        (Str, StrSerializationInliner()),
        (Integer, IntegerSerializationInliner()),
        (Float, FloatSerializationInliner()),
        (Decimal, DecimalSerializationInliner()),
        (Boolean, BooleanSerializationInliner()),
        (Constant, ConstantSerializationInliner()),
        (Method, MethodSerializationInliner()),
        (Function, FunctionSerializationInliner()),
        (Raw, RawSerializationInliner()),
        (Enum, EnumSerializationInliner()),
        (List, ListSerializationInliner()),
        (Dict, DictSerializationInliner()),
        (Nested, NestedSerializationInliner()),
        # Time and Date subclass DateTime, so they must come before DateTime
        (NaiveDateTime, NaiveDateTimeSerializationInliner()),
        (AwareDateTime, AwareDateTimeSerializationInliner()),
        (Time, TimeSerializationInliner()),  # Must come before DateTime - Time subclasses DateTime
        (Date, DateSerializationInliner()),  # Must come before DateTime - Date subclasses DateTime
        (DateTime, DateTimeSerializationInliner()),
        (TimeDelta, TimeDeltaSerializationInliner()),
        (IPv4Interface, IPv4InterfaceSerializationInliner()),
        (IPv6Interface, IPv6InterfaceSerializationInliner()),
        (IPInterface, IPInterfaceSerializationInliner()),
        (IPv4, IPv4SerializationInliner()),
        (IPv6, IPv6SerializationInliner()),
        (IP, IPSerializationInliner()),
    ]

    @override
    def find(self, schema: Schema, attr_name: str, field: Field) -> Inliner | None:
        for field_type, inliner in self._inliners_by_type:
            if isinstance(field, field_type) and not is_overridden(field._serialize, field_type._serialize):
                return inliner
        return None

    @override
    def find_by_name(self, name: str, schema: Schema, attr_name: str, field: Field) -> Inliner | None:
        return None


class BuiltinDeserializationInlinersFactory(Factory[[Schema, str, Field], Inliner]):
    # Ordered most-specific-first, similar to serialization inliners
    _inliners_by_type: ClassVar[list[tuple[type[Field], Inliner]]] = [
        (Url, UrlDeserializationInliner()),
        (Email, EmailDeserializationInliner()),
        (UUID, UUIDDeserializationInliner()),
        (Decimal, DecimalDeserializationInliner()),
        (Float, FloatDeserializationInliner()),
        (Integer, IntegerDeserializationInliner()),
        # Time and Date subclass DateTime, so they must come before DateTime
        (NaiveDateTime, NaiveDateTimeDeserializationInliner()),
        (AwareDateTime, AwareDateTimeDeserializationInliner()),
        (Time, TimeDeserializationInliner()),
        (Date, DateDeserializationInliner()),
        (DateTime, DateTimeDeserializationInliner()),
        (TimeDelta, TimeDeltaDeserializationInliner()),
        # IPv4/IPv6 subclass IP, so they must come before IP
        (IPv4, IPv4DeserializationInliner()),
        (IPv6, IPv6DeserializationInliner()),
        (IP, IPDeserializationInliner()),
        # IPv4Interface/IPv6Interface subclass IPInterface, so they must come before IPInterface
        (IPv4Interface, IPv4InterfaceDeserializationInliner()),
        (IPv6Interface, IPv6InterfaceDeserializationInliner()),
        (IPInterface, IPInterfaceDeserializationInliner()),
        (Str, StrDeserializationInliner()),
        (Boolean, BooleanDeserializationInliner()),
        (Enum, EnumDeserializationInliner()),
        (Raw, RawDeserializationInliner()),
        (Constant, ConstantDeserializationInliner()),
        (Method, MethodDeserializationInliner()),
        (Function, FunctionDeserializationInliner()),
        (List, ListDeserializationInliner()),
        (Dict, DictDeserializationInliner()),
        (Nested, NestedDeserializationInliner()),
    ]

    @override
    def find(self, schema: Schema, attr_name: str, field: Field) -> Inliner | None:
        for field_type, inliner in self._inliners_by_type:
            if isinstance(field, field_type):
                # Only use the inliner if _deserialize is not overridden
                # Validators are still called after inlining via _validate()
                if is_overridden(field._deserialize, field_type._deserialize):
                    return None
                return inliner
        return None

    @override
    def find_by_name(self, name: str, schema: Schema, attr_name: str, field: Field) -> Inliner | None:
        return None


builtin_serialization_inliner_factory = BuiltinSerializationInlinersFactory()
builtin_deserialization_inliner_registry = BuiltinDeserializationInlinersFactory()
