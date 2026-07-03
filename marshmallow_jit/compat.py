# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Marshmallow version compatibility utilities.

This module provides a unified API across marshmallow 3.x and 4.x,
handling differences in import paths and available features.
"""

"""Marshmallow version compatibility utilities.

This module provides a unified API across marshmallow 3.x and 4.x,
handling differences in import paths and available features.
"""

# Try marshmallow 4 first (constants at package root)
try:
    from marshmallow import EXCLUDE, INCLUDE, RAISE

    _MARSHMALLOW_MAJOR_VERSION = 4
except ImportError:
    # Fall back to marshmallow 3 (constants in utils)
    from marshmallow.utils import EXCLUDE, INCLUDE, RAISE

    _MARSHMALLOW_MAJOR_VERSION = 3

__all__ = ["RAISE", "INCLUDE", "EXCLUDE", "_MARSHMALLOW_MAJOR_VERSION"]
