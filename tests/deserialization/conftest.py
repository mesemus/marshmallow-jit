# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT

"""Deserialization-specific test fixtures - imports shared field matrix from parent conftest."""

# Re-export everything from parent conftest for backward compatibility
from tests.conftest import (
    DESERIALIZATION_KWARGS_CASES,
    FIELD_DESERIALIZATION_MATRIX,
    FIELD_SERIALIZATION_MATRIX,
    build_deserialization_source_kwargs,
    configure_deserialization_field,
)

__all__ = [
    "DESERIALIZATION_KWARGS_CASES",
    "FIELD_DESERIALIZATION_MATRIX",
    "FIELD_SERIALIZATION_MATRIX",
    "build_deserialization_source_kwargs",
    "configure_deserialization_field",
]
