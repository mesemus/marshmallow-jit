# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Configuration for the marshmallow-jit package."""

import os


def env_enabled(var_name: str) -> bool:
    """Check if an environment variable is enabled (true/1/yes/y)."""
    return os.getenv(var_name, "false").lower() in ("true", "1", "yes", "y")


# Whether to use the global cache for storing marshmallow schemas.
#
# Note: the cache records classes by their id, so if classes are generated
# during the runtime, the cache will not perform well.
USE_GLOBAL_CACHE = env_enabled("MARSHMALLOW_JIT_USE_GLOBAL_CACHE")
GLOBAL_CACHE_SIZE = int(os.getenv("MARSHMALLOW_JIT_GLOBAL_CACHE_SIZE", 1000))

#
# Error/Warning handling
FAIL_ON_UNKNOWN_FIELD_TYPE = env_enabled("MARSHMALLOW_JIT_FAIL_ON_UNKNOWN_FIELD")
