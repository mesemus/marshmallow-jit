# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT

"""Serialization-specific test fixtures - imports shared field matrix from parent conftest."""

# Re-export everything from parent conftest for backward compatibility
from tests.conftest import (
    FIELD_DESERIALIZATION_MATRIX,
    FIELD_MATRIX,
    FIELD_SERIALIZATION_MATRIX,
    SERIALIZATION_KWARGS_CASES,
    UnstringifiableValue,
    _CustomDecimalField,
    _CustomFloatField,
    _CustomIntegerField,
    _ExampleEnum,
    _ExampleNestedSchema,
    _ExampleNestedSchemaWithHooks,
    build_source_kwargs,
    configure_field,
)

__all__ = [
    "SERIALIZATION_KWARGS_CASES",
    "FIELD_DESERIALIZATION_MATRIX",
    "FIELD_MATRIX",
    "FIELD_SERIALIZATION_MATRIX",
    "UnstringifiableValue",
    "_CustomDecimalField",
    "_CustomFloatField",
    "_CustomIntegerField",
    "_ExampleEnum",
    "_ExampleNestedSchema",
    "_ExampleNestedSchemaWithHooks",
    "build_source_kwargs",
    "configure_field",
]
