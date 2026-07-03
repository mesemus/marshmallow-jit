# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT

"""Profiling script for marshmallow-jit with complex nested schemas.

This script creates a schema with:
- ~10 primitive fields at the top level
- A list of 5 nested schemas, each with ~5 primitive fields
- Runs serialization/deserialization multiple times to identify hotspots

Usage:
    # Line-by-line profiling (requires line_profiler)
    kernprof -l -v profiling/profile_hotspots.py

    # Scalene memory/CPU profiler
    python -m scalene profiling/profile_hotspots.py

    # Standard cProfile
    python -m cProfile -o output.prof profiling/profile_hotspots.py
    python -m snakeviz output.prof  # GUI viewer
"""

import cProfile
import decimal
import pstats
from io import StringIO
from math import ceil
from typing import Any

from marshmallow import Schema, fields

from marshmallow_jit.schema import JITSchemaMixin, jit_schema

# ============================================================================
# Nested Schema Definitions
# ============================================================================


class AddressSchemaPlain(Schema):
    """Nested schema with ~5 primitive fields."""

    street = fields.Str(required=True)
    city = fields.Str(required=True)
    zip_code = fields.Str(required=True)
    country = fields.Str(required=True)
    building_number = fields.Int(required=False)


class AddressSchema(AddressSchemaPlain):
    """JIT-enabled nested schema (decorator applied at runtime)."""

    class Meta:
        jit_options = {
            "serializer": "mapping",
        }

    pass


# Apply JIT to nested schemas
AddressSchema = jit_schema(AddressSchema)


class ContactSchemaPlain(Schema):
    """Another nested schema with ~5 primitive fields."""

    email = fields.Email(required=True)
    phone = fields.Str(required=False)
    mobile = fields.Str(required=False)
    website = fields.Url(required=False)
    preferred_contact = fields.Str(validate=lambda v: v in ["email", "phone", "mail"])


class ContactSchema(ContactSchemaPlain):
    """JIT-enabled nested schema (decorator applied at runtime)."""

    class Meta:
        jit_options = {
            "serializer": "mapping",
        }

    pass


# Apply JIT to nested schemas
ContactSchema = jit_schema(ContactSchema)


# ============================================================================
# Top-level Schema with ~10 primitive fields + nested list
# ============================================================================


class UserSchemaPlain(Schema):
    """Top-level schema with ~10 primitive fields and a list of nested schemas."""

    # Primitive fields (~10)
    id = fields.Integer(required=True)
    username = fields.Str(required=True)
    email = fields.Email(required=True)
    first_name = fields.Str(required=True)
    last_name = fields.Str(required=True)
    age = fields.Integer(required=False)
    score = fields.Float(required=False)
    is_active = fields.Boolean(required=True)
    created_at = fields.DateTime(required=False)
    balance = fields.Decimal(required=False, places=2)

    # List of nested schemas (5 items) - use plain versions for plain schema
    addresses = fields.List(fields.Nested(AddressSchemaPlain()), required=True)
    contacts = fields.List(fields.Nested(ContactSchemaPlain()), required=False)


class UserSchemaJITClass(UserSchemaPlain):
    """JIT-enabled top-level schema."""

    class Meta:
        jit_options = {
            "serializer": "mapping",  # Force mapping serializer to skip runtime type checks
        }

    # List of nested schemas (5 items) - use plain versions for plain schema
    addresses = fields.List(fields.Nested(AddressSchema()), required=True)
    contacts = fields.List(fields.Nested(ContactSchema()), required=False)


# Apply JIT after class definition
UserSchemaJITClass = jit_schema(UserSchemaJITClass)


# Create instance factory
def UserSchemaJIT():
    """Factory that returns a JIT-enabled UserSchema instance."""
    return UserSchemaJITClass()


plain_schema_instance_for_measuring = UserSchemaPlain()
jit_schema_instance_for_measuring = UserSchemaJITClass()


# ============================================================================
# Test Data Generation
# ============================================================================


def generate_test_data(num_addresses: int = 5, num_contacts: int = 3) -> dict[str, Any]:
    """Generate realistic test data for the schema (for serialization - uses datetime objects)."""
    import datetime

    return {
        "id": 12345,
        "username": "johndoe",
        "email": "john.doe@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "age": 30,
        "score": 95.5,
        "is_active": True,
        "created_at": datetime.datetime(2024, 1, 15, 10, 30, 0),  # Use actual datetime object for serialization
        "balance": decimal.Decimal("1234.56"),  # Use Decimal for serialization
        "addresses": [
            {
                "street": "Main Street",
                "city": "Boston",
                "zip_code": "02101",
                "country": "USA",
                "building_number": i * 10 + 1,
            }
            for i in range(num_addresses)
        ],
        "contacts": [
            {
                "email": f"contact{i}@example.com",
                "phone": f"+1-555-{i:04d}",
                "mobile": f"+1-555-{i:04d}",
                "website": f"https://contact{i}.com",
                "preferred_contact": ["email", "phone", "mail"][i % 3],
            }
            for i in range(num_contacts)
        ],
    }


def generate_test_data_for_deserialization(num_addresses: int = 5, num_contacts: int = 3) -> dict[str, Any]:
    """Generate realistic test data for the schema (for deserialization - uses strings)."""
    return {
        "id": 12345,
        "username": "johndoe",
        "email": "john.doe@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "age": 30,
        "score": 95.5,
        "is_active": True,
        "created_at": "2024-01-15T10:30:00Z",  # Use ISO format string for deserialization
        "balance": "1234.56",
        "addresses": [
            {
                "street": "Main Street",
                "city": "Boston",
                "zip_code": "02101",
                "country": "USA",
                "building_number": i * 10 + 1,
            }
            for i in range(num_addresses)
        ],
        "contacts": [
            {
                "email": f"contact{i}@example.com",
                "phone": f"+1-555-{i:04d}",
                "mobile": f"+1-555-{i:04d}",
                "website": f"https://contact{i}.com",
                "preferred_contact": ["email", "phone", "mail"][i % 3],
            }
            for i in range(num_contacts)
        ],
    }


# ============================================================================
# Benchmark Functions
# ============================================================================


def benchmark_plain_serialization(data: dict, iterations: int = 1000) -> float:
    """Benchmark plain marshmallow serialization using pre-created instance."""
    schema = plain_schema_instance_for_measuring

    start = __import__("time").time()
    for _ in range(iterations):
        result = schema.dump(data)
    end = __import__("time").time()

    return (end - start) / iterations


def benchmark_jit_serialization(data: dict, iterations: int = 1000) -> float:
    """Benchmark JIT-compiled serialization using pre-created instance.

    Note: The JIT compilation has already happened at module load time,
    so we're measuring pure runtime performance with no warmup needed.
    """
    schema = jit_schema_instance_for_measuring

    start = __import__("time").time()
    for _ in range(iterations):
        result = schema.dump(data)
    end = __import__("time").time()

    return (end - start) / iterations


def benchmark_plain_deserialization(data: dict, iterations: int = 1000) -> float:
    """Benchmark plain marshmallow deserialization using pre-created instance."""
    schema = plain_schema_instance_for_measuring

    start = __import__("time").time()
    for _ in range(iterations):
        result = schema.load(data)
    end = __import__("time").time()

    return (end - start) / iterations


def benchmark_jit_deserialization(data: dict, iterations: int = 1000) -> float:
    """Benchmark JIT-compiled deserialization using pre-created instance.

    Note: The JIT compilation has already happened at module load time,
    so we're measuring pure runtime performance with no warmup needed.
    """
    schema = jit_schema_instance_for_measuring

    start = __import__("time").time()
    for _ in range(iterations):
        result = schema.load(data)
    end = __import__("time").time()

    return (end - start) / iterations


# ============================================================================
# Profiling Functions
# ============================================================================


def profile_serialization(method: str = "cprofile"):
    """Profile serialization with different methods."""
    data = generate_test_data()

    if method == "cprofile":
        print("=" * 80)
        print("CProfile: Serialization (JIT vs Plain)")
        print("=" * 80)

        # Profile plain serialization
        print("\n--- Plain Marshmallow Serialization ---")
        profiler = cProfile.Profile()
        profiler.enable()

        schema = UserSchemaPlain()
        for _ in range(100):
            result = schema.dump(data)

        profiler.disable()

        s = StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
        ps.print_stats(30)
        print(s.getvalue())

        # Profile JIT serialization
        print("\n--- JIT Serialization ---")
        profiler = cProfile.Profile()
        profiler.enable()

        schema = UserSchemaJIT()
        # Warm up
        _ = schema.dump(data)

        for _ in range(100):
            result = schema.dump(data)

        profiler.disable()

        s = StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
        ps.print_stats(30)
        print(s.getvalue())

    elif method == "scalene":
        print("Running Scalene profiler...")
        print("Note: Use `python -m scalene profiling/profile_hotspots.py` for full output")

        # Simple scalene-style timing
        import time

        data = generate_test_data()

        # Plain
        schema = UserSchemaPlain()
        start = time.time()
        for _ in range(1000):
            result = schema.dump(data)
        plain_time = time.time() - start

        # JIT
        schema = UserSchemaJIT()
        _ = schema.dump(data)  # Warm up
        start = time.time()
        for _ in range(1000):
            result = schema.dump(data)
        jit_time = time.time() - start

        print(f"\nPlain serialization: {plain_time * 1000:.2f}ms for 1000 iterations")
        print(f"JIT serialization:   {jit_time * 1000:.2f}ms for 1000 iterations")
        print(f"Speedup:             {plain_time / jit_time:.2f}x")


def profile_deserialization(method: str = "cprofile"):
    """Profile deserialization with different methods."""
    # Use deserialization data (strings, not datetime objects)
    data = generate_test_data_for_deserialization()

    if method == "cprofile":
        print("=" * 80)
        print("CProfile: Deserialization (JIT vs Plain)")
        print("=" * 80)

        # Profile plain deserialization
        print("\n--- Plain Marshmallow Deserialization ---")
        profiler = cProfile.Profile()
        profiler.enable()

        schema = plain_schema_instance_for_measuring
        for _ in range(100):
            result = schema.load(data)

        profiler.disable()

        s = StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
        ps.print_stats(30)
        print(s.getvalue())

        # Profile JIT deserialization
        print("\n--- JIT Deserialization ---")
        profiler = cProfile.Profile()
        profiler.enable()

        schema = jit_schema_instance_for_measuring
        for _ in range(100):
            result = schema.load(data)

        profiler.disable()

        s = StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
        ps.print_stats(30)
        print(s.getvalue())


def run_benchmarks():
    """Run simple benchmarks to compare performance."""
    print("=" * 80)
    print("Performance Benchmarks")
    print("=" * 80)

    # Use appropriate data for serialization vs deserialization
    ser_data = generate_test_data()  # datetime objects, Decimal
    de_data = generate_test_data_for_deserialization()  # strings
    iterations = 1000

    # Serialization benchmarks
    print("\n--- Serialization ---")
    plain_ser_time = benchmark_plain_serialization(ser_data, iterations)
    jit_ser_time = benchmark_jit_serialization(ser_data, iterations)

    print(f"Plain: {plain_ser_time * 1000:.3f}ms per iteration")
    print(f"JIT:   {jit_ser_time * 1000:.3f}ms per iteration")
    print(f"Speedup: {plain_ser_time / jit_ser_time:.2f}x")

    # Deserialization benchmarks
    print("\n--- Deserialization ---")
    plain_de_time = benchmark_plain_deserialization(de_data, iterations)
    jit_de_time = benchmark_jit_deserialization(de_data, iterations)

    print(f"Plain: {plain_de_time * 1000:.3f}ms per iteration")
    print(f"JIT:   {jit_de_time * 1000:.3f}ms per iteration")
    print(f"Speedup: {plain_de_time / jit_de_time:.2f}x")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "benchmark":
            run_benchmarks()
        elif command == "profile_serialization":
            profile_serialization("cprofile")
        elif command == "profile_deserialization":
            profile_deserialization("cprofile")
        else:
            print(f"Unknown command: {command}")
            print("Usage: python profile_hotspots.py [benchmark|profile_serialization|profile_deserialization]")
    else:
        # Default: run benchmarks
        run_benchmarks()
