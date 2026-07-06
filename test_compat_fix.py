#!/usr/bin/env python3
"""Test script to verify marshmallow 3 vs 4 compatibility fix."""

import datetime as dt
from enum import Enum

from marshmallow import Schema, ValidationError
from marshmallow.fields import Date, DateTime, Time, TimeDelta
from marshmallow.fields import Enum as EnumField

from marshmallow_jit.schema import jit_schema


class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3


@jit_schema
class TestSchema(Schema):
    datetime_field = DateTime()
    date_field = Date()
    time_field = Time()
    timedelta_field = TimeDelta()
    enum_field = EnumField(Color, by_value=True)


def test_native_types_rejected_in_marshmallow_3():
    """Test that native Python types are properly rejected during deserialization in marshmallow 3."""
    schema = TestSchema()

    # Test with datetime object (should be rejected)
    try:
        result = schema.load({"datetime_field": dt.datetime(2024, 1, 2)})
        print("❌ FAILED: datetime object should be rejected but was accepted:", result)
        return False
    except ValidationError as e:
        print("✅ PASSED: datetime object correctly rejected:", str(e))

    # Test with date object (should be rejected)
    try:
        result = schema.load({"date_field": dt.date(2024, 1, 2)})
        print("❌ FAILED: date object should be rejected but was accepted:", result)
        return False
    except ValidationError as e:
        print("✅ PASSED: date object correctly rejected:", str(e))

    # Test with time object (should be rejected)
    try:
        result = schema.load({"time_field": dt.time(12, 30)})
        print("❌ FAILED: time object should be rejected but was accepted:", result)
        return False
    except ValidationError as e:
        print("✅ PASSED: time object correctly rejected:", str(e))

    # Test with timedelta object (should be rejected)
    try:
        result = schema.load({"timedelta_field": dt.timedelta(days=1)})
        print("❌ FAILED: timedelta object should be rejected but was accepted:", result)
        return False
    except ValidationError as e:
        print("✅ PASSED: timedelta object correctly rejected:", str(e))

    # Test with enum object (should be rejected)
    try:
        result = schema.load({"enum_field": Color.RED})
        print("❌ FAILED: enum object should be rejected but was accepted:", result)
        return False
    except ValidationError as e:
        print("✅ PASSED: enum object correctly rejected:", str(e))

    return True


def test_string_inputs_accepted():
    """Test that string inputs are properly accepted and parsed."""
    schema = TestSchema()

    # Test with valid string inputs
    data = {
        "datetime_field": "2024-01-02T12:30:00",
        "date_field": "2024-01-02",
        "time_field": "12:30:00",
        "timedelta_field": 86400,  # 1 day in seconds
        "enum_field": 1,  # RED
    }

    result = schema.load(data)
    print("✅ PASSED: Valid string inputs correctly parsed:", result)
    assert result["datetime_field"] == dt.datetime(2024, 1, 2, 12, 30)
    assert result["date_field"] == dt.date(2024, 1, 2)
    assert result["time_field"] == dt.time(12, 30)
    assert result["timedelta_field"] == dt.timedelta(days=1)
    assert result["enum_field"] == Color.RED
    return True


if __name__ == "__main__":
    print("Testing marshmallow 3 vs 4 compatibility fix...\n")
    print("=" * 70)
    print("Test 1: Native types should be rejected in marshmallow 3")
    print("=" * 70)
    test1_passed = test_native_types_rejected_in_marshmallow_3()

    print("\n" + "=" * 70)
    print("Test 2: String inputs should be accepted and parsed")
    print("=" * 70)
    test2_passed = test_string_inputs_accepted()

    print("\n" + "=" * 70)
    if test1_passed and test2_passed:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 70)
